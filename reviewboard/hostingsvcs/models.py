from django.db import models
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.managers import HostingServiceAccountManager
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.site.models import LocalSite


class HostingServiceAccount(models.Model):

    service_name = models.CharField(
        max_length=128,
        help_text=_('The ID of the hosting service that is associated '
                    'with this account.'))
    hosting_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_('The hosting URL.'))
    username = models.CharField(
        max_length=128,
        help_text=_('The username of the account on the hosting service.'))
    data = JSONField(
        help_text=_('Account data specific to the hosting service. This '
                    'should generally not be changed.'))
    visible = models.BooleanField(
        default=True,
        help_text=_('Whether this account shows up as an option when '
                    'configuring a repository.'))
    local_site = models.ForeignKey(
        LocalSite,
        on_delete=models.CASCADE,
        related_name='hosting_service_accounts',
        verbose_name=_('Local site'),
        blank=True,
        null=True,
        help_text=_('The LocalSite to associate with this account.'))

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
        """The hosting service associated with this account.

        Type:
            reviewboard.hostingsvcs.service.HostingService

        Raises:
            reviewboard.hostingsvcs.errors.MissingHostingServiceError:
                The hosting service could not be loaded from the registry.
        """
        if not hasattr(self, '_service'):
            cls = get_hosting_service(self.service_name)

            if cls:
                self._service = cls(self)
            else:
                raise MissingHostingServiceError(self.service_name)

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

        The account is mutable by the user if the user is an administrator
        with proper permissions or the account is part of a LocalSite and
        the user has permissions to modify it.
        """
        return user.has_perm('hostingsvcs.change_hostingserviceaccount',
                             self.local_site)

    def accept_certificate(self, certificate):
        """Accept the SSL certificate for the linked hosting URL.

        Args:
            certificate (reviewboard.scmtools.certs.Certificate):
                The certificate to accept.

        Raises:
            ValueError:
                The certificate data did not include required fields.
        """
        if not certificate.pem_data:
            raise ValueError('The certificate does not include a PEM-encoded '
                             'representation.')

        self.data['ssl_cert'] = certificate.pem_data

    class Meta:
        db_table = 'hostingsvcs_hostingserviceaccount'
        verbose_name = _('Hosting Service Account')
        verbose_name_plural = _('Hosting Service Accounts')
