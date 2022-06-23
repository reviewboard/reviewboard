from django.db.models import Manager, Q

from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.site.models import LocalSite


class HostingServiceAccountManager(Manager):
    """A manager for HostingServiceAccount models."""

    def accessible(self, visible_only=True, local_site=None,
                   filter_local_site=None):
        """Return hosting service accounts that are accessible.

        These will include all visible accounts that are compatible with the
        specified :term:`Local Site`.

        Version Changed:
            5.0:
            Deprecated ``filter_local_site`` and added support for
            setting ``local_site`` to :py:class:`LocalSite.ALL
            <reviewboard.site.models.LocalSite.ALL>`.

        Args:
            visible_only (bool, optional):
                Whether to only include visible accounts in the results.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A :term:`Local Site` that the accounts must be associated with.
                If not specified, returned accounts won't be bound to a
                Local Site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Version Changed:
                    5.0:
                    Added support for :py:attr:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>`.

            filter_local_site (bool, optional):
                Whether to factor in the ``local_site`` argument. If ``False``,
                the :term:`Local Site` will be ignored.

                Deprecated:
                    5.0:
                    Callers should instead set ``local_site`` to
                    :py:class:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>` instead of
                    setting this to ``True``.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        if filter_local_site is not None:
            RemovedInReviewBoard60Warning.warn(
                'filter_local_site is deprecated. Please pass '
                'local_site=LocalSite.ALL instead. This will be required '
                'in Review Board 6.')

            if filter_local_site:
                assert local_site is not LocalSite.ALL
            else:
                assert local_site in (None, LocalSite.ALL)
                local_site = LocalSite.ALL

        q = LocalSite.objects.build_q(local_site=local_site)

        if visible_only:
            q &= Q(visible=True)

        return self.filter(q)

    def can_create(self, user, local_site=None):
        return user.has_perm('hostingsvcs.create_hostingserviceaccount',
                             local_site)
