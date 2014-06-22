from __future__ import unicode_literals

import hmac
import logging

from django.contrib.sites.models import Site
from django.http.request import HttpRequest
from django.utils.six.moves.urllib.request import Request, urlopen
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.encoders import BasicAPIEncoder, JSONEncoderAdapter

from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import ReviewRequest
from reviewboard.reviews.signals import review_request_published
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

    def __init__(self):
        super(FakeHTTPRequest, self).__init__()

        if self._secure is None:
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


def review_request_published_cb(sender, user, review_request, changedesc,
                                **kwargs):
    event = 'review_request_published'
    handlers = get_handlers(event, review_request.local_site)

    if handlers:
        request = FakeHTTPRequest()
        payload = {
            'is_new': changedesc is None,
            'review_request_id': review_request.get_display_id(),
            'review_request': resources.review_request.serialize_object(
                review_request, request=request),
        }

        if changedesc:
            payload['change'] = resources.change.serialize_object(
                changedesc, request=request),

        dispatch(request, handlers, event, payload)


def connect_signals():
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
