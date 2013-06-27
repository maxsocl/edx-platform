"""
Views related to operations on course objects
"""
import json
import random
import string

from django.contrib.auth.decorators import login_required
from django_future.csrf import ensure_csrf_cookie
from django.conf import settings
from django.views.decorators.http import require_http_methods, require_POST
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from util.json_request import JsonResponse
from mitxmako.shortcuts import render_to_response

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.inheritance import own_metadata

from xmodule.modulestore.exceptions import (
    ItemNotFoundError, InvalidLocationError)
from xmodule.modulestore import Location

from contentstore.course_info_model import (
    get_course_updates, update_course_updates, delete_course_update)
from contentstore.utils import (
    get_lms_link_for_item, add_extra_panel_tab, remove_extra_panel_tab,
    get_modulestore)
from models.settings.course_details import (
    CourseDetails, CourseSettingsEncoder)

from models.settings.course_grading import CourseGradingModel
from models.settings.course_metadata import CourseMetadata
from auth.authz import create_all_course_groups, is_user_in_creator_group
from util.json_request import expect_json

from .access import has_access, get_location_and_verify_access
from .tabs import initialize_course_tabs
from .component import (
    OPEN_ENDED_COMPONENT_TYPES, NOTE_COMPONENT_TYPES,
    ADVANCED_COMPONENT_POLICY_KEY)

from django_comment_common.utils import seed_permissions_roles
import datetime
from django.utils.timezone import UTC
__all__ = ['course_index', 'create_new_course', 'course_info',
           'course_info_updates', 'get_course_settings',
           'course_config_graders_page',
           'course_config_advanced_page',
           'course_settings_updates',
           'course_grader_updates',
           'course_advanced_updates', 'textbook_index', 'textbook_by_id',
           'create_textbook']


@login_required
@ensure_csrf_cookie
def course_index(request, org, course, name):
    """
    Display an editable course overview.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    lms_link = get_lms_link_for_item(location)

    upload_asset_callback_url = reverse('upload_asset', kwargs={
        'org': org,
        'course': course,
        'coursename': name
    })

    course = modulestore().get_item(location, depth=3)
    sections = course.get_children()

    return render_to_response('overview.html', {
        'context_course': course,
        'lms_link': lms_link,
        'sections': sections,
        'course_graders': json.dumps(CourseGradingModel.fetch(course.location).graders),
        'parent_location': course.location,
        'new_section_template': Location('i4x', 'edx', 'templates', 'chapter', 'Empty'),
        'new_subsection_template': Location('i4x', 'edx', 'templates', 'sequential', 'Empty'),  # for now they are the same, but the could be different at some point...
        'upload_asset_callback_url': upload_asset_callback_url,
        'create_new_unit_template': Location('i4x', 'edx', 'templates', 'vertical', 'Empty')
    })


@login_required
@expect_json
def create_new_course(request):

    if not is_user_in_creator_group(request.user):
        raise PermissionDenied()

    # This logic is repeated in xmodule/modulestore/tests/factories.py
    # so if you change anything here, you need to also change it there.
    # TODO: write a test that creates two courses, one with the factory and
    # the other with this method, then compare them to make sure they are
    # equivalent.
    template = Location(request.POST['template'])
    org = request.POST.get('org')
    number = request.POST.get('number')
    display_name = request.POST.get('display_name')

    try:
        dest_location = Location('i4x', org, number, 'course', Location.clean(display_name))
    except InvalidLocationError as error:
        return JsonResponse({
            "ErrMsg": "Unable to create course '{name}'.\n\n{err}".format(
                name=display_name, err=error.message)})

    # see if the course already exists
    existing_course = None
    try:
        existing_course = modulestore('direct').get_item(dest_location)
    except ItemNotFoundError:
        pass

    if existing_course is not None:
        return JsonResponse({'ErrMsg': 'There is already a course defined with this name.'})

    course_search_location = ['i4x', dest_location.org, dest_location.course, 'course', None]
    courses = modulestore().get_items(course_search_location)

    if len(courses) > 0:
        return JsonResponse({'ErrMsg': 'There is already a course defined with the same organization and course number.'})

    new_course = modulestore('direct').clone_item(template, dest_location)

    # clone a default 'about' module as well

    about_template_location = Location(['i4x', 'edx', 'templates', 'about', 'overview'])
    dest_about_location = dest_location._replace(category='about', name='overview')
    modulestore('direct').clone_item(about_template_location, dest_about_location)

    if display_name is not None:
        new_course.display_name = display_name

    # set a default start date to now
    new_course.start = datetime.datetime.now(UTC())

    initialize_course_tabs(new_course)

    create_all_course_groups(request.user, new_course.location)

    # seed the forums
    seed_permissions_roles(new_course.location.course_id)

    return JsonResponse({'id': new_course.location.url()})


@login_required
@ensure_csrf_cookie
def course_info(request, org, course, name, provided_id=None):
    """
    Send models and views as well as html for editing the course info to the client.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    course_module = modulestore().get_item(location)

    # get current updates
    location = Location(['i4x', org, course, 'course_info', "updates"])

    return render_to_response('course_info.html', {
        'context_course': course_module,
        'url_base': "/" + org + "/" + course + "/",
        'course_updates': json.dumps(get_course_updates(location)),
        'handouts_location': Location(['i4x', org, course, 'course_info', 'handouts']).url()
    })


