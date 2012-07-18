import logging
import urllib

from django.conf import settings
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from mitxmako.shortcuts import render_to_response, render_to_string
#from django.views.decorators.csrf import ensure_csrf_cookie
from django_future.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control

from module_render import toc_for_course, get_module, get_section
from models import StudentModuleCache
from student.models import UserProfile
from multicourse import multicourse_settings

from util.cache import cache, cache_if_anonymous
from student.models import UserTestGroup, CourseEnrollment
from courseware import grades
from courseware.courses import check_course
from xmodule.modulestore.django import modulestore

log = logging.getLogger("mitx.courseware")

template_imports = {'urllib': urllib}

def user_groups(user):
    if not user.is_authenticated():
        return []

    # TODO: Rewrite in Django
    key = 'user_group_names_{user.id}'.format(user=user)
    cache_expiration = 60 * 60  # one hour

    # Kill caching on dev machines -- we switch groups a lot
    group_names = cache.get(key)

    if group_names is None:
        group_names = [u.name for u in UserTestGroup.objects.filter(users=user)]
        cache.set(key, group_names, cache_expiration)

    return group_names


def format_url_params(params):
    return [urllib.quote(string.replace(' ', '_')) for string in params]


@ensure_csrf_cookie
@cache_if_anonymous
def courses(request):
    # TODO: Clean up how 'error' is done.
    context = {'courses': modulestore().get_courses()}
    return render_to_response("courses.html", context)

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def gradebook(request, course_id):
    if 'course_admin' not in user_groups(request.user):
        raise Http404
    course = check_course(course_id)
    
    
    student_objects = User.objects.all()[:100]
    student_info = []

    for student in student_objects:
        student_module_cache = StudentModuleCache(student, course)
        course, _, _, _ = get_module(request.user, request, course.location, student_module_cache)
        student_info.append({
            'username': student.username,
            'id': student.id,
            'email': student.email,
            'grade_info': grades.grade_sheet(student, course, student_module_cache),
            'realname': UserProfile.objects.get(user=student).name
        })

    return render_to_response('gradebook.html', {'students': student_info, 'course': course})


@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def profile(request, course_id, student_id=None):
    ''' User profile. Show username, location, etc, as well as grades .
        We need to allow the user to change some of these settings .'''
    course = check_course(course_id)

    if student_id is None:
        student = request.user
    else:
        if 'course_admin' not in user_groups(request.user):
            raise Http404
        student = User.objects.get(id=int(student_id))

    user_info = UserProfile.objects.get(user=student)

    student_module_cache = StudentModuleCache(request.user, course)
    course, _, _, _ = get_module(request.user, request, course.location, student_module_cache)

    context = {'name': user_info.name,
               'username': student.username,
               'location': user_info.location,
               'language': user_info.language,
               'email': student.email,
               'course': course,
               'format_url_params': format_url_params,
               'csrf': csrf(request)['csrf_token']
               }
    context.update(grades.grade_sheet(student, course, student_module_cache))

    return render_to_response('profile.html', context)


