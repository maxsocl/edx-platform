import logging
import yaml
import os

from lxml import etree
from pprint import pprint
from collections import namedtuple
from pkg_resources import resource_listdir, resource_string, resource_isdir

from xmodule.modulestore import Location

from .model import ModelMetaclass, ParentModelMetaclass, NamespacesMetaclass
from .plugin import Plugin


class XModuleMetaclass(ParentModelMetaclass, NamespacesMetaclass, ModelMetaclass):
    pass

log = logging.getLogger(__name__)


def dummy_track(event_type, event):
    pass


class HTMLSnippet(object):
    """
    A base class defining an interface for an object that is able to present an
    html snippet, along with associated javascript and css
    """

    js = {}
    js_module_name = None

    css = {}

    @classmethod
    def get_javascript(cls):
        """
        Return a dictionary containing some of the following keys:

            coffee: A list of coffeescript fragments that should be compiled and
                    placed on the page

            js: A list of javascript fragments that should be included on the
            page

        All of these will be loaded onto the page in the CMS
        """
        # cdodge: We've moved the xmodule.coffee script from an outside directory into the xmodule area of common
        # this means we need to make sure that all xmodules include this dependency which had been previously implicitly 
        # fulfilled in a different area of code
        js = cls.js
        
        if js is None:
            js = {}

        if 'coffee' not in js:
            js['coffee'] = []
        
        js['coffee'].append(resource_string(__name__, 'js/src/xmodule.coffee'))

        return js

    @classmethod
    def get_css(cls):
        """
        Return a dictionary containing some of the following keys:

            css: A list of css fragments that should be applied to the html
                 contents of the snippet

            sass: A list of sass fragments that should be applied to the html
                  contents of the snippet

            scss: A list of scss fragments that should be applied to the html
                  contents of the snippet
        """
        return cls.css

    def get_html(self):
        """
        Return the html used to display this snippet
        """
        raise NotImplementedError(
            "get_html() must be provided by specific modules - not present in {0}"
                                  .format(self.__class__))


