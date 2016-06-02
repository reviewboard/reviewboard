from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.hostingsvcs.managers import HostingServiceAccountManager
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.site.models import LocalSite


@python_2_unicode_compatible
class HostingServiceAccount(models.Model):
    service_name = models.CharField(max_length=128)
    hosting_url = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=128)
    data = JSONField()
    visible = models.BooleanField(default=True)
    local_site = models.ForeignKey(LocalSite,
                                   related_name='hosting_service_accounts',
                                   verbose_name=_('Local site'),
                                   blank=True,
                                   null=True)

    objects = HostingServiceAccountManager()

    def __str__(self):
        if self.hosting_url:
            # Show the hosting URL, so that users can distinguish between
            # the accounts across different self-hosted servers of a given
            # type.
            return '%s (%s)' % (self.username, self.hosting_url)
        else:
            return self.username

    @property
    def service(self):
        if not hasattr(self, '_service'):
            cls = get_hosting_service(self.service_name)

            if cls:
                self._service = cls(self)
            else:
                self._service = None

        return self._service

    @property
    def is_authorized(self):
        service = self.service

        if service:
            return service.is_authorized()
        else:
            return False

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to the account.

        The account is accessible by the user if the user has access to the
        local site.
        """
        return not self.local_site or self.local_site.is_accessible_by(user)

    def is_mutable_by(self, user):
        """Returns whether or not the user can modify or delete the account.

        The acount is mutable by the user if the user is an administrator
        with proper permissions or the account is part of a LocalSite and
        the user has permissions to modify it.
        """
        return user.has_perm('hostingsvcs.change_hostingserviceaccount',
                             self.local_site)
