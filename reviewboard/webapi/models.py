from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.site.models import LocalSite
from reviewboard.webapi.managers import WebAPITokenManager


@python_2_unicode_compatible
class WebAPIToken(models.Model):
    """An access token used for authenticating with the API.

    Each token can be used to authenticate the token's owner with the API,
    without requiring a username or password to be provided. Tokens can
    be revoked, and new tokens added.

    Tokens can store policy information, which will later be used for
    restricting access to the API.
    """
    user = models.ForeignKey(User, related_name='webapi_tokens')
    local_site = models.ForeignKey(LocalSite, related_name='webapi_tokens',
                                   blank=True, null=True)

    token = models.CharField(max_length=40, unique=True)
    time_added = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)

    note = models.TextField(blank=True)
    policy = JSONField(default={})

    extra_data = JSONField(default={})

    objects = WebAPITokenManager()

    def is_accessible_by(self, user):
        return user.is_superuser or self.user == user

    def is_mutable_by(self, user):
        return user.is_superuser or self.user == user

    def is_deletable_by(self, user):
        return user.is_superuser or self.user == user

    def __str__(self):
        return 'Web API token for %s' % self.user

    class Meta:
        verbose_name = _('Web API token')
        verbose_name_plural = _('Web API tokens')
