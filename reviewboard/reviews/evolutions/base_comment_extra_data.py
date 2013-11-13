from __future__ import unicode_literals

from django_evolution.mutations import AddField
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('Comment', 'extra_data', JSONField, null=True),
    AddField('ScreenshotComment', 'extra_data', JSONField, null=True),
]
