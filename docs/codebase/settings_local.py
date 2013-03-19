import os

SECRET_KEY = 'HASJFDYWQ98r6y2hesakjfhakjfy87eyr1hakjwfa'
CACHE_BACKEND = 'locmem://'
LOCAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
ADMINS = [
    ('Example Admin', 'admin@example.com'),
]
