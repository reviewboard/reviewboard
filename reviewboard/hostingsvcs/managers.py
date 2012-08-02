from django.db.models import Manager


class HostingServiceAccountManager(Manager):
    """A manager for HostingServiceAccount models."""
    def accessible(self, visible_only=True, local_site=None):
        """Returns hosting service accounts that are accessible."""
        qs = self.all()

        if visible_only:
            qs = qs.filter(visible=True)

        qs = qs.distinct()

        return qs.filter(local_site=local_site)

    def can_create(self, user, local_site=None):
        return (user.has_perm('hostingsvcs.create_hostingserviceaccount') or
                (local_site and local_site.is_mutable_by(user)))
