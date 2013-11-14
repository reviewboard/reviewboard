from __future__ import unicode_literals

from django.dispatch import Signal


checking_file_exists = Signal(providing_args=['path', 'revision', 'request'])
checked_file_exists = Signal(providing_args=['path', 'revision', 'request'])

fetching_file = Signal(providing_args=['path', 'revision', 'request'])
fetched_file = Signal(providing_args=['path', 'revision', 'request'])
