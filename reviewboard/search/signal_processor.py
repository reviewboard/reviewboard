"""The signal processor for Review Board search."""

from __future__ import unicode_literals

import threading
from functools import partial

from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.utils import six
from haystack.signals import BaseSignalProcessor

from reviewboard.accounts.models import Profile
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.reviews.signals import review_request_published
from reviewboard.search import search_backend_registry


class SignalProcessor(BaseSignalProcessor):
    """"Listens for signals and updates the search index.

    This will listen for any signals that would affect the search index, and
    invokes a suitable Haystack callback to immediately update the data stored
    in the index.

    This only updates the search index if:

    1) Search is enabled.
    2) The current search engine backend supports on-the-fly indexing.
    """

    save_signals = [
        (ReviewRequest, review_request_published, 'review_request'),
        (User, post_save, 'instance'),
        (Profile, post_save, 'instance'),
    ]

    delete_signals = [
        (ReviewRequest, post_delete),
        (User, post_delete),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize the signal processor.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent constructor.

            **kwargs (dict):
                Keyword arguments to pass to the parent constructor.
        """
        self.is_setup = False
        self._handlers = {}
        self._pending_user_changes = threading.local()

        super(SignalProcessor, self).__init__(*args, **kwargs)

    def setup(self):
        """Register the signal handlers for this processor."""

        # We define this here instead of at the class level because we cannot
        # reference class members during the class' definition.
        m2m_changed_signals = [
            (Group.users.through, self._handle_group_m2m_changed),
        ]

        if not self.is_setup:
            for cls, signal, instance_kwarg in self.save_signals:
                handler = partial(self.check_handle_save,
                                  instance_kwarg=instance_kwarg)
                self._handlers[(cls, signal)] = handler

            for cls, signal in self.delete_signals:
                self._handlers[(cls, signal)] = self.check_handle_delete

            for cls, handler in m2m_changed_signals:
                self._handlers[(cls, m2m_changed)] = handler

            for (cls, signal), handler in six.iteritems(self._handlers):
                signal.connect(handler, sender=cls)

            self.is_setup = True

    def teardown(self):
        """Unregister all signal handlers for this processor."""
        if self.is_setup:
            for (cls, signal), handler in six.iteritems(self._handlers):
                signal.disconnect(handler, sender=cls)

            self.is_setup = False

    def check_handle_save(self, instance_kwarg, **kwargs):
        """Conditionally update the search index when an object is updated.

        Args:
            instance_kwarg (unicode):
                The name of the instance parameter.

            **kwargs (dict):
                Signal arguments. These will be passed to
                :py:meth:`handle_save`.
        """
        instance = kwargs.pop(instance_kwarg)
        backend = search_backend_registry.current_backend

        if backend and search_backend_registry.on_the_fly_indexing_enabled:
            if isinstance(instance, Profile):
                # When we save a Profile, we want to update the User index.
                kwargs['sender'] = User
                instance = instance.user

            self.handle_save(instance=instance, **kwargs)

    def check_handle_delete(self, **kwargs):
        """Conditionally update the search index when an object is deleted.

        Args:
            **kwargs (dict):
                Signal arguments. These will be passed to
                :py:meth:`handle_delete`.
        """
        backend = search_backend_registry.current_backend

        if backend and search_backend_registry.on_the_fly_indexing_enabled:
            self.handle_delete(**kwargs)

    def _handle_group_m2m_changed(self, instance, action, pk_set, reverse,
                                  **kwargs):
        """Handle a Group.users relation changing.

        When the :py:attr:`Group.users
        <reviewboard.reviews.models.group.Group.users>` field changes, we don't
        get a corresponding :py:data:`~django.db.signals.post_save` signal
        (because the related model wasn't saved). Instead, we will get multiple
        :py:data:`~django.db.signals.m2m_changed` signals that indicate how the
        relation is changing. This method will handle those signals and
        call the correct save method so  that they can be re-indexed.

        Args:
            instance (django.contrib.auth.models.User or reviewboward.reviews.models.group.Group):
                The model that updated.

            action (unicode):
                The update action. This will be one of:

                * ``'pre_add'``
                * ``'post_add'``
                * ``'pre_remove'``
                * ``'post_remove'``
                * ``'pre_clear'``
                * ``'post_clear'``

            pk_set (set of int):
                The primary keys of the related objects that changed.

                When the action is ``'pre_clear'`` or ``'post_clear'``,
                this argument will be an empty set.

            reverse (bool):
                Whether or not the reverse relation was modified. If
                true, this indicated that ``instance`` is a
                :py:class:`~django.contrib.auth.models.User` object and
                ``pk_set`` is the set of primary keys of the added or removed
                groups.

                When this argument is false, ``instance`` is a
                :py:class:`~reviewboard.reviews.models.group.Group`
                object and ``pk_set`` is the set of primary keys of the added
                or removed users.

            **kwargs (dict):
                Additional keyword arguments.
        """
        backend = search_backend_registry.current_backend

        if not (backend and
                search_backend_registry.on_the_fly_indexing_enabled):
            return

        if not hasattr(self._pending_user_changes, 'data'):
            self._pending_user_changes.data = {}

        if action in ('post_add', 'post_remove'):
            if reverse:
                # When using the reverse relation, the instance is the User and
                # the pk_set is the PKs of the groups being added or removed.
                users = [instance]
            else:
                # Otherwise the instance is the Group and the pk_set is the set
                # of User primary keys.
                users = User.objects.filter(pk__in=pk_set)

            for user in users:
                self.handle_save(instance=user, instance_kwarg='instance',
                                 sender=User)
        elif action == 'pre_clear':
            # When ``reverse`` is ``True``, a User is having their groups
            # cleared so we don't need to worry about storing any state in the
            # pre_clear  phase.
            #
            # Otherwise, a ReviewGroup is having their users cleared. In both
            # the pre_clear and post_clear phases, the ``pk_set`` argument will
            # be empty, so we cache the PKs of the current members of the
            # groups so we know to reindex them.
            if not reverse:
                self._pending_user_changes.data[instance.pk] = list(
                    instance.users.values_list('pk', flat=True))
        elif action == 'post_clear':
            if reverse:
                # When ``reverse`` is ``True``, we just have to reindex a
                # single user.
                self.handle_save(instance=instance, instance_kwarg='instance',
                                 sender=User)
            else:
                # Here, we are reindexing every user that got removed from the
                # group via clearing.
                pks = self._pending_user_changes.data.pop(instance.pk)

                for user in User.objects.filter(pk__in=pks):
                    self.handle_save(instance=user, instance_kwarg='instance',
                                     sender=User)
