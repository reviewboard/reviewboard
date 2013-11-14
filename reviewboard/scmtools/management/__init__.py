from __future__ import unicode_literals

from django.conf import settings
from django.core.management import call_command
from django.db.models import signals

from reviewboard.scmtools.models import Tool


def register_scmtools(app, created_models, **kwargs):
    if Tool in created_models and not getattr(settings, "RUNNING_TEST", False):
        call_command('registerscmtools')


signals.post_syncdb.connect(register_scmtools)
