"""Manually add an index for ReviewRequest.summary.

MySQL has a quirk (many say a bug) where the max index length is based on the
actual number of allowed bytes, rather than characters, in a VARCHAR. On
InnoDB, this max length is 767 bytes. Each Unicode character in MySQL takes 3
bytes, though. If you're running InnoDB with utf-8 and create an index on a
column with a max length over 255 characters (or 765 bytes, you'll either get
an index safely capped to 255 (if running MySQL < 5.6) or an error (if running
MySQL 5.6+).

Note that this is not a problem for Postgres or SQLite. It's also, in this
case, not a problem for MySQL with MyISAM, since the max length there is 1000
bytes.

Our options for the summary field were to either truncate from 300 characters
to 255 (destroying bits of history), to remove the index entirely, or to cap
the index ourselves. The first two options are terrible, and the third is not
directly supported by Django.

Turns out what we can do is create per-engine SQL initial data files that will
create the appropriate indexes. This will only work for new installations,
though, but covers that case.

This evolution then, depending on the database type, invokes custom SQL for
creating the index. On MySQL, that custom SQL will contain a key length cap,
and for everything else, there will be no cap (since they don't support such a
concept).

Version Added:
    2.0.11
"""

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
