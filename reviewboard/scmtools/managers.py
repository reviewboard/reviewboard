from __future__ import unicode_literals

from django.db.models import Manager, Q
from django.db.models.query import QuerySet


_TOOL_CACHE = {}


class ToolQuerySet(QuerySet):
    def get(self, *args, **kwargs):
        pk = kwargs.get('id__exact', None)

        if pk is None:
            return super(ToolQuerySet, self).get(*args, **kwargs)

        if not _TOOL_CACHE:
            # Precompute the cache to reduce lookups.
            for tool in self.model.objects.all():
                _TOOL_CACHE[tool.pk] = tool

        if pk not in _TOOL_CACHE:
            # We'll try to look up the Tool anyway, since it may have been
            # added since. This will also ensure the proper exception is
            # raised if not found.
            _TOOL_CACHE[pk] = super(ToolQuerySet, self).get(*args, **kwargs)

        return _TOOL_CACHE[pk]


class ToolManager(Manager):
    """Manages Tool models.

    Any get() operations performed (directly or indirectly through a
    ForeignKey) will go through a cache to attempt to minimize Tool
    lookups.

    The Tool cache is never cleared, but as Tool objects should never
    be modified by hand (they're registered when doing an rb-site upgrade,
    and then the server process must be reloaded), this shouldn't be a
    problem.
    """
    use_for_related_fields = True

    def get_query_set(self):
        return ToolQuerySet(self.model, using=self.db)


class RepositoryManager(Manager):
    """A manager for Repository models."""
    def accessible(self, user, visible_only=True, local_site=None):
        """Returns repositories that are accessible by the given user."""
        if user.is_superuser:
            if visible_only:
                qs = self.filter(visible=True).distinct()
            else:
                qs = self.all()
        else:
            q = Q(public=True)

            if visible_only:
                q = q & Q(visible=True)

            if user.is_authenticated():
                q = q | (Q(users__pk=user.pk) |
                         Q(review_groups__users=user.pk))

            qs = self.filter(q).distinct()

        return qs.filter(local_site=local_site)

    def can_create(self, user, local_site=None):
        return user.has_perm('scmtools.create_repository', local_site)
