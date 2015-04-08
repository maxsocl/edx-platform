""" Code to allow module store to interface with courseware index """
from __future__ import absolute_import

from datetime import timedelta
import logging

from django.conf import settings
from django.utils.translation import ugettext as _
from eventtracking import tracker
from xmodule.modulestore import ModuleStoreEnum
from search.search_engine_base import SearchEngine

# REINDEX_AGE is the default amount of time that we look back for changes
# that might have happened. If we are provided with a time at which the
# indexing is triggered, then we know it is safe to only index items
# recently changed at that time. This is the time period that represents
# how far back from the trigger point to look back in order to index
REINDEX_AGE = timedelta(0, 60)  # 60 seconds

log = logging.getLogger('edx.modulestore')


class SearchIndexingError(Exception):
    """ Indicates some error(s) occured during indexing """

    def __init__(self, message, error_list):
        super(SearchIndexingError, self).__init__(message)
        self.error_list = error_list


class SearchIndexBase(object):
    """
    Class to perform indexing for courseware search from different modulestores
    """

    INDEX_NAME = None
    DOCUMENT_TYPE = None
    ENABLE_INDEXING_KEY = None

    INDEX_EVENT = {
        'name': None,
        'category': None
    }

    @classmethod
    def indexing_is_enabled(cls):
        """
        Checks to see if the indexing feature is enabled
        """
        return settings.FEATURES.get(cls.ENABLE_INDEXING_KEY, False)

    @classmethod
    def _fetch_top_level(self, modulestore, structure_key):
        """ Fetch the item from the modulestore location """
        raise NotImplementedError("Should be overridden in child classes")

    @classmethod
    def _get_location_info(self, structure_key):
        """ Builds location info dictionary """
        raise NotImplementedError("Should be overridden in child classes")

    @classmethod
    def _id_modifier(self, usage_id):
        """ Modifies usage_id to submit to index """
        return usage_id

    @classmethod
    def remove_deleted_items(cls, searcher, structure_key, exclude_items):
        """
        remove any item that is present in the search index that is not present in updated list of indexed items
        as we find items we can shorten the set of items to keep
        """
        response = searcher.search(
            doc_type=cls.DOCUMENT_TYPE,
            field_dictionary=cls._get_location_info(structure_key),
            exclude_ids=exclude_items
        )
        result_ids = [result["data"]["id"] for result in response["results"]]
        for result_id in result_ids:
            searcher.remove(cls.DOCUMENT_TYPE, result_id)

    @classmethod
    def index(cls, modulestore, structure_key, triggered_at=None, reindex_age=REINDEX_AGE):
        """
        Process course for indexing

        Arguments:
        structure_key (CourseKey|LibraryKey) - course or library identifier

        triggered_at (datetime) - provides time at which indexing was triggered;
            useful for index updates - only things changed recently from that date
            (within REINDEX_AGE above ^^) will have their index updated, others skip
            updating their index but are still walked through in order to identify
            which items may need to be removed from the index
            If None, then a full reindex takes place

        Returns:
        Number of items that have been added to the index
        """
        error_list = []
        searcher = SearchEngine.get_search_engine(cls.INDEX_NAME)
        if not searcher:
            return

        location_info = cls._get_location_info(structure_key)

        # Wrap counter in dictionary - otherwise we seem to lose scope inside the embedded function `index_item`
        indexed_count = {
            "count": 0
        }

        # indexed_items is a list of all the items that we wish to remain in the
        # index, whether or not we are planning to actually update their index.
        # This is used in order to build a query to remove those items not in this
        # list - those are ready to be destroyed
        indexed_items = set()

        def index_item(item, skip_index=False):
            """
            Add this item to the search index and indexed_items list

            Arguments:
            item - item to add to index, its children will be processed recursively

            skip_index - simply walk the children in the tree, the content change is
                older than the REINDEX_AGE window and would have been already indexed.
                This should really only be passed from the recursive child calls when
                this method has determined that it is safe to do so
            """
            is_indexable = hasattr(item, "index_dictionary")
            item_index_dictionary = item.index_dictionary() if is_indexable else None
            # if it's not indexable and it does not have children, then ignore
            if not item_index_dictionary and not item.has_children:
                return

            item_id = unicode(cls._id_modifier(item.scope_ids.usage_id))
            indexed_items.add(item_id)
            if item.has_children:
                # determine if it's okay to skip adding the children herein based upon how recently any may have changed
                skip_child_index = skip_index or \
                    (triggered_at is not None and (triggered_at - item.subtree_edited_on) > reindex_age)
                for child_item in item.get_children():
                    index_item(child_item, skip_index=skip_child_index)

            if skip_index or not item_index_dictionary:
                return

            item_index = {}
            # if it has something to add to the index, then add it
            try:
                item_index.update(location_info)
                item_index.update(item_index_dictionary)
                item_index['id'] = item_id
                if item.start:
                    item_index['start_date'] = item.start

                searcher.index(cls.DOCUMENT_TYPE, item_index)
                indexed_count["count"] += 1
            except Exception as err:  # pylint: disable=broad-except
                # broad exception so that index operation does not fail on one item of many
                log.warning('Could not index item: %s - %r', item.location, err)
                error_list.append(_('Could not index item: {}').format(item.location))

        try:
            with modulestore.branch_setting(ModuleStoreEnum.RevisionOption.published_only):
                structure = cls._fetch_top_level(modulestore, structure_key)
                for item in structure.get_children():
                    index_item(item)
                cls.remove_deleted_items(searcher, structure_key, indexed_items)
        except Exception as err:  # pylint: disable=broad-except
            # broad exception so that index operation does not prevent the rest of the application from working
            log.exception(
                "Indexing error encountered, courseware index may be out of date %s - %r",
                structure_key,
                err
            )
            error_list.append(_('General indexing error occurred'))

        if error_list:
            raise SearchIndexingError('Error(s) present during indexing', error_list)

        return indexed_count["count"]

    @classmethod
    def _do_reindex(cls, modulestore, structure_key):
        """
        (Re)index all content within the given structure (course or library),
        tracking the fact that a full reindex has taken place
        """
        indexed_count = cls.index(modulestore, structure_key)
        if indexed_count:
            cls._track_index_request(cls.INDEX_EVENT['name'], cls.INDEX_EVENT['category'], indexed_count)
        return indexed_count

    @classmethod
    def _track_index_request(cls, event_name, category, indexed_count):
        """Track content index requests.

        Arguments:
            event_name (str):  Name of the event to be logged.
            category (str): cat3gory of indexed items
            indexed_count (int): number of indexed items
        Returns:
            None

        """
        data = {
            "indexed_count": indexed_count,
            'category': category,
        }

        tracker.emit(
            event_name,
            data
        )


