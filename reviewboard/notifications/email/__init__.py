"""Review Board e-mail module."""

from __future__ import absolute_import, unicode_literals

import email

from django.db.models.signals import post_delete, post_save
from djblets.auth.signals import user_registered

from reviewboard.notifications.email.signal_handlers import (
    send_password_changed_mail,
    send_reply_published_mail,
    send_review_published_mail,
    send_review_request_closed_mail,
    send_review_request_published_mail,
    send_user_registered_mail,
    send_webapi_token_deleted_mail,
    send_webapi_token_saved_mail)
from reviewboard.notifications.email.hooks import (register_email_hook,
                                                   unregister_email_hook)
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.webapi.models import WebAPIToken


def connect_signals():
    """Connect e-mail callbacks to signals."""
    reply_published.connect(send_reply_published_mail, sender=Review)
    review_published.connect(send_review_published_mail, sender=Review)
    review_request_closed.connect(send_review_request_closed_mail,
                                  sender=ReviewRequest)
    review_request_published.connect(send_review_request_published_mail,
                                     sender=ReviewRequest)
    user_registered.connect(send_user_registered_mail)
    post_delete.connect(send_webapi_token_deleted_mail, sender=WebAPIToken)
    post_save.connect(send_webapi_token_saved_mail, sender=WebAPIToken)

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
