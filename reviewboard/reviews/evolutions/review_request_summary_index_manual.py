from __future__ import unicode_literals

from django.conf import settings
from django_evolution.mutations import ChangeField, SQLMutation


if settings.DATABASES['default']['ENGINE'].endswith('mysql'):
    field_index_suffix = '(255)'
else:
    field_index_suffix = ''

index_sql = (
    'CREATE INDEX reviews_reviewrequest_summary ON reviews_reviewrequest'
    ' (summary%s);'
    % field_index_suffix
)


MUTATIONS = [
    ChangeField('ReviewRequest', 'summary', initial=None, db_index=False),
    SQLMutation('reviewrequest_summary', [index_sql]),
]
