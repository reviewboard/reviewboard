from __future__ import unicode_literals

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('HostingServiceAccount', 'hosting_url', initial=None,
                max_length=255)
]
