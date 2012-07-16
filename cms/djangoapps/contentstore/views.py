from util.json_request import expect_json
import json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django_future.csrf import ensure_csrf_cookie
from django.core.urlresolvers import reverse
from fs.osfs import OSFS

from xmodule.modulestore import Location
from github_sync import export_to_github

from mitxmako.shortcuts import render_to_response
from xmodule.modulestore.django import modulestore

# ==== Public views ==================================================

@ensure_csrf_cookie
def signup(request):
    """
    Display the signup form.
    """
    csrf_token = csrf(request)['csrf_token']
    return render_to_response('signup.html', {'csrf': csrf_token }) 

@ensure_csrf_cookie
def login_page(request):
    """
    Display the login form.
    """
    csrf_token = csrf(request)['csrf_token']
    return render_to_response('login.html', {'csrf': csrf_token }) 
    
# ==== Views for any logged-in user ==================================

@login_required
@ensure_csrf_cookie
def index(request):
    courses = modulestore().get_items(['i4x', None, None, 'course', None])
    return render_to_response('index.html', {
        'courses': [(course.metadata['display_name'],
                    reverse('course_index', args=[
                        course.location.org,
                        course.location.course,
                        course.location.name]))
                    for course in courses]
    })

# ==== Views with per-item permissions================================

def has_access(user, location):
    '''Return True if user allowed to access this piece of data'''
    # TODO (vshnayder): actually check perms
    return user.is_active and user.is_authenticated

@login_required
@ensure_csrf_cookie
def course_index(request, org, course, name):
    location = ['i4x', org, course, 'course', name]
    if not has_access(request.user, location):
        raise Http404  # TODO (vshnayder): better error
    
    # TODO (cpennington): These need to be read in from the active user
    course = modulestore().get_item(location)
    weeks = course.get_children()
    return render_to_response('course_index.html', {'weeks': weeks})

@login_required
def edit_item(request):
    # TODO (vshnayder): change name from id to location in coffee+html as well.
    item_location = request.GET['id']
    print item_location, request.GET
    if not has_access(request.user, item_location):
        raise Http404  # TODO (vshnayder): better error
        
    item = modulestore().get_item(item_location)
    return render_to_response('unit.html', {
        'contents': item.get_html(),
        'js_module': item.js_module_name(),
        'category': item.category,
        'name': item.name,
    })


def user_author_string(user):
    '''Get an author string for commits by this user.  Format:
    first last <email@email.com>.

    If the first and last names are blank, uses the username instead.
    Assumes that the email is not blank.
    '''
    f = user.first_name
    l = user.last_name
    if f == '' and l == '':
        f = user.username
    return '{first} {last} <{email}>'.format(first=f,
                                             last=l,
                                             email=user.email)

@login_required
@expect_json
def save_item(request):
    item_location = request.POST['id']
    if not has_access(request.user, item_location):
        raise Http404  # TODO (vshnayder): better error

    data = json.loads(request.POST['data'])
    modulestore().update_item(item_location, data)

    # Export the course back to github
    # This uses wildcarding to find the course, which requires handling
    # multiple courses returned, but there should only ever be one
    course_location = Location(item_location)._replace(
        category='course', name=None)
    courses = modulestore().get_items(course_location, depth=None)
    for course in courses:
        author_string = user_author_string(request.user)
        export_to_github(course, "CMS Edit", author_string)

    return HttpResponse(json.dumps({}))