@expect_json
@login_required
@ensure_csrf_cookie
def course_info_updates(request, org, course, provided_id=None):
    """
    restful CRUD operations on course_info updates.

    org, course: Attributes of the Location for the item to edit
    provided_id should be none if it's new (create) and a composite of the update db id + index otherwise.
    """
    # ??? No way to check for access permission afaik
    # get current updates
    location = ['i4x', org, course, 'course_info', "updates"]

    # Hmmm, provided_id is coming as empty string on create whereas I believe it used to be None :-(
    # Possibly due to my removing the seemingly redundant pattern in urls.py
    if provided_id == '':
        provided_id = None

    # check that logged in user has permissions to this item
    if not has_access(request.user, location):
        raise PermissionDenied()

    if request.method == 'GET':
        return JsonResponse(get_course_updates(location))
    elif request.method == 'DELETE':
        try:
            return JsonResponse(delete_course_update(location, request.POST, provided_id))
        except:
            return HttpResponseBadRequest("Failed to delete",
                                          content_type="text/plain")
    elif request.method == 'POST':
        try:
            return JsonResponse(update_course_updates(location, request.POST, provided_id))
        except:
            return HttpResponseBadRequest("Failed to save",
                                          content_type="text/plain")


@login_required
@ensure_csrf_cookie
def get_course_settings(request, org, course, name):
    """
    Send models and views as well as html for editing the course settings to the client.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    course_module = modulestore().get_item(location)

    return render_to_response('settings.html', {
        'context_course': course_module,
        'course_location': location,
        'details_url': reverse(course_settings_updates,
                               kwargs={"org": org,
                                       "course": course,
                                       "name": name,
                                       "section": "details"}),
        'about_page_editable': not settings.MITX_FEATURES.get('ENABLE_MKTG_SITE', False)
    })


@login_required
@ensure_csrf_cookie
def course_config_graders_page(request, org, course, name):
    """
    Send models and views as well as html for editing the course settings to the client.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    course_module = modulestore().get_item(location)
    course_details = CourseGradingModel.fetch(location)

    return render_to_response('settings_graders.html', {
        'context_course': course_module,
        'course_location': location,
        'course_details': json.dumps(course_details, cls=CourseSettingsEncoder)
    })


