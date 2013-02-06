import logging
import re

from staticfiles.storage import staticfiles_storage
from staticfiles import finders
from django.conf import settings

from xmodule.modulestore.django import modulestore
from xmodule.modulestore.xml import XMLModuleStore
from xmodule.contentstore.content import StaticContent

log = logging.getLogger(__name__)


def _url_replace_regex(prefix):
    return r"""
        (?x)                 # flags=re.VERBOSE
        (?P<quote>\\?['"])   # the opening quotes
        (?P<prefix>{prefix}) # theeprefix
        (?P<rest>.*?)        # everything else in the url
        (?P=quote)           # the first matching closing quote
        """.format(prefix=prefix)


def try_staticfiles_lookup(path):
    """
    Try to lookup a path in staticfiles_storage.  If it fails, return
    a dead link instead of raising an exception.
    """
    try:
        url = staticfiles_storage.url(path)
    except Exception as err:
        log.warning("staticfiles_storage couldn't find path {0}: {1}".format(
            path, str(err)))
        # Just return the original path; don't kill everything.
        url = path
    return url


def replace_course_urls(text, course_id):
    """
    Replace /course/$stuff urls with /courses/$course_id/$stuff urls

    text: The text to replace
    course_module: A CourseDescriptor

    returns: text with the links replaced
    """


    def replace_course_url(match):
        quote = match.group('quote')
        rest = match.group('rest')
        return "".join([quote, '/courses/' + course_id + '/', rest, quote])

    return re.sub(_url_replace_regex('/course/'), replace_course_url, text)


def replace_static_urls(text, data_directory, course_namespace=None):
    """
    Replace /static/$stuff urls either with their correct url as generated by collectstatic,
    (/static/$md5_hashed_stuff) or by the course-specific content static url
    /static/$course_data_dir/$stuff, or, if course_namespace is not None, by the
    correct url in the contentstore (c4x://)

    text: The source text to do the substitution in
    data_directory: The directory in which course data is stored
    course_namespace: The course identifier used to distinguish static content for this course in studio
    """

    def replace_static_url(match):
        original = match.group(0)
        prefix = match.group('prefix')
        quote = match.group('quote')
        rest = match.group('rest')

        # course_namespace is not None, then use studio style urls
        if course_namespace is not None and not isinstance(modulestore(), XMLModuleStore):
            url = StaticContent.convert_legacy_static_url(rest, course_namespace)
        # If we're in debug mode, and the file as requested exists, then don't change the links
        elif (settings.DEBUG and finders.find(rest, True)):
            return original
        # Otherwise, look the file up in staticfiles_storage without the data directory
        else:
            try:
                url = staticfiles_storage.url(rest)
            # And if that fails, assume that it's course content, and add manually data directory
            except Exception as err:
                log.warning("staticfiles_storage couldn't find path {0}: {1}".format(
                    rest, str(err)))
                url = "".join([prefix, data_directory, '/', rest])

        return "".join([quote, url, quote])

    return re.sub(
        _url_replace_regex('/static/(?!{data_dir})'.format(data_dir=data_directory)),
        replace_static_url,
        text
    )
