import pymongo
import sys
import logging

from bson.son import SON
from collections import namedtuple
from fs.osfs import OSFS
from itertools import repeat
from path import path

from importlib import import_module
from xmodule.errortracker import null_error_tracker, exc_info_to_str
from xmodule.mako_module import MakoDescriptorSystem
from xmodule.x_module import XModuleDescriptor
from xmodule.error_module import ErrorDescriptor
from xmodule.runtime import DbModel, KeyValueStore, InvalidScopeError
from xmodule.model import Scope

from . import ModuleStoreBase, Location
from .draft import DraftModuleStore
from .exceptions import (ItemNotFoundError,
                         DuplicateItemError)
from .inheritance import own_metadata


log = logging.getLogger(__name__)

# TODO (cpennington): This code currently operates under the assumption that
# there is only one revision for each item. Once we start versioning inside the CMS,
# that assumption will have to change


class MongoKeyValueStore(KeyValueStore):
    """
    A KeyValueStore that maps keyed data access to one of the 3 data areas
    known to the MongoModuleStore (data, children, and metadata)
    """
    def __init__(self, data, children, metadata):
        self._data = data
        self._children = children
        self._metadata = metadata

    def get(self, key):
        if key.field_name == 'children':
            return self._children
        elif key.scope == Scope.settings:
            return self._metadata[key.field_name]
        elif key.scope == Scope.content:
            if key.field_name == 'data' and not isinstance(self._data, dict):
                return self._data
            else:
                return self._data[key.field_name]
        else:
            raise InvalidScopeError(key.scope)

    def set(self, key, value):
        if key.field_name == 'children':
            self._children = value
        elif key.scope == Scope.settings:
            self._metadata[key.field_name] = value
        elif key.scope == Scope.content:
            if key.field_name == 'data' and not isinstance(self._data, dict):
                self._data = value
            else:
                self._data[key.field_name] = value
        else:
            raise InvalidScopeError(key.scope)

    def delete(self, key):
        if key.field_name == 'children':
            self._children = []
        elif key.scope == Scope.settings:
            if key.field_name in self._metadata:
                del self._metadata[key.field_name]
        elif key.scope == Scope.content:
            if key.field_name == 'data' and not isinstance(self._data, dict):
                self._data = None
            else:
                del self._data[key.field_name]
        else:
            raise InvalidScopeError(key.scope)


MongoUsage = namedtuple('MongoUsage', 'id, def_id')


class CachingDescriptorSystem(MakoDescriptorSystem):
    """
    A system that has a cache of module json that it will use to load modules
    from, with a backup of calling to the underlying modulestore for more data
    """
    def __init__(self, modulestore, module_data, default_class, resources_fs,
                 error_tracker, render_template):
        """
        modulestore: the module store that can be used to retrieve additional modules

        module_data: a dict mapping Location -> json that was cached from the
            underlying modulestore

        default_class: The default_class to use when loading an
            XModuleDescriptor from the module_data

        resources_fs: a filesystem, as per MakoDescriptorSystem

        error_tracker: a function that logs errors for later display to users

        render_template: a function for rendering templates, as per
            MakoDescriptorSystem
        """
        super(CachingDescriptorSystem, self).__init__(
                self.load_item, resources_fs, error_tracker, render_template)
        self.modulestore = modulestore
        self.module_data = module_data
        self.default_class = default_class
        # cdodge: other Systems have a course_id attribute defined. To keep things consistent, let's
        # define an attribute here as well, even though it's None
        self.course_id = None

    def load_item(self, location):
        location = Location(location)
        json_data = self.module_data.get(location)
        if json_data is None:
            return self.modulestore.get_item(location)
        else:
            # TODO (vshnayder): metadata inheritance is somewhat broken because mongo, doesn't
            # always load an entire course.  We're punting on this until after launch, and then
            # will build a proper course policy framework.
            try:
                class_ = XModuleDescriptor.load_class(
                    json_data['location']['category'],
                    self.default_class
                )
                definition = json_data.get('definition', {})
                kvs = MongoKeyValueStore(
                    definition.get('data', {}),
                    definition.get('children', []),
                    json_data.get('metadata', {}),
                )

                model_data = DbModel(kvs, class_, None, MongoUsage(self.course_id, location))
                return class_(self, location, model_data)
            except:
                log.debug("Failed to load descriptor", exc_info=True)
                return ErrorDescriptor.from_json(
                    json_data,
                    self,
                    error_msg=exc_info_to_str(sys.exc_info())
                )


def location_to_query(location, wildcard=True):
    """
    Takes a Location and returns a SON object that will query for that location.
    Fields in location that are None are ignored in the query

    If `wildcard` is True, then a None in a location is treated as a wildcard
    query. Otherwise, it is searched for literally
    """
    query = SON()
    # Location dict is ordered by specificity, and SON
    # will preserve that order for queries
    for key, val in Location(location).dict().iteritems():
        if wildcard and val is None:
            continue
        query['_id.{key}'.format(key=key)] = val

    return query


