"""Extension hooks for augmenting e-mail messages."""

from __future__ import unicode_literals

import warnings
from collections import defaultdict
from inspect import getargspec

from reviewboard.deprecation import RemovedInReviewBoard40Warning
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)


# A mapping of signals to EmailHooks.
_hooks = defaultdict(set)

# A mapping of signals to newly added arguments.
#
# See _call_hook_compat.
_hook_compat = defaultdict(list)
_hook_compat.update({
    review_published: ['to_owner_only'],
})


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
    optional_args = _hook_compat.get(signal)

    if signal in _hooks:
        for hook in _hooks[signal]:
            to_field = _call_hook_compat(
                hook,
                hook.get_to_field,
                optional_args=optional_args,
                value=to_field,
                **kwargs
            )
            cc_field = _call_hook_compat(
                hook,
                hook.get_cc_field,
                optional_args=optional_args,
                value=cc_field,
                **kwargs
            )

    return to_field, cc_field


def _call_hook_compat(hook, method, optional_args, value, **kwargs):
    """Call a hook in a backwards-compatible manner.

    This method allows newer versions of Review Board to add new arguments to
    EMail hooks without breaking backwards compatability. Instead, we inspect
    the method that would be called and if it does not accept any of the
    arguments listed in ``optional_args``, they will not be passed to the
    function and a warning will be emitted.

    Args:
        method (callable):
            The method on the
            :py:class:`reviewboard.extensions.hooks.EmailHook` class.

        optional_args (list of str):
            The names of the arguments that the hook may not have.

        value (object):
            The value to pass to the hook.

        **kwargs (dict):
            The keyword arguments that will be passed to ``method``.

    Returns:
        object:
        The return value of the passed method.
    """
    argspec = getargspec(method)
    removed = False

    if argspec.keywords is None:
        for arg in optional_args or []:
            if arg not in argspec.args:
                removed = True
                del kwargs[arg]

    if removed:
        warnings.warn(
            '%s.%s should accept **kwargs. Some arguments may not be passed '
            'to the hook.'
            % (hook.__name__, method.__name__),
            RemovedInReviewBoard40Warning
        )

    return method(value, **kwargs)