@login_required
@ensure_csrf_cookie
def course_config_advanced_page(request, org, course, name):
    """
    Send models and views as well as html for editing the advanced course settings to the client.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    course_module = modulestore().get_item(location)

    return render_to_response('settings_advanced.html', {
        'context_course': course_module,
        'course_location': location,
        'advanced_dict': json.dumps(CourseMetadata.fetch(location)),
    })


@expect_json
@login_required
@ensure_csrf_cookie
def course_settings_updates(request, org, course, name, section):
    """
    restful CRUD operations on course settings. This differs from get_course_settings by communicating purely
    through json (not rendering any html) and handles section level operations rather than whole page.

    org, course: Attributes of the Location for the item to edit
    section: one of details, faculty, grading, problems, discussions
    """
    get_location_and_verify_access(request, org, course, name)

    if section == 'details':
        manager = CourseDetails
    elif section == 'grading':
        manager = CourseGradingModel
    else:
        return

    if request.method == 'GET':
        # Cannot just do a get w/o knowing the course name :-(
        return JsonResponse(manager.fetch(Location(['i4x', org, course, 'course', name])), encoder=CourseSettingsEncoder)
    elif request.method == 'POST':  # post or put, doesn't matter.
        return JsonResponse(manager.update_from_json(request.POST), encoder=CourseSettingsEncoder)


@expect_json
@require_http_methods(("GET", "POST", "PUT", "DELETE"))
@login_required
@ensure_csrf_cookie
def course_grader_updates(request, org, course, name, grader_index=None):
    """
    restful CRUD operations on course_info updates. This differs from get_course_settings by communicating purely
    through json (not rendering any html) and handles section level operations rather than whole page.

    org, course: Attributes of the Location for the item to edit
    """

    location = get_location_and_verify_access(request, org, course, name)

    if request.method == 'GET':
        # Cannot just do a get w/o knowing the course name :-(
        return JsonResponse(CourseGradingModel.fetch_grader(Location(location), grader_index))
    elif request.method == "DELETE":
        # ??? Should this return anything? Perhaps success fail?
        CourseGradingModel.delete_grader(Location(location), grader_index)
        return JsonResponse()
    else:  # post or put, doesn't matter.
        return JsonResponse(CourseGradingModel.update_grader_from_json(Location(location), request.POST))


# # NB: expect_json failed on ["key", "key2"] and json payload
@require_http_methods(("GET", "POST", "PUT", "DELETE"))
@login_required
@ensure_csrf_cookie
def course_advanced_updates(request, org, course, name):
    """
    restful CRUD operations on metadata. The payload is a json rep of the metadata dicts. For delete, otoh,
    the payload is either a key or a list of keys to delete.

    org, course: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)

    if request.method == 'GET':
        return JsonResponse(CourseMetadata.fetch(location))
    elif request.method == 'DELETE':
        return JsonResponse(CourseMetadata.delete_key(location, json.loads(request.body)))
    else:
        # NOTE: request.POST is messed up because expect_json
        # cloned_request.POST.copy() is creating a defective entry w/ the whole payload as the key
        request_body = json.loads(request.body)
        # Whether or not to filter the tabs key out of the settings metadata
        filter_tabs = True

        # Check to see if the user instantiated any advanced components. This is a hack
        # that does the following :
        #   1) adds/removes the open ended panel tab to a course automatically if the user
        #   has indicated that they want to edit the combinedopendended or peergrading module
        #   2) adds/removes the notes panel tab to a course automatically if the user has
        #   indicated that they want the notes module enabled in their course
        # TODO refactor the above into distinct advanced policy settings
        if ADVANCED_COMPONENT_POLICY_KEY in request_body:
            # Get the course so that we can scrape current tabs
            course_module = modulestore().get_item(location)

            # Maps tab types to components
            tab_component_map = {
                'open_ended': OPEN_ENDED_COMPONENT_TYPES,
                'notes': NOTE_COMPONENT_TYPES,
            }

            # Check to see if the user instantiated any notes or open ended components
            for tab_type in tab_component_map.keys():
                component_types = tab_component_map.get(tab_type)
                found_ac_type = False
                for ac_type in component_types:
                    if ac_type in request_body[ADVANCED_COMPONENT_POLICY_KEY]:
                        # Add tab to the course if needed
                        changed, new_tabs = add_extra_panel_tab(tab_type, course_module)
                        # If a tab has been added to the course, then send the metadata along to CourseMetadata.update_from_json
                        if changed:
                            course_module.tabs = new_tabs
                            request_body.update({'tabs': new_tabs})
                            # Indicate that tabs should not be filtered out of the metadata
                            filter_tabs = False
                        # Set this flag to avoid the tab removal code below.
                        found_ac_type = True
                        break
                # If we did not find a module type in the advanced settings,
                # we may need to remove the tab from the course.
                if not found_ac_type:
                    # Remove tab from the course if needed
                    changed, new_tabs = remove_extra_panel_tab(tab_type, course_module)
                    if changed:
                        course_module.tabs = new_tabs
                        request_body.update({'tabs': new_tabs})
                        # Indicate that tabs should *not* be filtered out of the metadata
                        filter_tabs = False
        try:
            return JsonResponse(CourseMetadata.update_from_json(location,
                                                                request_body,
                                                                filter_tabs=filter_tabs))
        except (TypeError, ValueError) as e:
            return HttpResponseBadRequest("Incorrect setting format. " + str(e), content_type="text/plain")


class TextbookValidationError(Exception):
    pass


def validate_textbooks_json(text):
    try:
        textbooks = json.loads(text)
    except ValueError:
        raise TextbookValidationError("invalid JSON")
    if not isinstance(textbooks, (list, tuple)):
        raise TextbookValidationError("must be JSON list")
    for textbook in textbooks:
        validate_textbook_json(textbook)
    # check specified IDs for uniqueness
    all_ids = [textbook["id"] for textbook in textbooks if "id" in textbook]
    unique_ids = set(all_ids)
    if len(all_ids) > len(unique_ids):
        raise TextbookValidationError("IDs must be unique")
    return textbooks


def validate_textbook_json(textbook, used_ids=()):
    if isinstance(textbook, basestring):
        try:
            textbook = json.loads(textbook)
        except ValueError:
            raise TextbookValidationError("invalid JSON")
    if not isinstance(textbook, dict):
        raise TextbookValidationError("must be JSON object")
    if not textbook.get("tab_title"):
        raise TextbookValidationError("must have tab_title")
    tid = str(textbook.get("id", ""))
    if tid and not tid[0].isdigit():
        raise TextbookValidationError("textbook ID must start with a digit")
    return textbook


