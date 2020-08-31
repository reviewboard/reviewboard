from __future__ import unicode_literals

from django.db.models import Manager, Q
from django.db.models.query import QuerySet


_TOOL_CACHE = {}


class ToolQuerySet(QuerySet):
    """QuerySet for accessing database-registered SCMTools.

    This provides some basic caching capabilities to ensure that common
    lookups of tools don't hit the database any more than necessary.
    """

    def get(self, *args, **kwargs):
        """Return a Tool registration from the database.

        If querying directly by ID, this will return a cached entry, if
        available.

        If the cache is empty, all database registrations will be queried
        immediately and cached.

        And other queries will proceed as normal, uncached.

        Args:
            *args (tuple):
                Positional query arguments.

            **kwargs (dict):
                Keyword query arguments.

        Returns:
            reviewboard.scmtools.models.Tool:
            The queried Tool, if found.

        Raises:
            reviewboard.scmtools.models.Tool.DoesNotExist:
                The queried Tool could not be found.

            reviewboard.scmtools.models.Tool.MultipleObjectsReturned:
                Multiple Tools matching the query were found.
        """
        pk = None

        # This is all pretty awful. We're not meant to reach into these
        # objects. However, we also don't really have another way of finding
        # out what ID was queried.
        #
        # This will be less of a problem when we move away from database-backed
        # Tool registration.
        if len(args) > 0 and isinstance(args[0], Q):
            try:
                query_field, query_value = args[0].children[0]
            except Exception:
                query_field = None
                query_value = None

            if query_field in ('id', 'id__exact', 'pk', 'pk__exact'):
                pk = query_value
        else:
            pk = (kwargs.get('pk') or
                  kwargs.get('pk__exact') or
                  kwargs.get('id') or
                  kwargs.get('id__exact'))

        if pk is None:
            # Something else was queried. Request it from the database as
            # normal.
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

    def get_queryset(self):
        """Return a QuerySet for Tool models.

        Returns:
            ToolQuerySet:
            The new QuerySet instance.
        """
        return ToolQuerySet(self.model, using=self.db)

    def clear_tool_cache(self):
        """Clear the internal cache of Tools.

        This is intended for unit tests, and won't be called during production.
        """
        _TOOL_CACHE.clear()


class RepositoryManager(Manager):
    """A manager for Repository models."""

    def accessible(self, user, visible_only=True, local_site=None,
                   show_all_local_sites=False):
        """Return a queryset for repositories accessible by the given user.

        For superusers, all public and private repositories will be returned.

        For regular users, only repositories that are public or that the user
        is on the access lists for (directly or through a review group) will
        be returned.

        For anonymous users, only public repositories will be returned.

        The returned list is further filtered down based on the
        ``visible_only``, ``local_site``, and ``show_all_local_sites``
        parameters.

        Args:
            user (django.contrib.auth.models.User):
                The user that must have access to any returned repositories.

            visible_only (bool, optional):
                Whether only visible repositories should be returned.

            local_site (reviewboard.site.models.LocalSite, optional):
                A specific :term:`Local Site` that the repositories must be
                associated with. By default, this will only return
                repositories not part of a site.

            show_all_local_sites (bool, optional):
                Whether repositories from all :term:`Local Sites` should be
                returned. This cannot be ``True`` if a ``local_site`` argument
                was provided.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        if user.is_superuser:
            qs = self.all()

            if visible_only:
                qs = qs.filter(visible=True)
        else:
            q = Q(public=True)

            if visible_only:
                # We allow accessible() to return hidden repositories if the
                # user is a member, so we must perform this check here.
                q &= Q(visible=True)

            if user.is_authenticated():
                q |= (Q(users__pk=user.pk) |
                      Q(review_groups__users=user.pk))

            qs = self.filter(q)

        if show_all_local_sites:
            assert local_site is None
        else:
            qs = qs.filter(local_site=local_site)

        return qs.distinct()

    def accessible_ids(self, *args, **kwargs):
        """Return IDs of repositories that are accessible by the given user.

        This wraps :py:meth:`accessible` and takes the same arguments.

        Args:
            *args (tuple):
                Positional arguments to pass to :py:meth:`accessible`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`accessible`.

        Returns:
            list of int:
            The list of IDs.
        """
        return self.accessible(*args, **kwargs).values_list('pk', flat=True)

    def can_create(self, user, local_site=None):
        return user.has_perm('scmtools.add_repository', local_site)

    def encrypt_plain_text_passwords(self):
        """Encrypts any stored plain-text passwords."""
        qs = self.exclude(
            Q(encrypted_password=None) |
            Q(encrypted_password='') |
            Q(encrypted_password__startswith=
              self.model.ENCRYPTED_PASSWORD_PREFIX))
        qs = qs.only('encrypted_password')

        for repository in qs:
            # This will trigger a migration of the password.
            repository.password