class XModule(HTMLSnippet):
    ''' Implements a generic learning module.

        Subclasses must at a minimum provide a definition for get_html in order
        to be displayed to users.

        See the HTML module for a simple example.
    '''

    __metaclass__ = XModuleMetaclass

    # The default implementation of get_icon_class returns the icon_class
    # attribute of the class
    #
    # This attribute can be overridden by subclasses, and
    # the function can also be overridden if the icon class depends on the data
    # in the module
    icon_class = 'other'

    def __init__(self, system, location, descriptor, model_data):
        '''
        Construct a new xmodule

        system: A ModuleSystem allowing access to external resources

        location: Something Location-like that identifies this xmodule

        definition: A dictionary containing 'data' and 'children'. Both are
        optional

            'data': is JSON-like (string, dictionary, list, bool, or None,
                optionally nested).

                This defines all of the data necessary for a problem to display
                that is intrinsic to the problem.  It should not include any
                data that would vary between two courses using the same problem
                (due dates, grading policy, randomization, etc.)

            'children': is a list of Location-like values for child modules that
                this module depends on

        descriptor: the XModuleDescriptor that this module is an instance of.
            TODO (vshnayder): remove the definition parameter and location--they
            can come from the descriptor.

        instance_state: A string of serialized json that contains the state of
                this module for current student accessing the system, or None if
                no state has been saved

        shared_state: A string of serialized json that contains the state that
            is shared between this module and any modules of the same type with
            the same shared_state_key. This state is only shared per-student,
            not across different students

        kwargs: Optional arguments. Subclasses should always accept kwargs and
            pass them to the parent class constructor.

            Current known uses of kwargs:

                metadata: SCAFFOLDING - This dictionary will be split into
                    several different types of metadata in the future (course
                    policy, modification history, etc).  A dictionary containing
                    data that specifies information that is particular to a
                    problem in the context of a course
        '''
        self.system = system
        self.location = Location(location)
        self.descriptor = descriptor
        self.id = self.location.url()
        self.url_name = self.location.name
        self.category = self.location.category
        self._model_data = model_data
        self._loaded_children = None

    def get_children(self):
        '''
        Return module instances for all the children of this module.
        '''
        if not self.has_children:
            return []

        if self._loaded_children is None:
            children = [self.system.get_module(loc) for loc in self.children]
            # get_module returns None if the current user doesn't have access
            # to the location.
            self._loaded_children = [c for c in children if c is not None]

        return self._loaded_children

    def __unicode__(self):
        return '<x_module(id={0})>'.format(self.id)

    def get_display_items(self):
        '''
        Returns a list of descendent module instances that will display
        immediately inside this module.
        '''
        items = []
        for child in self.get_children():
            items.extend(child.displayable_items())

        return items

    def displayable_items(self):
        '''
        Returns list of displayable modules contained by this module. If this
        module is visible, should return [self].
        '''
        return [self]

    def get_icon_class(self):
        '''
        Return a css class identifying this module in the context of an icon
        '''
        return self.icon_class

    ### Functions used in the LMS

    def get_score(self):
        ''' Score the student received on the problem.
        '''
        return None

    def max_score(self):
        ''' Maximum score. Two notes:

            * This is generic; in abstract, a problem could be 3/5 points on one
              randomization, and 5/7 on another

            * In practice, this is a Very Bad Idea, and (a) will break some code
              in place (although that code should get fixed), and (b) break some
              analytics we plan to put in place.
        '''
        return None

    def get_progress(self):
        ''' Return a progress.Progress object that represents how far the
        student has gone in this module.  Must be implemented to get correct
        progress tracking behavior in nesting modules like sequence and
        vertical.

        If this module has no notion of progress, return None.
        '''
        return None

    def handle_ajax(self, dispatch, get):
        ''' dispatch is last part of the URL.
            get is a dictionary-like object '''
        return ""


def policy_key(location):
    """
    Get the key for a location in a policy file.  (Since the policy file is
    specific to a course, it doesn't need the full location url).
    """
    return '{cat}/{name}'.format(cat=location.category, name=location.name)


Template = namedtuple("Template", "metadata data children")


class ResourceTemplates(object):
    @classmethod
    def templates(cls):
        """
        Returns a list of Template objects that describe possible templates that can be used
        to create a module of this type.
        If no templates are provided, there will be no way to create a module of
        this type

        Expects a class attribute template_dir_name that defines the directory
        inside the 'templates' resource directory to pull templates from
        """
        templates = []
        dirname = os.path.join('templates', cls.template_dir_name)
        if not resource_isdir(__name__, dirname):
            log.warning("No resource directory {dir} found when loading {cls_name} templates".format(
                dir=dirname,
                cls_name=cls.__name__,
            ))
            return []

        for template_file in resource_listdir(__name__, dirname):
            if not template_file.endswith('.yaml'):
                log.warning("Skipping unknown template file %s" % template_file)
                continue
            template_content = resource_string(__name__, os.path.join(dirname, template_file))
            template = yaml.load(template_content)
            templates.append(Template(**template))

        return templates


