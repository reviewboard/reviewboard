from __future__ import unicode_literals

from django.dispatch import Signal

#: Emitted when a review request is publishing.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user publishing the review request.
#:
#:     review_request_draft (reviewboard.reviews.models.ReviewRequestDraft):
#:         The review request draft being published.
review_request_publishing = Signal(providing_args=['user',
                                                   'review_request_draft'])

#: Emitted when a review request is published.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user who published the review request.
#:
#:     review_request_draft (reviewboard.reviews.models.ReviewRequestDraft):
#:         The review request draft that was published.
review_request_published = Signal(providing_args=['user', 'review_request',
                                                  'trivial', 'changedesc'])

#: Emitted when a review request is about to be closed.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user closing the review request.
#:
#:     review_request (reviewboard.reviews.models.ReviewRequest):
#:         The review request being closed.
#:
#:     type (unicode):
#:         Describes how the review request is being closed. It is one of
#:         :py:data:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED` or
#:         :py:data:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.
#:
#:     description (unicode):
#:         The provided closing description.
#:
#:     rich_text (bool):
#:         Whether or not the description is rich text (Markdown).
review_request_closing = Signal(providing_args=['user', 'review_request',
                                                'type', 'description',
                                                'rich_text'])

#: Emitted when a review request has been closed.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user who closed the review request.
#:
#:     review_request (reviewboard.reviews.models.ReviewRequest):
#:         The review request that was closed.
#:
#:     type (unicode):
#:         Describes how the review request was closed. It is one of
#:         :py:data:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED` or
#:         :py:data:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.
#:
#:     description (unicode):
#:         The provided closing description.
#:
#:     rich_text (bool):
#:         Whether or not the description is rich text (Markdown).
review_request_closed = Signal(providing_args=['user', 'review_request',
                                               'type', 'description',
                                               'rich_text'])

#: Emitted when a review request is about to be reopened.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user re-opening the review request.
#:
#:     review_request (reviewboard.reviews.models.ReviewRequest):
#:         The review request being reopened.
review_request_reopening = Signal(providing_args=['user', 'review_request'])

#: Emitted when a review request has been reopened.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user who re-opened the review request.
#:
#:     review_request (reviewboard.reviews.models.ReviewRequest):
#:         The review request that was reopened.
review_request_reopened = Signal(providing_args=['user', 'review_request'])


#: Emitted when a review is being published.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user publishing the review.
#:
#:     review (reviewboard.reviews.models.Review):
#:         The review that's being published.
review_publishing = Signal(providing_args=['user', 'review'])

#: Emitted when a review has been published.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user who published the review request.
#:
#:     review (reviewboard.reviews.models.Review):
#:         The review that was published.
review_published = Signal(providing_args=['user', 'review'])

#: Emitted when a reply to a review is being published.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user publishing the reply.
#:
#:     review (reviewboard.reviews.models.Review):
#:         The reply that's being published.
reply_publishing = Signal(providing_args=['user', 'reply'])

#: Emitted when a reply to a review has ben published.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user who published the reply.
#:
#:     review (reviewboard.reviews.models.Review):
#:         The reply that was published.
#:
#:     trivial (bool):
#:         Whether the reply was considered trivial.
reply_published = Signal(providing_args=['user', 'reply', 'trivial'])
