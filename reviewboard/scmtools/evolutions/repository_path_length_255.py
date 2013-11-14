from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('Repository', 'path', initial=None, max_length=255),
    ChangeField('Repository', 'mirror_path', initial=None, max_length=255),
    ChangeField('Repository', 'raw_file_url', initial=None, max_length=255)
]
