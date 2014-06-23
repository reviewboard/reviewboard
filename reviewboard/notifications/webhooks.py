from __future__ import unicode_literals

import hmac
import logging

from django.contrib.sites.models import Site
from django.http.request import HttpRequest
from django.utils.six.moves.urllib.request import Request, urlopen
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.encoders import BasicAPIEncoder, JSONEncoderAdapter

from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import Review, ReviewRequest
from reviewboard.reviews.signals import (review_request_closed,
                                         review_request_published,
                                         review_request_reopened,
                                         review_published,
                                         reply_published)
from reviewboard.webapi.resources import resources


class FakeHTTPRequest(HttpRequest):
    """A fake HttpRequest implementation.

    The WebAPI serialization methods use HttpRequest.build_absolute_uri to
    generate all the links, but none of the various signals that generate
    webhook events have the request plumbed through. Since we don't actually
    need a valid request, this impersonates it enough to get valid results from
    build_absolute_uri.
    """
    _is_secure = None
    _host = None

    def __init__(self, user):
        super(FakeHTTPRequest, self).__init__()

        self.user = user

        if self._is_secure is None:
            siteconfig = SiteConfiguration.objects.get_current()
            self._is_secure = siteconfig.get('site_domain_method') == 'https'
            self._host = Site.objects.get_current().domain

    def is_secure(self):
        return self._is_secure

    def get_host(self):
        return self._host


def get_handlers(event, local_site):
    """Get a list of matching webhook handlers for the given event."""
    return [
        target
        for target in WebHookTarget.objects.filter(local_site=local_site,
                                                   enabled=True)
        if event in target.handlers or '*' in target.handlers
    ]


def dispatch(request, handlers, event, payload):
    """Dispatch the given event and payload to the given handlers."""
    encoder = BasicAPIEncoder()
    adapter = JSONEncoderAdapter(encoder)
    body = adapter.encode(payload, request=request)
    body = body.encode('utf-8')

    headers = {
        'X-ReviewBoard-Event': event,
        'Content-Type': 'application/json',
        'Content-Length': len(body),
    }

    for handler in handlers:
        signer = hmac.new(handler.secret.encode('utf-8'), body)
        headers['X-ReviewBoard-Signature'] = signer.hexdigest()

        logging.info('Dispatching webhook for event %s to %s',
                     event, handler.url)
        urlopen(Request(handler.url, body, headers))


def _serialize_review(review, request):
    return {
        'review': resources.review.serialize_object(
            review, request=request),
        'diff_comments': [
            resources.filediff_comment.serialize_object(
                comment, request=request)
            for comment in review.comments.all()
        ],
        'screenshot_comments': [
            resources.screenshot_comment.serialize_object(
                comment, request=request)
            for comment in review.screenshot_comments.all()
        ],
        'file_attachment_comments': [
            resources.file_attachment_comment.serialize_object(
                comment, request=request)
            for comment in review.file_attachment_comments.all()
        ],
    }


def review_request_closed_cb(sender, user, review_request, type,
                             **kwargs):
    event = 'review_request_closed'
    handlers = get_handlers(event, review_request.local_site)

    if handlers:
        request = FakeHTTPRequest(user)
        payload = {
            'event': event,
            'closed_by': resources.user.serialize_object(
                user, request=request),
            'close_type': type,
            'review_request': resources.review_request.serialize_object(
                review_request, request=request),
        }

        dispatch(request, handlers, event, payload)


def review_request_published_cb(sender, user, review_request, changedesc,
                                **kwargs):
    event = 'review_request_published'
    handlers = get_handlers(event, review_request.local_site)

    if handlers:
        request = FakeHTTPRequest(user)
        payload = {
            'event': event,
            'is_new': changedesc is None,
            'review_request': resources.review_request.serialize_object(
                review_request, request=request),
        }

        if changedesc:
            payload['change'] = resources.change.serialize_object(
                changedesc, request=request),

        dispatch(request, handlers, event, payload)


def review_request_reopened_cb(sender, user, review_request, **kwargs):
    event = 'review_request_reopened'
    handlers = get_handlers(event, review_request.local_site)

    if handlers:
        request = FakeHTTPRequest(user)
        payload = {
            'event': event,
            'reopened_by': resources.user.serialize_object(
                user, request=request),
            'review_request': resources.review_request.serialize_object(
                review_request, request=request),
        }

        dispatch(request, handlers, event, payload)


def review_published_cb(sender, user, review, **kwargs):
    event = 'review_published'
    handlers = get_handlers(event, review.review_request.local_site)

    if handlers:
        request = FakeHTTPRequest(user)
        payload = _serialize_review(review, request)
        payload['event'] = event
        dispatch(request, handlers, event, payload)


def reply_published_cb(sender, user, reply, **kwargs):
    event = 'reply_published'
    handlers = get_handlers(event, reply.review_request.local_site)

    if handlers:
        request = FakeHTTPRequest(user)
        payload = _serialize_review(reply, request)
        payload['event'] = event
        dispatch(request, handlers, event, payload)


def connect_signals():
    review_request_closed.connect(review_request_closed_cb,
                                  sender=ReviewRequest)
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
    review_request_reopened.connect(review_request_reopened_cb,
                                    sender=ReviewRequest)

    review_published.connect(review_published_cb, sender=Review)
    reply_published.connect(reply_published_cb, sender=Review)
