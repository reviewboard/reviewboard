"""Managers for the hostingsvcs app."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.db.models import Manager, Q

from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet

    from reviewboard.hostingsvcs.models import HostingServiceAccount
    from reviewboard.site.models import AnyOrAllLocalSites


class HostingServiceAccountManager(Manager['HostingServiceAccount']):
    """A manager for HostingServiceAccount models."""

    def accessible(
        self,
        visible_only: bool = True,
        local_site: Optional[AnyOrAllLocalSites] = None,
    ) -> QuerySet[HostingServiceAccount]:
        """Return hosting service accounts that are accessible.

        These will include all visible accounts that are compatible with the
        specified :term:`Local Site`.

        Version Changed:
            6.0:
            Removed the ``filter_local_site`` argument.

        Version Changed:
            5.0:
            Deprecated ``filter_local_site`` and added support for
            setting ``local_site`` to :py:class:`LocalSite.ALL
            <reviewboard.site.models.LocalSite.ALL>`.

        Args:
            visible_only (bool, optional):
                Whether to only include visible accounts in the results.

            local_site (reviewboard.site.models.AnyOrAllLocalSites, optional):
                A :term:`Local Site` that the accounts must be associated with.
                If not specified, returned accounts won't be bound to a
                Local Site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Version Changed:
                    5.0:
                    Added support for :py:attr:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>`.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        q = LocalSite.objects.build_q(local_site=local_site)

        if visible_only:
            q &= Q(visible=True)

        return self.filter(q)

    def can_create(
        self,
        user: User,
        local_site: Optional[AnyOrAllLocalSites] = None,
    ) -> bool:
        """Return whether the user can create a hosting service account.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

            local_site (reviewboard.site.models.AnyOrAllLocalSites, optional):
                A :term:`Local Site` to create hosting service accounts on.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

        Returns:
            bool:
            True if the user can create hosting service accounts.
        """
        return user.has_perm('hostingsvcs.create_hostingserviceaccount',
                             local_site)
