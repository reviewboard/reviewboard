"""Review Board e-mail module."""

from __future__ import absolute_import, unicode_literals

import email

from django.db.models.signals import post_delete, post_save
from djblets.auth.signals import user_registered

from reviewboard.notifications.email.signal_handlers import (
    reply_published_cb,
    review_published_cb,
    review_request_closed_cb,
    review_request_published_cb,
    user_registered_cb,
    webapi_token_deleted_cb,
    webapi_token_saved_cb)
from reviewboard.notifications.email.hooks import (register_email_hook,
                                                   unregister_email_hook)
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.webapi.models import WebAPIToken


def connect_signals():
    """Connect e-mail callbacks to signals."""
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
    review_published.connect(review_published_cb, sender=Review)
    reply_published.connect(reply_published_cb, sender=Review)
    review_request_closed.connect(review_request_closed_cb,
                                  sender=ReviewRequest)
    user_registered.connect(user_registered_cb)
    post_save.connect(webapi_token_saved_cb, sender=WebAPIToken)
    post_delete.connect(webapi_token_deleted_cb, sender=WebAPIToken)


# Fixes bug #3613
_old_header_init = email.header.Header.__init__


def _unified_header_init(self, *args, **kwargs):
    kwargs['continuation_ws'] = b' '

    _old_header_init(self, *args, **kwargs)


email.header.Header.__init__ = _unified_header_init


__all__ = [
    'register_email_hook',
    'unregister_email_hook',
]
