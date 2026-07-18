"""Models for hosting service accounts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django.db import models
from django.utils.translation import gettext_lazy as _
from djblets.conditions import ConditionSet
from djblets.db.fields import JSONField

from reviewboard.certs.cert import Certificate
from reviewboard.certs.manager import cert_manager
from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.hostingsvcs.base import (
    BaseBugTracker,
    hosting_service_registry,
)
from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.managers import (
    ConfiguredBugTrackerManager,
    HostingServiceAccountManager,
)
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import ClassVar, Final

    from django.contrib.auth.models import User
    from django.http import HttpRequest
    from typelets.django.auth import AnyUser
    from typelets.django.strings import StrPromise

    from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
    from reviewboard.scmtools.certs import Certificate as LegacyCertificate


logger = logging.getLogger(__name__)


#: The reserved service name identifying the sentinel bug tracker.
#:
#: The sentinel tracker owns unattributed bug links. It is never listed,
#: never enabled, and never matches a real hosting service ID.
#:
#: Version Added:
#:     9.0
SENTINEL_BUG_TRACKER_SERVICE_NAME: Final[str] = '<sentinel>'


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
        user: AnyUser,
    ) -> bool:
        """Return whether or not the user has access to the account.

        The account is accessible by the user if the user has access to the
        local site.

        Args:
            user (django.contrib.auth.models.User or
                  django.contrib.auth.models.AnonymousUser):
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


