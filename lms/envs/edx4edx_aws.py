# Settings for edx4edx production instance
from .aws import *
COURSE_NAME = "edx4edx"
COURSE_NUMBER = "edX.01"
COURSE_TITLE = "edx4edx: edX Author Course"
EDX4EDX_ROOT = ENV_ROOT / "data/edx4edx"

### Dark code. Should be enabled in local settings for devel. 
QUICKEDIT = True
ENABLE_MULTICOURSE = True # set to False to disable multicourse display (see lib.util.views.mitxhome)
###
PIPELINE_CSS_COMPRESSOR = None
PIPELINE_JS_COMPRESSOR = None

COURSE_DEFAULT = 'edx4edx'
COURSE_SETTINGS =  {'edx4edx': {'number' : 'edX.01',
                                    'title'  : 'edx4edx: edX Author Course',
                                    'xmlpath': '/edx4edx/',
                                    'github_url': 'https://github.com/MITx/edx4edx',
                                    'active' : True,
                                    },
                    }

STATICFILES_DIRS = [
    PROJECT_ROOT / "static",
    ASKBOT_ROOT / "askbot" / "skins",
    ("edx4edx", EDX4EDX_ROOT / "html"),
    ("circuits", DATA_DIR / "images"),
    ("handouts", DATA_DIR / "handouts"),
    ("subs", DATA_DIR / "subs"),

# This is how you would use the textbook images locally
#    ("book", ENV_ROOT / "book_images")
]

MAKO_TEMPLATES['course'] = [DATA_DIR, EDX4EDX_ROOT ]
