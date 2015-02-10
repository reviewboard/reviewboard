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