class ConfiguredBugTracker(models.Model):
    """A configured bug tracker instance.

    Bug trackers are matched to review requests through
    :py:meth:`ConfiguredBugTrackerManager.for_review_request()
    <reviewboard.hostingsvcs.managers.ConfiguredBugTrackerManager.
    for_review_request>`.

    Version Added:
        9.0
    """

    APPLY_TO_ALL = 'A'
    APPLY_TO_NO_REPOS = 'N'
    APPLY_TO_SELECTED_REPOS = 'S'

    APPLY_TO_CHOICES: Mapping[str, StrPromise] = {
        APPLY_TO_ALL: _('All review requests'),
        APPLY_TO_SELECTED_REPOS: _(
            'Only review requests on selected repositories'
        ),
        APPLY_TO_NO_REPOS: _(
            'Only review requests not associated with a repository (file '
            'attachments only)'
        ),
    }

    #: Show bugs as a list of links in the review request's information.
    DISPLAY_MODE_COMPACT = 'compact'

    #: Show bugs as a table of IDs, summaries, and statuses.
    DISPLAY_MODE_DETAILED = 'detailed'

    DISPLAY_MODE_CHOICES: Mapping[str, StrPromise] = {
        DISPLAY_MODE_COMPACT: _(
            'Compact: a list of bug links in the Information section'
        ),
        DISPLAY_MODE_DETAILED: _(
            'Detailed: a table of bug IDs, summaries, and statuses shown '
            'below the main fields'
        ),
     }

    #: The settings key storing the display mode.
    DISPLAY_MODE_KEY = 'display_mode'

    added_timestamp = models.DateTimeField(auto_now_add=True)

    apply_to = models.CharField(
        _('apply to'),
        max_length=1,
        blank=False,
        default=APPLY_TO_ALL,
        choices=APPLY_TO_CHOICES)

    enabled = models.BooleanField(default=True)

    extra_data = JSONField()

    hosting_account = models.ForeignKey(
        HostingServiceAccount,
        on_delete=models.PROTECT,
        related_name='bug_trackers',
        verbose_name=_('Hosting service account'),
        blank=True,
        null=True,
        help_text=_(
            'The account used to talk to the bug tracker, for services that '
            'require one.'
        ))

    last_updated_timestamp = models.DateTimeField(auto_now=True)

    local_site = models.ForeignKey(
        LocalSite,
        on_delete=models.CASCADE,
        related_name='bug_trackers',
        verbose_name=_('Local site'),
        blank=True,
        null=True,
        help_text=_('The LocalSite to associate with this bug tracker.'))

    name = models.CharField(
        max_length=128,
        help_text=_(
            'The display name for this bug tracker. This is used as the field '
            'label on review requests.'
        ))

    repositories = models.ManyToManyField(
        'scmtools.Repository',
        blank=True,
        related_name='bug_trackers',
        help_text=_(
            'If set, this bug tracker will be limited to these repositories.'
        ))

    settings = JSONField(
        help_text=_('Service-specific settings for this bug tracker.'))

    service_name = models.CharField(
        max_length=128,
        help_text=_('The ID of the hosting service providing this bug '
                    'tracker.'))

    user_conditions = JSONField(
        help_text=_(
            'Serialized conditions determining which users may interact with '
            'this bug tracker.'
        ))

    objects: ClassVar[ConfiguredBugTrackerManager] = \
        ConfiguredBugTrackerManager()

    def __str__(self) -> str:
        """Return a string representation of the bug tracker.

        Returns:
            str:
            A string representation of the object.
        """
        return self.name

    @property
    def service(self) -> BaseBugTracker:
        """The hosting service providing this bug tracker.

        Type:
            reviewboard.hostingsvcs.base.hosting_service.BaseBugTracker

        Raises:
            reviewboard.hostingsvcs.errors.MissingHostingServiceError:
                The hosting service could not be loaded from the registry.
        """
        if not hasattr(self, '_service'):
            service_name = self.service_name

            cls = hosting_service_registry.get_hosting_service(service_name)

            if not cls:
                logger.error(
                    'Failed to load hosting service %s for bug tracker %s.',
                    service_name, self.pk)

                raise MissingHostingServiceError(service_name)

            if not issubclass(cls, BaseBugTracker):
                logger.error(
                    'Bug tracker %s is configured with hosting service %s '
                    'that does not inherit from BaseBugTracker.',
                    self.pk, service_name)

                raise MissingHostingServiceError(service_name)

            account = self.hosting_account

            if account is None:
                # Some bug tracker services do not require an account.
                # Give the service an unsaved placeholder so it can
                # still be instantiated.
                account = HostingServiceAccount(
                    service_name=service_name,
                    local_site=self.local_site)

            self._service = cls(account)

        return self._service

    @property
    def display_mode(self) -> str:
        """How the tracker's bugs are shown on review requests.

        This is one of :py:attr:`DISPLAY_MODE_COMPACT` or
        :py:attr:`DISPLAY_MODE_DETAILED`. Unknown values fall back to
        the compact mode.

        Type:
            str

        Version Added:
            9.0
        """
        display_mode = (self.settings or {}).get(self.DISPLAY_MODE_KEY)

        if display_mode == self.DISPLAY_MODE_DETAILED:
            return self.DISPLAY_MODE_DETAILED

        return self.DISPLAY_MODE_COMPACT

    def is_accessible_by(
        self,
        user: AnyUser,
    ) -> bool:
        """Return whether the user has access to the bug tracker's Local Site.

        The bug tracker is accessible by the user if the user has access
        to the :term:`Local Site`. This does not check the user conditions. Use
        :py:meth:`is_usable_by` for that.

        Args:
            user (django.contrib.auth.models.User or
                  django.contrib.auth.models.AnonymousUser):
                The user to check.

        Returns:
            bool:
            True if the user has access to the bug tracker's
            :term:`Local Site`.
        """
        return not self.local_site or self.local_site.is_accessible_by(user)

    def is_usable_by(
        self,
        user: AnyUser,
        *,
        request: (HttpRequest | None) = None,
    ) -> bool:
        """Return whether the user may interact with this bug tracker.

        This is the security boundary for bug tracker content. Every
        endpoint that exposes bug URLs, metadata, or search must call
        this. Users failing this check see bare bug IDs only.

        An empty condition set means the tracker is usable by everyone.
        If a non-empty condition set cannot be deserialized, this fails
        closed and returns ``False``.

        Results are cached on ``request`` when one is provided.

        Args:
            user (django.contrib.auth.models.User or
                  django.contrib.auth.models.AnonymousUser):
                The acting user.

            request (django.http.HttpRequest, optional):
                The HTTP request, used for caching.

        Returns:
            bool:
            True if the user may interact with this bug tracker.
        """
        cache_key = (self.pk, user.pk)
        cache: (dict[tuple[int, int], bool] | None) = None

        if request is not None:
            try:
                cache = request._bug_tracker_usable_cache  # type:ignore
            except AttributeError:
                cache = {}
                request._bug_tracker_usable_cache = cache  # type:ignore

            assert cache is not None

            try:
                return cache[cache_key]
            except KeyError:
                pass

        usable = self._check_user_conditions(user)

        if cache is not None:
            cache[cache_key] = usable

        return usable

    def is_mutable_by(
        self,
        user: User,
    ) -> bool:
        """Return whether the user can modify or delete the bug tracker.

        The bug tracker is mutable by the user if the user is an
        administrator with proper permissions or the bug tracker is part
        of a LocalSite and the user has permissions to modify it.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            True if the user can modify the bug tracker.
        """
        return user.has_perm('hostingsvcs.change_configuredbugtracker',
                             self.local_site)

    def _check_user_conditions(
        self,
        user: AnyUser,
    ) -> bool:
        """Return whether the user matches the stored user conditions.

        Args:
            user (django.contrib.auth.models.User or
                  django.contrib.auth.models.AnonymousUser):
                The acting user.

        Returns:
            bool:
            True if the conditions are empty or match the user. False if
            they do not match, or if a non-empty condition set could not
            be deserialized (failing closed).
        """
        from reviewboard.accounts.conditions import user_condition_choices

        conditions_data = self.user_conditions

        if not conditions_data or not conditions_data.get('conditions'):
            return True

        try:
            condition_set = ConditionSet.deserialize(
                user_condition_choices,
                conditions_data,
                choice_kwargs={
                    'local_site': self.local_site,
                    'matching': True,
                })
        except Exception:
            # This is a security boundary. A broken condition set must
            # deny access, not grant it.
            logger.exception('Unable to load bad user condition set data '
                             'for bug tracker ID=%s',
                             self.pk)
            logger.debug('Bad conditions data = %r', conditions_data)

            return False

        try:
            return condition_set.matches(user=user)
        except Exception as e:
            logger.exception('Unexpected failure when matching user '
                             'conditions for bug tracker ID=%s: %s',
                             self.pk, e)

            return False

    class Meta:
        """Metadata for the ConfiguredBugTracker model."""

        db_table = 'hostingsvcs_configuredbugtracker'
        verbose_name = _('Bug Tracker')
        verbose_name_plural = _('Bug Trackers')
