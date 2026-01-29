"""Add HostingServiceAccount.hosting_url.

Version Added:
    1.7.8
"""

from __future__ import annotations

from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('HostingServiceAccount', 'hosting_url', models.CharField,
             max_length=256, null=True)
]
