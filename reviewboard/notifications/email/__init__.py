"""Review Board e-mail module."""

from __future__ import absolute_import, unicode_literals

import email

from django.db.models.signals import post_delete
from djblets.auth.signals import user_registered

from reviewboard.notifications.email.signal_handlers import (
    send_reply_published_mail,
    send_review_published_mail,
    send_review_request_closed_mail,
    send_review_request_published_mail,
    send_user_registered_mail,
    send_webapi_token_created_mail,
    send_webapi_token_deleted_mail,
    send_webapi_token_updated_mail)
from reviewboard.notifications.email.hooks import (register_email_hook,
                                                   unregister_email_hook)
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.webapi.models import WebAPIToken
from djblets.webapi.signals import webapi_token_created, webapi_token_updated

def connect_signals():
    """Connect e-mail callbacks to signals."""
    signal_table = [
        (reply_published, send_reply_published_mail, Review),
        (review_published, send_review_published_mail, Review),
        (review_request_closed, send_review_request_closed_mail,
         ReviewRequest),
        (review_request_published, send_review_request_published_mail,
         ReviewRequest),
        (user_registered, send_user_registered_mail, None),
        (webapi_token_created, send_webapi_token_created_mail, WebAPIToken),
        (webapi_token_updated, send_webapi_token_updated_mail, WebAPIToken),
        (post_delete, send_webapi_token_deleted_mail, WebAPIToken),
    ]

    for signal, handler, sender in signal_table:
        signal.connect(handler, sender=sender)


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