def assign_textbook_id(textbook, used_ids=()):
    tid = Location.clean(textbook["tab_title"])
    if not tid[0].isdigit():
        # stick a random digit in front
        tid = random.choice(string.digits) + tid
    while tid in used_ids:
        # add a random ASCII character to the end
        tid = tid + random.choice(string.ascii_lowercase)
    return tid


@login_required
@ensure_csrf_cookie
def textbook_index(request, org, course, name):
    """
    Display an editable textbook overview.

    org, course, name: Attributes of the Location for the item to edit
    """
    location = get_location_and_verify_access(request, org, course, name)
    store = get_modulestore(location)
    course_module = store.get_item(location, depth=3)

    if request.is_ajax():
        if request.method == 'GET':
            return JsonResponse(course_module.pdf_textbooks)
        elif request.method == 'POST':
            try:
                textbooks = validate_textbooks_json(request.body)
            except TextbookValidationError as e:
                return JsonResponse({"error": e.message}, status=400)

            tids = set(t["id"] for t in textbooks if "id" in t)
            for textbook in textbooks:
                if not "id" in textbook:
                    tid = assign_textbook_id(textbook, tids)
                    textbook["id"] = tid
                    tids.add(tid)

            if not any(tab['type'] == 'pdf_textbooks' for tab in course_module.tabs):
                course_module.tabs.append({"type": "pdf_textbooks"})
            course_module.pdf_textbooks = textbooks
            store.update_metadata(course_module.location, own_metadata(course_module))
            return JsonResponse(course_module.pdf_textbooks)
    else:
        upload_asset_url = reverse('upload_asset', kwargs={
            'org': org,
            'course': course,
            'coursename': name,
        })
        textbook_url = reverse('textbook_index', kwargs={
            'org': org,
            'course': course,
            'name': name,
        })
        return render_to_response('textbooks.html', {
            'context_course': course_module,
            'course': course_module,
            'upload_asset_url': upload_asset_url,
            'textbook_url': textbook_url,
        })


@require_POST
@login_required
@ensure_csrf_cookie
def create_textbook(request, org, course, name):
    location = get_location_and_verify_access(request, org, course, name)
    store = get_modulestore(location)
    course_module = store.get_item(location, depth=3)

    try:
        textbook = validate_textbook_json(request.body)
    except TextbookValidationError as e:
        return JsonResponse({"error": e.message}, status=400)
    if not textbook.get("id"):
        tids = set(t["id"] for t in course_module.pdf_textbooks if "id" in t)
        textbook["id"] = assign_textbook_id(textbook, tids)
    course_module.pdf_textbooks.append(textbook)
    store.update_metadata(course_module.location, own_metadata(course_module))
    resp = JsonResponse(textbook, status=201)
    resp["Location"] = reverse("textbook_by_id", kwargs={
        'org': org,
        'course': course,
        'name': name,
        'tid': textbook["id"],
    })
    return resp


@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "DELETE"))
def textbook_by_id(request, org, course, name, tid):
    location = get_location_and_verify_access(request, org, course, name)
    store = get_modulestore(location)
    course_module = store.get_item(location, depth=3)
    matching_id = [tb for tb in course_module.pdf_textbooks
                   if str(tb.get("id")) == str(tid)]
    if matching_id:
        textbook = matching_id[0]
    else:
        textbook = None

    if request.method == 'GET':
        if not textbook:
            return JsonResponse(status=404)
        return JsonResponse(textbook)
    elif request.method == 'POST':
        try:
            new_textbook = validate_textbook_json(request.body)
        except TextbookValidationError as e:
            return JsonResponse({"error": e.message}, status=400)
        new_textbook["id"] = tid
        if textbook:
            i = course_module.pdf_textbooks.index(textbook)
            new_textbooks = course_module.pdf_textbooks[0:i]
            new_textbooks.append(new_textbook)
            new_textbooks.extend(course_module.pdf_textbooks[i+1:])
            course_module.pdf_textbooks = new_textbooks
        else:
            course_module.pdf_textbooks.append(new_textbook)
        store.update_metadata(course_module.location, own_metadata(course_module))
        return JsonResponse(new_textbook, status=201)
    elif request.method == 'DELETE':
        if not textbook:
            return JsonResponse(status=404)
        i = course_module.pdf_textbooks.index(textbook)
        new_textbooks = course_module.pdf_textbooks[0:i]
        new_textbooks.extend(course_module.pdf_textbooks[i+1:])
        course_module.pdf_textbooks = new_textbooks
        store.update_metadata(course_module.location, own_metadata(course_module))
        return JsonResponse()
