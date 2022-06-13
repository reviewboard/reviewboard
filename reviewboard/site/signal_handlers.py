"""Signal handlers."""

from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed, post_delete, post_save

from reviewboard.site.models import LocalSite
from reviewboard.site.signals import local_site_user_added


def _emit_local_site_user_signals(instance, action, pk_set, **kwargs):
    """Handle the m2m_changed event for LocalSite and User.

    This function handles both the case where users are added to local sites
    and local sites are added to the set of a user's local sites. In both of
    these cases, the :py:data:`reviewboard.site.signals.local_site_user_added`
    signal is dispatched.

    Version Added:
        5.0:
        This logic used to live in :py:mod:`reviewboard.site.models`.

    Args:
        instance (django.contrib.auth.models.User or
                  reviewboard.site.models.LocalSite):
            The Local Site or User that caused the signal to be emitted,
            depending on the side of the relation that changed.

        action (unicode):
            The action that was performed. This handler only responds to
            ``post_add``.

        pk_set (list of int):
            The list of primary keys that were added.

        **kwargs (dict, unused):
            Additional keyword arguments from the signal.
    """
    if action != 'post_add':
        return

    if isinstance(instance, User):
        users = [instance]
        local_sites = LocalSite.objects.filter(id__in=pk_set)
    else:
        users = User.objects.filter(id__in=pk_set)
        local_sites = [instance]

    for user in users:
        for local_site in local_sites:
            local_site_user_added.send(sender=LocalSite,
                                       user=user,
                                       local_site=local_site)


def _invalidate_caches(**kwargs):
    """Invalidate all LocalSite-related caches.

    This will invalidate on any post-save/delete events for any
    :py:class:`~reviewboard.site.models.LocalSite` instances. Cache will be
    invalidated, causing stats to be re-generated the next time they're
    needed.

    Version Added:
        5.0

    Args:
        **kwargs (dict, unused):
            Keyword arguments passed to the signal.
    """
    LocalSite.objects.invalidate_stats_cache()


def _on_save_invalidate_local_site_acl_cache(instance, created, update_fields,
                                             **kwargs):
    """Invalidate a per-LocalSite ACL cache.

    This will invalidate when an existing Local Site's public state has
    changed. Cache will be invalidated, causing stats to be re-generated the
    next time they're needed.

    Version Added:
        5.0

    Args:
        instance (reviewboard.site.models.LocalSite):
            The Local Site instance.

        created (bool):
            Whether the Local Site was created.

        update_fields (list of str):
            The list of fields that were specifically updated, if any.

        **kwargs (dict, unused):
            Additional keyword arguments passed to the signal.
    """
    if not created and (not update_fields or 'public' in update_fields):
        LocalSite.objects.invalidate_local_site_acl_stats_cache(instance)


def _on_delete_invalidate_local_site_acl_cache(instance, **kwargs):
    """Invalidate a per-LocalSite ACL cache.

    This will invalidate when a Local Site is deleted. Cache will be
    invalidated, causing stats to be re-generated the next time they're
    needed.

    Version Added:
        5.0

    Args:
        instance (reviewboard.site.models.LocalSite):
            The Local Site instance.

        **kwargs (dict, unused):
            Additional keyword arguments passed to the signal.
    """
    LocalSite.objects.invalidate_local_site_acl_stats_cache(instance)


def _on_m2m_invalidate_local_site_acl_cache(instance, reverse, action,
                                            pk_set, **kwargs):
    """Invalidate a per-LocalSite ACL cache.

    This will invalidate when the user or administrator membership of a site
    has changed. Cache will be invalidated, causing stats to be re-generated
    the next time they're needed.

    Version Added:
        5.0

    Args:
        instance (reviewboard.site.models.LocalSite or
                  django.contrib.auth.models.User):
            The Local Site instance, or a user if altering the relation from
            the other end.

        reverse (bool):
            Whether a change was made on the reverse end of the relation.

        action (str):
            The M2M action being performed.

        pk_set (list of int):
            The list of objects set on the other end of a M2M relation.

            These will be Local Site IDs if ``reverse`` is ``True``.

        **kwargs (dict, unused):
            Additional keyword arguments passed to the signal.
    """
    if reverse:
        if action in ('post_add', 'post_remove'):
            for pk in pk_set:
                LocalSite.objects.invalidate_local_site_acl_stats_cache(pk)
    else:
        assert isinstance(instance, LocalSite)

        LocalSite.objects.invalidate_local_site_acl_stats_cache(instance)


def connect_signal_handlers():
    """Connect LocalSite-related signal handlers.

    Version Added:
        5.0
    """
    m2m_changed.connect(_emit_local_site_user_signals,
                        sender=LocalSite.users.through)

    # Invalidate stat caches any time Local Sites have been added or deleted.
    post_save.connect(_invalidate_caches, sender=LocalSite)
    post_delete.connect(_invalidate_caches, sender=LocalSite)

    # Invalidate ACL stat caches any time Local Sites have been deleted or
    # or saved, or membership changed.
    post_save.connect(_on_save_invalidate_local_site_acl_cache,
                      sender=LocalSite)
    post_delete.connect(_on_delete_invalidate_local_site_acl_cache,
                        sender=LocalSite)
    m2m_changed.connect(_on_m2m_invalidate_local_site_acl_cache,
                        sender=LocalSite.admins.through)
    m2m_changed.connect(_on_m2m_invalidate_local_site_acl_cache,
                        sender=LocalSite.users.through)
