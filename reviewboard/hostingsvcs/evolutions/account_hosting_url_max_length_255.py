"""Reduce max_length of HostingServiceAccount.hosting_url to 255 chars.

This was reduced from 256 characters.

Version Added:
    1.7.8
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('HostingServiceAccount', 'hosting_url', initial=None,
                max_length=255)
]
