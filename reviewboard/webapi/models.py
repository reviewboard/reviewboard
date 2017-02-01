from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.webapi.models import BaseWebAPIToken

from reviewboard.site.models import LocalSite


class WebAPIToken(BaseWebAPIToken):
    """An access token used for authenticating with the API.

    Each token can be used to authenticate the token's owner with the API,
    without requiring a username or password to be provided. Tokens can
    be revoked, and new tokens added.

    Tokens can store policy information, which will later be used for
    restricting access to the API.
    """

    local_site = models.ForeignKey(LocalSite, related_name='webapi_tokens',
                                   blank=True, null=True)

    @classmethod
    def get_root_resource(self):
        from reviewboard.webapi.resources import resources

        return resources.root

    class Meta:
        db_table = 'webapi_webapitoken'
        verbose_name = _('Web API Token')
        verbose_name_plural = _('Web API Tokens')
