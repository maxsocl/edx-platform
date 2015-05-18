"""
Script for collecting a list of videos that are not set to download.

On default mongo, it collects all videos. On split mongo, collects videos on published courses.

"""
from bson.objectid import ObjectId
from pymongo import MongoClient

# video_download_allowed = False  # Change this var to look for video downloads set to true or false
client = MongoClient()
db = client['edxapp']


def clean_file(filename):
    """
    Remove given file and start a new csv
    """
    with open(filename, 'w') as f:
        f.write("org\tcourse_name\tvideo_id\tvideo_display_name\tvideo_download_allowed\thtml5_sources\n")


def get_set_metadata_field(field, mongo_doc):
    """
    Will return "None" if the given metadata field is not set. Otherwise, return the field's value.
    """
    if field in mongo_doc[u'metadata']:
        return mongo_doc[u'metadata'][field]
    else:
        return "None"


def get_draft_mongo_data(video_download_allowed=False):
    """
    Via mongo queries, produce a list of videos that are flagged with download as False
    """
    # Old modulestore
    # Will produce a tsv with org, course name, and video GUID
    with open(filename_default_mongo, 'a') as output_file:
        for i in db['modulestore'].find(
                {"metadata.download_video" : video_download_allowed, "_id.revision": None},
                {"_id.course": 1, "metadata.display_name": 1, "metadata.html5_sources": 1}
        ):
            display_name = get_set_metadata_field(u'display_name', i)
            html5_sources = get_set_metadata_field(u'html5_sources', i)

            output_file.write("{org}\t{course_name}\t{video_id}\t{video_display_name}\t{video_download_allowed}\t{html5_sources}\n".format(
                org=(i[u'_id'][u'org']).encode("utf-8"),
                course_name=(i[u'_id'][u'course']).encode("utf-8"),
                video_id=(i[u'_id']['name']).encode("utf-8"),
                video_display_name=display_name.encode("utf-8"),
                video_download_allowed=video_download_allowed,
                html5_sources=html5_sources
            )
            )


def get_split_mongo_data(video_download_allowed=False):

    published_courses = []
    for i in db['modulestore.active_versions'].find(
            {"versions.published-branch": {"$exists": True}},
            {"_id": 0, "versions.published-branch": 1,
             "course": 1,
             "org": 1}
    ):
        published_courses.append(i)

    for published_course in published_courses:
        # Get all the block sets for a given course as dicts
        for i in db['modulestore.structures'].find(
                {
                    "blocks.fields.download_video": video_download_allowed,
                    "_id": published_course[u'versions'][u'published-branch']
                }
        ):
            # Given one block set, now get all the blocks (could contain multiple video xblocks)
            for b in i[u'blocks']:
                # Given one xblock, only do something with it if it is a video xblock
                # Since the above query returns ALL xblocks, regardless of whether or not they allow downloads for
                # videos, we filter again for download_video == False
                if b[u'block_type'] == u'video' and b[u'fields'][u'download_video'] == video_download_allowed:
                    html5_sources = b[u'fields'][u'html5_sources']
                    with open(filename_split_mongo, 'a') as output_file:
                        output_file.write(
                            "{org}\t{course_name}\t{video_id}\t{video_display_name}\t{video_download_allowed}\t{html5_sources}\n".format(
                                org=(published_course[u'org']).encode("utf-8"),
                                course_name=(published_course[u'course']).encode("utf-8"),
                                video_id=(b[u'block_id']).encode("utf-8"),
                                video_display_name=(b[u'fields'][u'display_name']).encode("utf-8"),
                                video_download_allowed=b[u'fields'][u'download_video'],
                                html5_sources=html5_sources
                            )
                        )

# MAIN

filename_split_mongo = "split_mongo.tsv"
clean_file(filename_split_mongo)

filename_default_mongo = "draft_mongo.tsv"
clean_file(filename_default_mongo)


# Find videos where download is not allowed
get_draft_mongo_data(video_download_allowed=False)
get_split_mongo_data(video_download_allowed=False)

# Find videos where download is allowed
get_draft_mongo_data(video_download_allowed=True)
get_split_mongo_data(video_download_allowed=True)
