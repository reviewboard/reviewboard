"""Models for hosting service accounts."""

from __future__ import annotations

import logging
from typing import ClassVar, TYPE_CHECKING
from urllib.parse import urlparse

from django.db import models
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.certs.cert import Certificate
from reviewboard.certs.manager import cert_manager
from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.managers import HostingServiceAccountManager
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from reviewboard.scmtools.certs import Certificate as LegacyCertificate


logger = logging.getLogger(__name__)


class HostingServiceAccount(models.Model):
    """An account for a hosting service."""

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

    objects: ClassVar[HostingServiceAccountManager] = \
        HostingServiceAccountManager()

    def __str__(self) -> str:
        """Return a string representation of the hosting service account.

        Returns:
            str:
            A string representation of the object.
        """
        if self.hosting_url:
            # Show the hosting URL, so that users can distinguish between
            # the accounts across different self-hosted servers of a given
            # type.
            return f'{self.username} ({self.hosting_url})'
        else:
            return self.username

    @property
    def service(self) -> BaseHostingService:
        """The hosting service associated with this account.

        Type:
            reviewboard.hostingsvcs.base.hosting_service.BaseHostingService

        Raises:
            reviewboard.hostingsvcs.errors.MissingHostingServiceError:
                The hosting service could not be loaded from the registry.
        """
        if not hasattr(self, '_service'):
            service_name = self.service_name

            cls = hosting_service_registry.get_hosting_service(
                self.service_name)

            if cls:
                self._service = cls(self)
            else:
                logger.error('Failed to load hosting service %s for '
                             'repository %s.',
                             service_name, self.pk)

                raise MissingHostingServiceError(service_name)

        return self._service

    @property
    def is_authorized(self) -> bool:
        """Whether the service is authorized.

        Type:
            bool
        """
        service = self.service

        if service:
            return service.is_authorized()
        else:
            return False

    def is_accessible_by(
        self,
        user: User,
    ) -> bool:
        """Return whether or not the user has access to the account.

        The account is accessible by the user if the user has access to the
        local site.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            True if the user has access to the hosting service account.
        """
        return not self.local_site or self.local_site.is_accessible_by(user)

    def is_mutable_by(
        self,
        user: User,
    ) -> bool:
        """Return whether or not the user can modify or delete the account.

        The account is mutable by the user if the user is an administrator
        with proper permissions or the account is part of a LocalSite and
        the user has permissions to modify it.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            True if the user can modify the hosting service account.
        """
        return user.has_perm('hostingsvcs.change_hostingserviceaccount',
                             self.local_site)

    def accept_certificate(
        self,
        certificate: LegacyCertificate,
    ) -> None:
        """Accept the SSL certificate for the linked hosting URL.

        Deprecated:
            8.0:
            This has been replaced with
            :py:meth:`CertificateManager.add_certificate()
            <reviewboard.certs.manager.CertificateManager.add_certificate>`
            and will be removed in Review Board 10.

        Args:
            certificate (reviewboard.scmtools.certs.Certificate):
                The certificate to accept.

        Raises:
            ValueError:
                The certificate data did not include required fields.
        """
        RemovedInReviewBoard10_0Warning.warn(
            'HostingServiceAccount.accept_certificate() is deprecated and '
            'will be removed in Review Board 10. Use '
            'cert_manager.add_certificate() instead.'
        )

        cert_data = certificate.pem_data

        if not cert_data:
            raise ValueError('The certificate does not include a PEM-encoded '
                             'representation.')

        # Also register with the certificate manager so that it can be
        # checked against the main fingerprint storage.
        hosting_url = self.hosting_url
        hostname = certificate.hostname
        fingerprint = certificate.fingerprint
        port = 443

        if hosting_url:
            try:
                parsed = urlparse(hosting_url)

                if parsed.hostname:
                    hostname = parsed.hostname

                if parsed.port:
                    port = parsed.port
                elif parsed.scheme == 'http':
                    logger.error(
                        'Attempted to accept TLS/SSL certificate for HTTP '
                        'URL %s. This may be a programming error or a '
                        'misconfiguration with a server. A certificate '
                        'will not be added.',
                        hosting_url,
                    )

                    return
            except Exception as e:
                logger.exception(
                    'Unexpected error parsing the URL %s when accepting a '
                    'TLS/SSL certificate: %s',
                    hosting_url, e,
                )

                return

        if not hostname:
            logger.error(
                'Could not determine a hostname to use for the TLS/SSL '
                'certificate accepted for %s. A certificate will not be '
                'added.',
                hosting_url or '<unknown>',
            )

            return

        try:
            cert_manager.add_certificate(
                Certificate(
                    hostname=hostname,
                    port=port,
                    cert_data=cert_data.encode('ascii'),
                ),
                local_site=self.local_site,
            )
        except Exception as e:
            logger.error(
                'Failed to add SSL certificate for %s:%s '
                '(fingerprint %r): %s',
                hostname, port, fingerprint, e,
            )

    class Meta:
        """Metadata for the HostingServiceAccount model."""

        db_table = 'hostingsvcs_hostingserviceaccount'
        verbose_name = _('Hosting Service Account')
        verbose_name_plural = _('Hosting Service Accounts')
