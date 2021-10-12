from django.conf import settings


SEQUENCE = []

if settings.DATABASES['default']['ENGINE'].endswith('mysql'):
    SEQUENCE.append('fields_changed_longtext')

SEQUENCE.extend([
    'rich_text',
    'changedesc_user',
])
