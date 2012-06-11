import json
import logging

from lxml import etree

from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect

from fs.osfs import OSFS

from django.conf import settings
from mitxmako.shortcuts import render_to_string, render_to_response

from models import StudentModule
from multicourse import multicourse_settings
from util.views import accepts

import courseware.content_parser as content_parser
import xmodule

log = logging.getLogger("mitx.courseware")

class I4xSystem(object):
    '''
    This is an abstraction such that x_modules can function independent 
    of the courseware (e.g. import into other types of courseware, LMS, 
    or if we want to have a sandbox server for user-contributed content)
    '''
    def __init__(self, ajax_url, track_function, render_function, render_template, filestore=None):
        self.ajax_url = ajax_url
        self.track_function = track_function
        if not filestore: 
            self.filestore = OSFS(settings.DATA_DIR)
        else:
            self.filestore = filestore
            if settings.DEBUG:
                log.info("[courseware.module_render.I4xSystem] filestore path = %s" % filestore)
        self.render_function = render_function
        self.render_template = render_template
        self.exception404 = Http404
        self.DEBUG = settings.DEBUG

    def get(self,attr):			# uniform access to attributes (like etree)
        return self.__dict__.get(attr)
    def set(self,attr,val):		# uniform access to attributes (like etree)
        self.__dict__[attr] = val
    def __repr__(self):
        return repr(self.__dict__)
    def __str__(self):
        return str(self.__dict__)

def object_cache(cache, user, module_type, module_id):
    # We don't look up on user -- all queries include user
    # Additional lookup would require a DB hit the way Django 
    # is broken. 
    for o in cache: 
        if o.module_type == module_type and \
                o.module_id == module_id:
            return o
    return None

def make_track_function(request):
    ''' We want the capa problem (and other modules) to be able to
    track/log what happens inside them without adding dependencies on
    Django or the rest of the codebase. We do this by passing a
    tracking function to them. This generates a closure for each request 
    that gives a clean interface on both sides. 
    '''
    import track.views

    def f(event_type, event):
        return track.views.server_track(request, event_type, event, page='x_module')
    return f

def grade_histogram(module_id):
    ''' Print out a histogram of grades on a given problem. 
        Part of staff member debug info. 
    '''
    from django.db import connection
    cursor = connection.cursor()

    cursor.execute("select courseware_studentmodule.grade,COUNT(courseware_studentmodule.student_id) from courseware_studentmodule where courseware_studentmodule.module_id=%s group by courseware_studentmodule.grade", [module_id])

    grades = list(cursor.fetchall())
    grades.sort(key=lambda x:x[0]) # Probably not necessary
    if (len(grades) == 1 and grades[0][0] is None):
        return []
    return grades

def get_module(user, request, xml_module, module_object_preload, position=None):
    ''' Get the appropriate xmodule and StudentModule.

    Arguments:
      - user                  : current django User
      - request               : current django HTTPrequest
      - xml_module            : lxml etree of xml subtree for the current module
      - module_object_preload : list of StudentModule objects, one of which may match this module type and id
      - position   	      : extra information from URL for user-specified position within module

    Returns:
      - a tuple (xmodule instance, student module, module type).

    '''
    module_type=xml_module.tag
    module_class=xmodule.get_module_class(module_type)
    module_id=xml_module.get('id') #module_class.id_attribute) or "" 

    # Grab state from database
    smod = object_cache(module_object_preload, 
                        user, 
                        module_type, 
                        module_id)

    if not smod: # If nothing in the database...
        state=None
    else:
        state = smod.state

    # get coursename if stored
    coursename = multicourse_settings.get_coursename_from_request(request)

    if coursename and settings.ENABLE_MULTICOURSE:
        xp = multicourse_settings.get_course_xmlpath(coursename)	# path to XML for the course
        data_root = settings.DATA_DIR + xp
    else:
        data_root = settings.DATA_DIR

    # Create a new instance
    ajax_url = settings.MITX_ROOT_URL + '/modx/'+module_type+'/'+module_id+'/'
    
    system = I4xSystem(track_function = make_track_function(request), 
                       render_function = lambda x: render_x_module(user, request, x, module_object_preload, position), 
                       render_template = render_to_string,
                       ajax_url = ajax_url,
                       filestore = OSFS(data_root),
                       )
    system.set('position',position)	# pass URL specified position along to module, through I4xSystem
    instance=module_class(system, 
                          etree.tostring(xml_module), 
                          module_id, 
                          state=state)
    
    # If instance wasn't already in the database, and this
    # isn't a guest user, create it
    if not smod and user.is_authenticated():
        smod=StudentModule(student=user, 
                           module_type = module_type,
                           module_id=module_id, 
                           state=instance.get_state())
        smod.save()
        module_object_preload.append(smod)

    return (instance, smod, module_type)

