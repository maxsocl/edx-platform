"""
Note that for this to work at all, you must have memcached running (or you won't
get shared sessions)
"""
from courses import *

# Move this to a shared file later:
for class_id, db_name in CLASSES_TO_DBS.items():
    DATABASES[class_id] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': path_for_db(db_name)
    }
