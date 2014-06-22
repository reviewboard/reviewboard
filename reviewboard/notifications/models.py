from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from multiselectfield import MultiSelectField

from reviewboard.site.models import LocalSite


class WebHookTarget(models.Model):
    """A target for a webhook.

    A webhook target is a URL which will receive a POST request when the
    corresponding event occurs.
    """
    HANDLER_CHOICES = (
        ('*', _('All')),
        ('review_request_closed', _('Review Request Closed')),
        ('review_request_published', _('Review Request Published')),
        ('review_request_reopened', _('Review Request Reopened')),
        ('review_published', _('Review Published')),
        ('reply_published', _('Reply Published')),
    )

    handlers = MultiSelectField(choices=HANDLER_CHOICES)
    url = models.URLField('URL')
    enabled = models.BooleanField()
    local_site = models.ForeignKey(LocalSite, blank=True, null=True)
    secret = models.CharField(max_length=128, blank=True)