class XModuleDescriptor(Plugin, HTMLSnippet, ResourceTemplates):
    """
    An XModuleDescriptor is a specification for an element of a course. This
    could be a problem, an organizational element (a group of content), or a
    segment of video, for example.

    XModuleDescriptors are independent and agnostic to the current student state
    on a problem. They handle the editing interface used by instructors to
    create a problem, and can generate XModules (which do know about student
    state).
    """
    entry_point = "xmodule.v1"
    module_class = XModule
    __metaclass__ = XModuleMetaclass

    # Attributes for inspection of the descriptor
    stores_state = False  # Indicates whether the xmodule state should be
    # stored in a database (independent of shared state)
    has_score = False  # This indicates whether the xmodule is a problem-type.
    # It should respond to max_score() and grade(). It can be graded or ungraded
    # (like a practice problem).

    # A list of metadata that this module can inherit from its parent module
    inheritable_metadata = (
        'graded', 'start', 'due', 'graceperiod', 'showanswer', 'rerandomize',
        # TODO (ichuang): used for Fall 2012 xqa server access
        'xqa_key',
        # TODO: This is used by the XMLModuleStore to provide for locations for
        # static files, and will need to be removed when that code is removed
        'data_dir'
    )

    # cdodge: this is a list of metadata names which are 'system' metadata
    # and should not be edited by an end-user
    system_metadata_fields = ['data_dir', 'published_date', 'published_by', 'is_draft']
    
    # A list of descriptor attributes that must be equal for the descriptors to
    # be equal
    equality_attributes = ('definition', 'metadata', 'location',
                           'shared_state_key', '_inherited_metadata')

    # Name of resource directory to load templates from
    template_dir_name = "default"

    # ============================= STRUCTURAL MANIPULATION ===================
    def __init__(self,
                 system,
                 location,
                 model_data):
        """
        Construct a new XModuleDescriptor. The only required arguments are the
        system, used for interaction with external resources, and the
        definition, which specifies all the data needed to edit and display the
        problem (but none of the associated metadata that handles recordkeeping
        around the problem).

        This allows for maximal flexibility to add to the interface while
        preserving backwards compatibility.

        system: A DescriptorSystem for interacting with external resources

        definition: A dict containing `data` and `children` representing the
        problem definition

        Current arguments passed in kwargs:

            location: A xmodule.modulestore.Location object indicating the name
                and ownership of this problem

            shared_state_key: The key to use for sharing StudentModules with
                other modules of this type

            metadata: A dictionary containing the following optional keys:
                goals: A list of strings of learning goals associated with this
                    module
                url_name: The name to use for this module in urls and other places
                    where a unique name is needed.
                format: The format of this module ('Homework', 'Lab', etc)
                graded (bool): Whether this module is should be graded or not
                start (string): The date for which this module will be available
                due (string): The due date for this module
                graceperiod (string): The amount of grace period to allow when
                    enforcing the due date
                showanswer (string): When to show answers for this module
                rerandomize (string): When to generate a newly randomized
                    instance of the module data
        """
        self.system = system
        self.location = Location(location)
        self.url_name = self.location.name
        self.category = self.location.category
        self._model_data = model_data

        self._child_instances = None
        self._inherited_metadata = set()
        self._child_instances = None

    def get_children(self):
        """Returns a list of XModuleDescriptor instances for the children of
        this module"""
        if not self.has_children:
            return []

        if self._child_instances is None:
            self._child_instances = []
            for child_loc in self.children:
                try:
                    child = self.system.load_item(child_loc)
                except ItemNotFoundError:
                    log.exception('Unable to load item {loc}, skipping'.format(loc=child_loc))
                    continue
                self._child_instances.append(child)

        return self._child_instances

    def get_child_by_url_name(self, url_name):
        """
        Return a child XModuleDescriptor with the specified url_name, if it exists, and None otherwise.
        """
        for c in self.get_children():
            if c.url_name == url_name:
                return c
        return None

    def xmodule(self, system):
        """
        Returns a constructor for an XModule. This constructor takes two
        arguments: instance_state and shared_state, and returns a fully
        instantiated XModule
        """
        return self.module_class(
            system,
            self.location,
            self,
            system.xmodule_model_data(self._model_data),
        )
    
    def has_dynamic_children(self):
        """
        Returns True if this descriptor has dynamic children for a given
        student when the module is created.
        
        Returns False if the children of this descriptor are the same
        children that the module will return for any student. 
        """
        return False
        

    # ================================= JSON PARSING ===========================
    @staticmethod
    def load_from_json(json_data, system, default_class=None):
        """
        This method instantiates the correct subclass of XModuleDescriptor based
        on the contents of json_data.

        json_data must contain a 'location' element, and must be suitable to be
        passed into the subclasses `from_json` method.
        """
        class_ = XModuleDescriptor.load_class(
            json_data['location']['category'],
            default_class
        )
        return class_.from_json(json_data, system)

    @classmethod
    def from_json(cls, json_data, system):
        """
        Creates an instance of this descriptor from the supplied json_data.
        This may be overridden by subclasses

        json_data: A json object specifying the definition and any optional
            keyword arguments for the XModuleDescriptor

        system: A DescriptorSystem for interacting with external resources
        """
        return cls(system=system, **json_data)

    # ================================= XML PARSING ============================
    @staticmethod
    def load_from_xml(xml_data,
            system,
            org=None,
            course=None,
            default_class=None):
        """
        This method instantiates the correct subclass of XModuleDescriptor based
        on the contents of xml_data.

        xml_data must be a string containing valid xml

        system is an XMLParsingSystem

        org and course are optional strings that will be used in the generated
            module's url identifiers
        """
        class_ = XModuleDescriptor.load_class(
            etree.fromstring(xml_data).tag,
            default_class
            )
        # leave next line, commented out - useful for low-level debugging
        # log.debug('[XModuleDescriptor.load_from_xml] tag=%s, class_=%s' % (
        #        etree.fromstring(xml_data).tag,class_))

        return class_.from_xml(xml_data, system, org, course)

    @classmethod
    def from_xml(cls, xml_data, system, org=None, course=None):
        """
        Creates an instance of this descriptor from the supplied xml_data.
        This may be overridden by subclasses

        xml_data: A string of xml that will be translated into data and children
            for this module

        system is an XMLParsingSystem

        org and course are optional strings that will be used in the generated
            module's url identifiers
        """
        raise NotImplementedError(
            'Modules must implement from_xml to be parsable from xml')

    def export_to_xml(self, resource_fs):
        """
        Returns an xml string representing this module, and all modules
        underneath it.  May also write required resources out to resource_fs

        Assumes that modules have single parentage (that no module appears twice
        in the same course), and that it is thus safe to nest modules as xml
        children as appropriate.

        The returned XML should be able to be parsed back into an identical
        XModuleDescriptor using the from_xml method with the same system, org,
        and course
        """
        raise NotImplementedError(
            'Modules must implement export_to_xml to enable xml export')

    # =============================== Testing ==================================
    def get_sample_state(self):
        """
        Return a list of tuples of instance_state, shared_state. Each tuple
        defines a sample case for this module
        """
        return [('{}', '{}')]

    # =============================== BUILTIN METHODS ==========================
    def __eq__(self, other):
        eq = (self.__class__ == other.__class__ and
                all(getattr(self, attr, None) == getattr(other, attr, None)
                    for attr in self.equality_attributes))

        if not eq:
            for attr in self.equality_attributes:
                pprint((getattr(self, attr, None),
                       getattr(other, attr, None),
                       getattr(self, attr, None) == getattr(other, attr, None)))

        return eq

    def __repr__(self):
        return ("{class_}({system!r}, location={location!r},"
                " model_data={model_data!r})".format(
            class_=self.__class__.__name__,
            system=self.system,
            location=self.location,
            model_data=self._model_data,
        ))



