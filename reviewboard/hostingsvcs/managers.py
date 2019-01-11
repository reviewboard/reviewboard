from __future__ import unicode_literals

from django.db.models import Manager


class HostingServiceAccountManager(Manager):
    """A manager for HostingServiceAccount models."""

    def accessible(self, visible_only=True, local_site=None,
                   filter_local_site=True):
        """Return hosting service accounts that are accessible.

        These will include all visible accounts that are compatible with the
        specified :term:`Local Site`.

        Args:
            visible_only (bool, optional):
                Whether to only include visible accounts in the results.

            local_site (reviewboard.site.models.LocalSite, optional):
                A :term:`Local Site` that the accounts must be associated with.
                If not specified, returned accounts won't be bound to a
                Local Site.

            filter_local_site (bool, optional):
                Whether to factor in the ``local_site`` argument. If ``False``,
                the :term:`Local Site` will be ignored.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        qs = self.all()

        if visible_only:
            qs = qs.filter(visible=True)

        qs = qs.distinct()

        if filter_local_site:
            qs = qs.filter(local_site=local_site)

        return qs

    def can_create(self, user, local_site=None):
        return user.has_perm('hostingsvcs.create_hostingserviceaccount',
                             local_site)
