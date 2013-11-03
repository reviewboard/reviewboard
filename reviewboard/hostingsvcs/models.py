from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.util.fields import JSONField

from reviewboard.hostingsvcs.managers import HostingServiceAccountManager
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.site.models import LocalSite


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

    def __unicode__(self):
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
        the user is in the admin list.
        """
        return (user.has_perm('hostingsvcs.change_hostingserviceaccount') or
                (self.local_site and self.local_site.is_mutable_by(user)))