def render_x_module(user, request, xml_module, module_object_preload, position=None):
    ''' Generic module for extensions. This renders to HTML.

    modules include sequential, vertical, problem, video, html

    Note that modules can recurse.  problems, video, html, can be inside sequential or vertical.

    Arguments:

      - user                  : current django User
      - request               : current django HTTPrequest
      - xml_module            : lxml etree of xml subtree for the current module
      - module_object_preload : list of StudentModule objects, one of which may match this module type and id
      - position   	      : extra information from URL for user-specified position within module

    Returns:

      -  dict which is context for HTML rendering of the specified module

    '''
    if xml_module==None :
        return {"content":""}

    (instance, smod, module_type) = get_module(user, request, xml_module, module_object_preload, position)

    # Grab content
    content = instance.get_html()

    # special extra information about each problem, only for users who are staff 
    if settings.MITX_FEATURES.get('DISPLAY_HISTOGRAMS_TO_STAFF') and user.is_staff:
        module_id = xml_module.get('id')
        histogram = grade_histogram(module_id)
        render_histogram = len(histogram) > 0
        content=content+render_to_string("staff_problem_info.html", {'xml':etree.tostring(xml_module), 
                                                                     'module_id' : module_id,
                                                                     'histogram': json.dumps(histogram),
                                                                     'render_histogram' : render_histogram})

    content = {'content':content,
               'type':module_type}

    return content

def modx_dispatch(request, module=None, dispatch=None, id=None):
    ''' Generic view for extensions. This is where AJAX calls go.

    Arguments:

      - request -- the django request.
      - module -- the name of the module, as used in the course configuration xml.
      - dispatch -- the command string to pass through to the module's handle_ajax call
           (e.g. 'problem_reset').  If this string contains '?', only pass
           through the part before the first '?'.
      - id -- the module id.  Used to look up the student module.

      TODO: why are id and module not the same?
    '''
    if not request.user.is_authenticated():
        return redirect('/')

    # Grab the student information for the module from the database
    s = StudentModule.objects.filter(student=request.user, 
                                     module_id=id)
    #s = StudentModule.get_with_caching(request.user, id)
    if len(s) == 0 or s is None:
        log.debug("Couldnt find module for user and id " + str(module) + " " + str(request.user) + " "+ str(id))
        raise Http404
    s = s[0]

    oldgrade = s.grade
    oldstate = s.state

    # TODO: if dispatch is left at default value None, this will go boom.  What's the correct
    # behavior?
    dispatch=dispatch.split('?')[0]

    ajax_url = settings.MITX_ROOT_URL + '/modx/'+module+'/'+id+'/'

    # get coursename if stored
    coursename = multicourse_settings.get_coursename_from_request(request)

    if coursename and settings.ENABLE_MULTICOURSE:
        xp = multicourse_settings.get_course_xmlpath(coursename)	# path to XML for the course
        data_root = settings.DATA_DIR + xp
    else:
        data_root = settings.DATA_DIR

    # Grab the XML corresponding to the request from course.xml
    try:
        xml = content_parser.module_xml(request.user, module, 'id', id, coursename)
    except:
        log.exception("Unable to load module during ajax call. module=%s, dispatch=%s, id=%s" % (module, dispatch, id))
        if accepts(request, 'text/html'):
            return render_to_response("module-error.html", {})
        else:
            response = HttpResponse(json.dumps({'success': "We're sorry, this module is temporarily unavailable. Our staff is working to fix it as soon as possible"}))
        return response

    # Create the module
    system = I4xSystem(track_function = make_track_function(request), 
                       render_function = None, 
                       render_template = render_to_string,
                       ajax_url = ajax_url,
                       filestore = OSFS(data_root),
                       )

    try:
        instance=xmodule.get_module_class(module)(system, 
                                                             xml, 
                                                             id, 
                                                             state=oldstate)
    except:
        log.exception("Unable to load module instance during ajax call")
        if accepts(request, 'text/html'):
            return render_to_response("module-error.html", {})
        else:
            response = HttpResponse(json.dumps({'success': "We're sorry, this module is temporarily unavailable. Our staff is working to fix it as soon as possible"}))
        return response

    # Let the module handle the AJAX
    ajax_return=instance.handle_ajax(dispatch, request.POST)
    # Save the state back to the database
    s.state=instance.get_state()
    if instance.get_score(): 
        s.grade=instance.get_score()['score']
    if s.grade != oldgrade or s.state != oldstate:
        s.save()
    # Return whatever the module wanted to return to the client/caller
    return HttpResponse(ajax_return)
