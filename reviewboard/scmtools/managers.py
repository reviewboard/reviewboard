from django.db.models import Manager


class RepositoryManager(Manager):
    """A manager for Repository models."""
    def can_create(self, user):
        return user.has_perm('scmtools.create_repository')
