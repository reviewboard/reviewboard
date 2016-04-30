from __future__ import unicode_literals

from django.db.models import Manager, Q


class WebHookTargetManager(Manager):
    """Manages WebHookTarget models.

    This provides a utility function for querying WebHookTargets for a
    given event.
    """

    def for_event(self, event, local_site_id=None, repository_id=None):
        """Returns a list of matching webhook targets for the given event."""
        if event == self.model.ALL_EVENTS:
            raise ValueError('"%s" is not a valid event choice' % event)

        q = Q(enabled=True) & Q(local_site=local_site_id)

        if repository_id is None:
            q &= (Q(apply_to=self.model.APPLY_TO_ALL) |
                  Q(apply_to=self.model.APPLY_TO_NO_REPOS))
        else:
            q &= (Q(apply_to=self.model.APPLY_TO_ALL) |
                  (Q(apply_to=self.model.APPLY_TO_SELECTED_REPOS) &
                   Q(repositories=repository_id)))

        return [
            target
            for target in self.filter(q)
            if event in target.events or self.model.ALL_EVENTS in target.events
        ]

    def for_local_site(self, local_site=None):
        """Return a list of webhooks on the local site.

        Args:
            local_site (reviewboard.site.models.LocalSite):
                An optional local site.

        Returns:
            django.db.models.query.QuerySet:
            A queryset matching all accessible webhooks.
        """
        return self.filter(local_site=local_site)

    def can_create(self, user, local_site=None):
        """Return whether the user can create webhooks on the local site.

        Args:
            user (django.contrib.auth.models.User):
                The user to check for permissions.

            local_site (reviewboard.site.models.LocalSite):
                The current local site, if it exists.

        Returns:
            bool:
            Whether or not the use can create a webhook on the local site.
        """
        return (user.is_superuser or
                (user.is_authenticated() and
                 local_site and
                 local_site.is_mutable_by(user)))