class CoursewareSearchIndexer(SearchIndexBase):
    INDEX_NAME = "courseware_index"
    DOCUMENT_TYPE = "courseware_content"
    ENABLE_INDEXING_KEY = 'ENABLE_COURSEWARE_INDEX'

    INDEX_EVENT = {
        'name': 'edx.course.index.reindexed',
        'category': 'courseware_index'
    }

    @classmethod
    def _fetch_top_level(self, modulestore, structure_key):
        """ Fetch the item from the modulestore location """
        return modulestore.get_course(structure_key, depth=None)

    @classmethod
    def _get_location_info(self, structure_key):
        """ Builds location info dictionary """
        return {"course": unicode(structure_key)}

    @classmethod
    def do_course_reindex(cls, modulestore, course_key):
        """
        (Re)index all content within the given course, tracking the fact that a full reindex has taken place
        """
        return cls._do_reindex(modulestore, course_key)


class LibrarySearchIndexer(SearchIndexBase):
    INDEX_NAME = "library_index"
    DOCUMENT_TYPE = "library_content"
    ENABLE_INDEXING_KEY = 'ENABLE_LIBRARY_INDEX'

    INDEX_EVENT = {
        'name': 'edx.library.index.reindexed',
        'category': 'library_index'
    }

    @classmethod
    def _fetch_top_level(self, modulestore, structure_key):
        """ Fetch the item from the modulestore location """
        return modulestore.get_library(structure_key, depth=None)

    @classmethod
    def _get_location_info(self, structure_key):
        """ Builds location info dictionary """
        return {"library": unicode(structure_key.replace(version_guid=None, branch=None))}

    @classmethod
    def _id_modifier(self, usage_id):
        """ Modifies usage_id to submit to index """
        return usage_id.replace(library_key=(usage_id.library_key.replace(version_guid=None, branch=None)))

    @classmethod
    def do_library_reindex(cls, modulestore, library_key):
        """
        (Re)index all content within the given library, tracking the fact that a full reindex has taken place
        """
        return cls._do_reindex(modulestore, library_key)