class MongoModuleStore(ModuleStoreBase):
    """
    A Mongodb backed ModuleStore
    """

    # TODO (cpennington): Enable non-filesystem filestores
    def __init__(self, host, db, collection, fs_root, render_template,
                 port=27017, default_class=None,
                 error_tracker=null_error_tracker,
                 user=None, password=None, **kwargs):

        ModuleStoreBase.__init__(self)

        self.collection = pymongo.connection.Connection(
            host=host,
            port=port,
            **kwargs
        )[db][collection]

        if user is not None and password is not None:
            self.collection.database.authenticate(user, password)


        # Force mongo to report errors, at the expense of performance
        self.collection.safe = True

        # Force mongo to maintain an index over _id.* that is in the same order
        # that is used when querying by a location
        self.collection.ensure_index(
            zip(('_id.' + field for field in Location._fields), repeat(1)))

        if default_class is not None:
            module_path, _, class_name = default_class.rpartition('.')
            class_ = getattr(import_module(module_path), class_name)
            self.default_class = class_
        else:
            self.default_class = None
        self.fs_root = path(fs_root)
        self.error_tracker = error_tracker
        self.render_template = render_template

    def _clean_item_data(self, item):
        """
        Renames the '_id' field in item to 'location'
        """
        item['location'] = item['_id']
        del item['_id']

    def _cache_children(self, items, depth=0):
        """
        Returns a dictionary mapping Location -> item data, populated with json data
        for all descendents of items up to the specified depth.
        (0 = no descendents, 1 = children, 2 = grandchildren, etc)
        If depth is None, will load all the children.
        This will make a number of queries that is linear in the depth.
        """
        data = {}
        to_process = list(items)
        while to_process and depth is None or depth >= 0:
            children = []
            for item in to_process:
                self._clean_item_data(item)
                children.extend(item.get('definition', {}).get('children', []))
                data[Location(item['location'])] = item

            # Load all children by id. See
            # http://www.mongodb.org/display/DOCS/Advanced+Queries#AdvancedQueries-%24or
            # for or-query syntax
            if children:
                to_process = list(self.collection.find(
                    {'_id': {'$in': [Location(child).dict() for child in children]}}))
            else:
                to_process = []
            # If depth is None, then we just recurse until we hit all the descendents
            if depth is not None:
                depth -= 1

        return data

    def _load_item(self, item, data_cache):
        """
        Load an XModuleDescriptor from item, using the children stored in data_cache
        """
        data_dir = getattr(item, 'data_dir', item['location']['course'])
        root = self.fs_root / data_dir

        if not root.isdir():
            root.mkdir()

        resource_fs = OSFS(root)

        system = CachingDescriptorSystem(
            self,
            data_cache,
            self.default_class,
            resource_fs,
            self.error_tracker,
            self.render_template,
        )
        return system.load_item(item['location'])

    def _load_items(self, items, depth=0):
        """
        Load a list of xmodules from the data in items, with children cached up
        to specified depth
        """
        data_cache = self._cache_children(items, depth)

        return [self._load_item(item, data_cache) for item in items]

    def get_courses(self):
        '''
        Returns a list of course descriptors.
        '''
        # TODO (vshnayder): Why do I have to specify i4x here?
        course_filter = Location("i4x", category="course")
        return self.get_items(course_filter)

    def _find_one(self, location):
        '''Look for a given location in the collection.  If revision is not
        specified, returns the latest.  If the item is not present, raise
        ItemNotFoundError.
        '''
        item = self.collection.find_one(
            location_to_query(location, wildcard=False),
            sort=[('revision', pymongo.ASCENDING)],
        )
        if item is None:
            raise ItemNotFoundError(location)
        return item

    def has_item(self, location):
        """
        Returns True if location exists in this ModuleStore.
        """
        location = Location.ensure_fully_specified(location)
        try:
            self._find_one(location)
            return True
        except ItemNotFoundError:
            return False

    def get_item(self, location, depth=0):
        """
        Returns an XModuleDescriptor instance for the item at location.

        If any segment of the location is None except revision, raises
            xmodule.modulestore.exceptions.InsufficientSpecificationError
        If no object is found at that location, raises
            xmodule.modulestore.exceptions.ItemNotFoundError

        location: a Location object
        depth (int): An argument that some module stores may use to prefetch
            descendents of the queried modules for more efficient results later
            in the request. The depth is counted in the number of
            calls to get_children() to cache. None indicates to cache all descendents.

        """
        location = Location.ensure_fully_specified(location)
        item = self._find_one(location)
        return self._load_items([item], depth)[0]

    def get_instance(self, course_id, location):
        """
        TODO (vshnayder): implement policy tracking in mongo.
        For now, just delegate to get_item and ignore policy.
        """
        return self.get_item(location)

    def get_items(self, location, depth=0):
        items = self.collection.find(
            location_to_query(location),
            sort=[('revision', pymongo.ASCENDING)],
        )

        return self._load_items(list(items), depth)

    def clone_item(self, source, location):
        """
        Clone a new item that is a copy of the item at the location `source`
        and writes it to `location`
        """
        try:
            source_item = self.collection.find_one(location_to_query(source))
            source_item['_id'] = Location(location).dict()
            self.collection.insert(source_item)
            item = self._load_items([source_item])[0]

            # VS[compat] cdodge: This is a hack because static_tabs also have references from the course module, so
            # if we add one then we need to also add it to the policy information (i.e. metadata)
            # we should remove this once we can break this reference from the course to static tabs
            if location.category == 'static_tab':
                course = self.get_course_for_item(item.location)
                existing_tabs = course.tabs or []
                existing_tabs.append({'type':'static_tab', 'name' : item.lms.display_name, 'url_slug' : item.location.name})
                course.tabs = existing_tabs
                self.update_metadata(course.location, course._model_data._kvs._metadata)

            return item
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateItemError(location)


    def get_course_for_item(self, location):
        '''
        VS[compat]
        cdodge: for a given Xmodule, return the course that it belongs to
        NOTE: This makes a lot of assumptions about the format of the course location
        Also we have to assert that this module maps to only one course item - it'll throw an
        assert if not
        This is only used to support static_tabs as we need to be course module aware
        '''

        # @hack! We need to find the course location however, we don't
        # know the 'name' parameter in this context, so we have
        # to assume there's only one item in this query even though we are not specifying a name
        course_search_location = ['i4x', location.org, location.course, 'course', None]
        courses = self.get_items(course_search_location)

        # make sure we found exactly one match on this above course search
        found_cnt = len(courses)
        if found_cnt == 0:
            raise Exception('Could not find course at {0}'.format(course_search_location))

        if found_cnt > 1:
            raise Exception('Found more than one course at {0}. There should only be one!!! Dump = {1}'.format(course_search_location, courses))

        return courses[0]

    def _update_single_item(self, location, update):
        """
        Set update on the specified item, and raises ItemNotFoundError
        if the location doesn't exist
        """

        # See http://www.mongodb.org/display/DOCS/Updating for
        # atomic update syntax
        result = self.collection.update(
            {'_id': Location(location).dict()},
            {'$set': update},
            multi=False,
            upsert=True,
        )
        if result['n'] == 0:
            raise ItemNotFoundError(location)

    def update_item(self, location, data):
        """
        Set the data in the item specified by the location to
        data

        location: Something that can be passed to Location
        data: A nested dictionary of problem data
        """

        self._update_single_item(location, {'definition.data': data})

    def update_children(self, location, children):
        """
        Set the children for the item specified by the location to
        children

        location: Something that can be passed to Location
        children: A list of child item identifiers
        """

        self._update_single_item(location, {'definition.children': children})

    def update_metadata(self, location, metadata):
        """
        Set the metadata for the item specified by the location to
        metadata

        location: Something that can be passed to Location
        metadata: A nested dictionary of module metadata
        """
        # VS[compat] cdodge: This is a hack because static_tabs also have references from the course module, so
        # if we add one then we need to also add it to the policy information (i.e. metadata)
        # we should remove this once we can break this reference from the course to static tabs
        loc = Location(location)
        if loc.category == 'static_tab':
            course = self.get_course_for_item(loc)
            existing_tabs = course.tabs or []
            for tab in existing_tabs:
                if tab.get('url_slug') == loc.name:
                    tab['name'] = metadata.get('display_name')
                    break
            course.tabs = existing_tabs
            self.update_metadata(course.location, own_metadata(course))

        self._update_single_item(location, {'metadata': metadata})

    def delete_item(self, location):
        """
        Delete an item from this modulestore

        location: Something that can be passed to Location
        """
        # VS[compat] cdodge: This is a hack because static_tabs also have references from the course module, so
        # if we add one then we need to also add it to the policy information (i.e. metadata)
        # we should remove this once we can break this reference from the course to static tabs
        if location.category == 'static_tab':
            item = self.get_item(location)
            course = self.get_course_for_item(item.location)
            existing_tabs = course.tabs or []
            course.tabs = [tab for tab in existing_tabs if tab.get('url_slug') != location.name]
            self.update_metadata(course.location, own_metadata(course))

        self.collection.remove({'_id': Location(location).dict()})

    def get_parent_locations(self, location):
        '''Find all locations that are the parents of this location.  Needed
        for path_to_location().

        returns an iterable of things that can be passed to Location.  This may
        be empty if there are no parents.
        '''
        location = Location.ensure_fully_specified(location)
        items = self.collection.find({'definition.children': location.url()},
                                    {'_id': True})
        return [i['_id'] for i in items]

    def get_errored_courses(self):
        """
        This function doesn't make sense for the mongo modulestore, as courses
        are loaded on demand, rather than up front
        """
        return {}


# DraftModuleStore is first, because it needs to intercept calls to MongoModuleStore
class DraftMongoModuleStore(DraftModuleStore, MongoModuleStore):
    pass
