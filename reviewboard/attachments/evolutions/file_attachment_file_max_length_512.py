from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'file', initial=None, max_length=512)
]