def render_accordion(request, course, chapter, section):
    ''' Draws navigation bar. Takes current position in accordion as
        parameter.

        If chapter and section are '' or None, renders a default accordion.

        Returns (initialization_javascript, content)'''

    # TODO (cpennington): do the right thing with courses
    toc = toc_for_course(request.user, request, course, chapter, section)

    active_chapter = 1
    for i in range(len(toc)):
        if toc[i]['active']:
            active_chapter = i

    context = dict([('active_chapter', active_chapter),
                    ('toc', toc),
                    ('course_name', course.title),
                    ('course_id', course.id),
                    ('format_url_params', format_url_params),
                    ('csrf', csrf(request)['csrf_token'])] + template_imports.items())
    return render_to_string('accordion.html', context)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def index(request, course_id, chapter=None, section=None,
          position=None):
    ''' Displays courseware accordion, and any associated content.
    If course, chapter, and section aren't all specified, just returns
    the accordion.  If they are specified, returns an error if they don't
    point to a valid module.

    Arguments:

     - request    : HTTP request
     - course     : coursename (str)
     - chapter    : chapter name (str)
     - section    : section name (str)
     - position   : position in module, eg of <sequential> module (str)

    Returns:

     - HTTPresponse
    '''
    course = check_course(course_id)
    
    def clean(s):
        ''' Fixes URLs -- we convert spaces to _ in URLs to prevent
        funny encoding characters and keep the URLs readable.  This undoes
        that transformation.
        '''
        return s.replace('_', ' ') if s is not None else None

    chapter = clean(chapter)
    section = clean(section)

    if settings.ENABLE_MULTICOURSE:
        settings.MODULESTORE['default']['OPTIONS']['data_dir'] = settings.DATA_DIR + multicourse_settings.get_course_xmlpath(course)

    context = {
        'csrf': csrf(request)['csrf_token'],
        'accordion': render_accordion(request, course, chapter, section),
        'COURSE_TITLE': course.title,
        'course': course,
        'init': '',
        'content': ''
    }

    look_for_module = chapter is not None and section is not None
    if look_for_module:
        # TODO (cpennington): Pass the right course in here

        section = get_section(course, chapter, section)
        student_module_cache = StudentModuleCache(request.user, section)
        module, _, _, _ = get_module(request.user, request, section.location, student_module_cache)
        context['content'] = module.get_html()

    result = render_to_response('courseware.html', context)
    return result


def jump_to(request, probname=None):
    '''
    Jump to viewing a specific problem.  The problem is specified by a
    problem name - currently the filename (minus .xml) of the problem.
    Maybe this should change to a more generic tag, eg "name" given as
    an attribute in <problem>.

    We do the jump by (1) reading course.xml to find the first
    instance of <problem> with the given filename, then (2) finding
    the parent element of the problem, then (3) rendering that parent
    element with a specific computed position value (if it is
    <sequential>).

    '''
    # get coursename if stored
    coursename = multicourse_settings.get_coursename_from_request(request)

    # begin by getting course.xml tree
    xml = content_parser.course_file(request.user, coursename)

    # look for problem of given name
    pxml = xml.xpath('//problem[@filename="%s"]' % probname)
    if pxml:
        pxml = pxml[0]

    # get the parent element
    parent = pxml.getparent()

    # figure out chapter and section names
    chapter = None
    section = None
    branch = parent
    for k in range(4):  # max depth of recursion
        if branch.tag == 'section':
            section = branch.get('name')
        if branch.tag == 'chapter':
            chapter = branch.get('name')
        branch = branch.getparent()

    position = None
    if parent.tag == 'sequential':
        position = parent.index(pxml) + 1  # position in sequence

    return index(request,
                 course=coursename, chapter=chapter,
                 section=section, position=position)


@ensure_csrf_cookie
def course_info(request, course_id):
    course = check_course(course_id)

    return render_to_response('info.html', {'course': course})

@ensure_csrf_cookie
def course_about(request, course_id):
    def registered_for_course(course, user):
        if user.is_authenticated():
            return CourseEnrollment.objects.filter(user = user, course_id=course.id).exists()
        else:
            return False
    course = check_course(course_id, course_must_be_open=False)
    registered = registered_for_course(course, request.user)
    return render_to_response('portal/course_about.html', {'course': course, 'registered': registered})


@login_required
@ensure_csrf_cookie
def enroll(request, course_id):
    course = check_course(course_id, course_must_be_open=False)
    user = request.user
    
    enrollment, created = CourseEnrollment.objects.get_or_create(user=user, course_id=course.id)
    
    return redirect(reverse('dashboard'))


def university_profile(request, org_id):
    all_courses = modulestore().get_courses()
    valid_org_ids = set(c.org for c in all_courses)
    if org_id not in valid_org_ids:
        raise Http404("University Profile not found for {0}".format(org_id))

    # Only grab courses for this org...
    courses=[c for c in all_courses if c.org == org_id]
    context = dict(courses=courses, org_id=org_id)
    template_file = "university_profile/{0}.html".format(org_id).lower()

    return render_to_response(template_file, context)


