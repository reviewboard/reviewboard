"""Extension hooks for augmenting e-mail messages."""

from __future__ import unicode_literals

import warnings
from collections import defaultdict
from inspect import getargspec

from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)


# A mapping of signals to EmailHooks.
_hooks = defaultdict(set)


def register_email_hook(signal, handler):
    """Register an e-mail hook.

    Args:
        signal (django.dispatch.Signal):
            The signal that will trigger the e-mail to be sent. This is one of
            :py:data:`~reviewboard.reviews.signals.review_request_published`,
            :py:data:`~reviewboard.reviews.signals.review_request_closed`,
            :py:data:`~reviewboard.reviews.signals.review_published`, or
            :py:data:`~reviewboard.reviews.signals.reply_published`.

        handler (reviewboard.extensions.hooks.EmailHook):
            The ``EmailHook`` that will be triggered when an e-mail of the
            chosen type is about to be sent.
    """
    assert signal in (review_request_published, review_request_closed,
                      review_published, reply_published), (
        'Invalid signal %r' % signal)

    _hooks[signal].add(handler)


def unregister_email_hook(signal, handler):
    """Unregister an e-mail hook.

    Args:
        signal (django.dispatch.Signal):
            The signal that will trigger the e-mail to be sent. This is one of
            :py:data:`~reviewboard.reviews.signals.review_request_published`,
            :py:data:`~reviewboard.reviews.signals.review_request_closed`,
            :py:data:`~reviewboard.reviews.signals.review_published`, or
            :py:data:`~reviewboard.reviews.signals.reply_published`.

        handler (reviewboard.extensions.hooks.EmailHook):
            The ``EmailHook`` that will be triggered when an e-mail of the
            chosen type is about to be sent.
    """
    assert signal in (review_request_published, review_request_closed,
                      review_published, reply_published), (
        'Invalid signal %r' % signal)

    _hooks[signal].discard(handler)


def filter_email_recipients_from_hooks(to_field, cc_field, signal, **kwargs):
    """Filter the e-mail recipients through configured e-mail hooks.

    Args:
        to_field (set):
            The original To field of the e-mail, as a set of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        cc_field (set):
            The original CC field of the e-mail, as a set of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        signal (django.dispatch.Signal):
            The signal that triggered the e-mail.

        **kwargs (dict):
            Extra keyword arguments to pass to the e-mail hook.

    Returns:
        tuple:
        A 2-tuple of the To field and the CC field, as sets of
        :py:class:`Users <django.contrib.auth.models.User>` and
        :py:class:`Groups <reviewboard.reviews.models.Group>`.
    """
    if signal in _hooks:
        for hook in _hooks[signal]:
            to_field = hook.get_to_field(to_field, **kwargs)
            cc_field = hook.get_cc_field(cc_field, **kwargs)

    return to_field, cc_field