class DescriptorSystem(object):
    def __init__(self, load_item, resources_fs, error_tracker, **kwargs):
        """
        load_item: Takes a Location and returns an XModuleDescriptor

        resources_fs: A Filesystem object that contains all of the
            resources needed for the course

        error_tracker: A hook for tracking errors in loading the descriptor.
            Used for example to get a list of all non-fatal problems on course
            load, and display them to the user.

            A function of (error_msg). errortracker.py provides a
            handy make_error_tracker() function.

            Patterns for using the error handler:
               try:
                  x = access_some_resource()
                  check_some_format(x)
               except SomeProblem as err:
                  msg = 'Grommet {0} is broken: {1}'.format(x, str(err))
                  log.warning(msg)  # don't rely on tracker to log
                        # NOTE: we generally don't want content errors logged as errors
                  self.system.error_tracker(msg)
                  # work around
                  return 'Oops, couldn't load grommet'

               OR, if not in an exception context:

               if not check_something(thingy):
                  msg = "thingy {0} is broken".format(thingy)
                  log.critical(msg)
                  self.system.error_tracker(msg)

               NOTE: To avoid duplication, do not call the tracker on errors
               that you're about to re-raise---let the caller track them.
        """

        self.load_item = load_item
        self.resources_fs = resources_fs
        self.error_tracker = error_tracker


