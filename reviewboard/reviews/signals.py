from __future__ import unicode_literals

from django.dispatch import Signal

review_request_publishing = Signal(providing_args=['user',
                                                   'review_request_draft'])

review_request_published = Signal(providing_args=['user', 'review_request',
                                                  'changedesc'])

#: Emitted when a review request is about to be closed.
#:
#: Args:
#:     user (User):
#:         The user closing the review request.
#:
#:     review_request (ReviewRequest):
#:         The review request being closed.
#:
#:     type (unicode):
#:         Describes how the review request is being closed. It is one of
#          ``ReviewRequest.SUBMITTED`` or ``ReviewRequest.DISCARDED``.
#:
#:     description (unicode):
#:         The provided closing description.
#:
#:     rich_text (bool):
#:         Whether or not the description is rich text (Markdown).
review_request_closing = Signal(providing_args=['user', 'review_request',
                                                'type', 'description',
                                                'rich_text'])


review_request_closed = Signal(providing_args=['user', 'review_request',
                                               'type'])

#: Emitted when a review request is about to be reopened.
#:
#: Args:
#:     user (User):
#:         The user re-opening the review request.
#:
#:     review_request (ReviewRequest):
#:         The review request being reopened.
review_request_reopening = Signal(providing_args=['user', 'review_request'])

review_request_reopened = Signal(providing_args=['user', 'review_request'])


review_publishing = Signal(providing_args=['user', 'review'])

review_published = Signal(providing_args=['user', 'review'])

reply_publishing = Signal(providing_args=['user', 'reply'])

reply_published = Signal(providing_args=['user', 'reply'])
