import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'docs.db',
    }
}

SECRET_KEY = 'HASJFDYWQ98r6y2hesakjfhakjfy87eyr1hakjwfa'
CACHE_BACKEND = 'locmem://'
LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
ADMINS = [
    ('Example Admin', 'admin@example.com'),
]

# Set this in order to bypass code that auto-fills the database with
# SCMTool data.
RUNNING_TEST = True