class XMLParsingSystem(DescriptorSystem):
    def __init__(self, load_item, resources_fs, error_tracker, process_xml, policy, **kwargs):
        """
        load_item, resources_fs, error_tracker: see DescriptorSystem

        policy: a policy dictionary for overriding xml metadata

        process_xml: Takes an xml string, and returns a XModuleDescriptor
            created from that xml
        """
        DescriptorSystem.__init__(self, load_item, resources_fs, error_tracker,
                                  **kwargs)
        self.process_xml = process_xml
        self.policy = policy


class ModuleSystem(object):
    '''
    This is an abstraction such that x_modules can function independent
    of the courseware (e.g. import into other types of courseware, LMS,
    or if we want to have a sandbox server for user-contributed content)

    ModuleSystem objects are passed to x_modules to provide access to system
    functionality.

    Note that these functions can be closures over e.g. a django request
    and user, or other environment-specific info.
    '''
    def __init__(self,
                 ajax_url,
                 track_function,
                 get_module,
                 render_template,
                 replace_urls,
                 xmodule_model_data,
                 user=None,
                 filestore=None,
                 debug=False,
                 xqueue=None,
                 node_path="",
                 anonymous_student_id=''):
        '''
        Create a closure around the system environment.

        ajax_url - the url where ajax calls to the encapsulating module go.

        track_function - function of (event_type, event), intended for logging
                         or otherwise tracking the event.
                         TODO: Not used, and has inconsistent args in different
                         files.  Update or remove.

        get_module - function that takes (location) and returns a corresponding
                         module instance object.  If the current user does not have
                         access to that location, returns None.

        render_template - a function that takes (template_file, context), and
                         returns rendered html.

        user - The user to base the random number generator seed off of for this
                         request

        filestore - A filestore ojbect.  Defaults to an instance of OSFS based
                         at settings.DATA_DIR.

        xqueue - Dict containing XqueueInterface object, as well as parameters
                    for the specific StudentModule:
                    xqueue = {'interface': XQueueInterface object,
                              'callback_url': Callback into the LMS,
                              'queue_name': Target queuename in Xqueue}

        replace_urls - TEMPORARY - A function like static_replace.replace_urls
                         that capa_module can use to fix up the static urls in
                         ajax results.

        anonymous_student_id - Used for tracking modules with student id
        '''
        self.ajax_url = ajax_url
        self.xqueue = xqueue
        self.track_function = track_function
        self.filestore = filestore
        self.get_module = get_module
        self.render_template = render_template
        self.DEBUG = self.debug = debug
        self.seed = user.id if user is not None else 0
        self.replace_urls = replace_urls
        self.node_path = node_path
        self.anonymous_student_id = anonymous_student_id
        self.user_is_staff = user is not None and user.is_staff
        self.xmodule_model_data = xmodule_model_data

    def get(self, attr):
        '''	provide uniform access to attributes (like etree).'''
        return self.__dict__.get(attr)

    def set(self, attr, val):
        '''provide uniform access to attributes (like etree)'''
        self.__dict__[attr] = val

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return str(self.__dict__)
