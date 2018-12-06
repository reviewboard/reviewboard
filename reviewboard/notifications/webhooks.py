from __future__ import unicode_literals

import hashlib
import hmac
import logging
from collections import OrderedDict
from datetime import datetime

from django.contrib.sites.models import Site
from django.db.models import Model
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils import six
from django.utils.encoding import force_text
from django.utils.safestring import SafeText
from django.utils.six.moves.urllib.parse import (urlencode, urlsplit,
                                                 urlunsplit)
from django.utils.six.moves.urllib.request import (
    HTTPBasicAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener)
from django.utils.translation import ugettext as _
from django.template import Context, Template
from django.template.base import Lexer, Parser
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.encoders import (BasicAPIEncoder, JSONEncoderAdapter,
                                     ResourceAPIEncoder, XMLEncoderAdapter)

from reviewboard import get_package_version
from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import Review, ReviewRequest
from reviewboard.reviews.signals import (review_request_closed,
                                         review_request_published,
                                         review_request_reopened,
                                         review_published,
                                         reply_published)


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

    def __init__(self, user, local_site_name=None):
        """Initialize a FakeHTTPRequest.

        Args:
            user (django.contrib.auth.models.User):
                The user who initiated the request.

            local_site_name (unicode, optional):
                The local site name (if the request was carried out against a
                local site).
        """
        super(FakeHTTPRequest, self).__init__()

        self.user = user
        self._local_site_name = local_site_name

        if self._is_secure is None:
            siteconfig = SiteConfiguration.objects.get_current()
            self._is_secure = siteconfig.get('site_domain_method') == 'https'
            self._host = Site.objects.get_current().domain

    def is_secure(self):
        return self._is_secure

    def get_host(self):
        return self._host


class CustomPayloadParser(Parser):
    """A custom template parser that blocks certain tags.

    This extends Django's Parser class for template parsing, and removes
    some built-in tags, in order to prevent mailicious use.
    """
    BLACKLISTED_TAGS = ('block', 'debug', 'extends', 'include', 'load', 'ssi')

    def __init__(self, *args, **kwargs):
        super(CustomPayloadParser, self).__init__(*args, **kwargs)

        # Remove some built-in tags that we don't want to expose.
        # There are no built-in filters we have to worry about.
        for tag_name in self.BLACKLISTED_TAGS:
            try:
                del self.tags[tag_name]
            except KeyError:
                pass


def render_custom_content(body, context_data={}):
    """Renders custom content for the payload using Django templating.

    This will take the custom payload content template provided by
    the user and render it using a stripped down version of Django's
    templating system.

    In order to keep the payload safe, we use a limited Context along with a
    custom Parser that blocks certain template tags. This gives us
    tags like {% for %} and {% if %}, but blacklists tags like {% load %}
    and {% include %}.
    """
    lexer = Lexer(body, origin=None)
    parser = CustomPayloadParser(lexer.tokenize())
    template = Template('')
    template.nodelist = parser.parse()

    return template.render(Context(context_data))


def normalize_webhook_payload(payload, request):
    """Normalize a payload for a WebHook, returning a safe, primitive version.

    This will take a payload containing various data types and model references
    and turn it into a payload built out of specific, whitelisted types
    (strings, bools, ints, dicts, lists, and datetimes). This payload is
    safe to include in custom templates without worrying about access to
    dangerous functions, and is easy to serialize.

    Args:
        payload (dict):
            The payload to normalize.

        request (django.http.HttpRequest):
            The HTTP request from the client.

    Returns:
        dict:
        The normalized payload.

    Raises:
        TypeError:
            An unsupported data type was found in the payload. This is an
            issue with the caller.
    """
    def _normalize_key(key):
        if key is None:
            return None

        if isinstance(key, (SafeText, bool, float)):
            return six.text_type(key)
        elif isinstance(key, bytes):
            return force_text(key)
        elif isinstance(key, (int, long, six.text_type)):
            return key

        raise TypeError(
            _('%s is not a valid data type for dictionary keys in '
              'WebHook payloads.')
            % type(key))

    def _normalize_value(value):
        if value is None:
            return None

        if isinstance(value, SafeText):
            return six.text_type(value)
        elif isinstance(value, bytes):
            return force_text(value)
        elif isinstance(value, (bool, datetime, float, int, long,
                                six.text_type)):
            return value
        elif isinstance(value, dict):
            return OrderedDict(
                (_normalize_key(dict_key), _normalize_value(dict_value))
                for dict_key, dict_value in six.iteritems(value)
            )
        elif isinstance(value, (list, tuple)):
            return [
                _normalize_value(item)
                for item in value
            ]
        elif isinstance(value, (Model, QuerySet)):
            result = resource_encoder.encode(value, request=request)

            if result is not None:
                return _normalize_value(result)

        raise TypeError(
            _('%s is not a valid data type for values in WebHook payloads.')
            % type(value))

    resource_encoder = ResourceAPIEncoder()

    return _normalize_value(payload)


def dispatch_webhook_event(request, webhook_targets, event, payload):
    """Dispatch the given event and payload to the given WebHook targets.

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        webhook_targets (list of
                         reviewboard.notifications.models.WebHookTarget):
            The list of WebHook targets containing endpoint URLs to dispatch
            to.

        event (unicode):
            The name of the event being dispatched.

        payload (dict):
            The payload data to encode for the WebHook payload.

    Raises:
        ValueError:
            There was an error with the payload format. Details are in the
            log and the exception message.
    """
    try:
        payload = normalize_webhook_payload(payload, request)
    except TypeError as e:
        logging.exception('WebHook payload passed to dispatch_webhook_event '
                          'containing invalid data types: %s',
                          e)

        raise ValueError(six.text_type(e))

    encoder = BasicAPIEncoder()
    bodies = {}

    for webhook_target in webhook_targets:
        if webhook_target.use_custom_content:
            try:
                body = render_custom_content(webhook_target.custom_content,
                                             payload)
                body = body.encode('utf-8')
            except Exception as e:
                logging.exception('Could not render WebHook payload: %s', e)
                continue
        else:
            encoding = webhook_target.encoding

            if encoding not in bodies:
                try:
                    if encoding == webhook_target.ENCODING_JSON:
                        adapter = JSONEncoderAdapter(encoder)
                        body = adapter.encode(payload, request=request)
                        body = body.encode('utf-8')
                    elif encoding == webhook_target.ENCODING_XML:
                        adapter = XMLEncoderAdapter(encoder)
                        body = adapter.encode(payload, request=request)
                    elif encoding == webhook_target.ENCODING_FORM_DATA:
                        adapter = JSONEncoderAdapter(encoder)
                        body = urlencode({
                            'payload': adapter.encode(payload,
                                                      request=request),
                        })
                        body = body.encode('utf-8')
                    else:
                        logging.error('Unexpected WebHookTarget encoding "%s" '
                                      'for ID %s',
                                      encoding, webhook_target.pk)
                        continue
                except Exception as e:
                    logging.exception('Could not encode WebHook payload: %s',
                                      e)
                    continue

                bodies[encoding] = body
            else:
                body = bodies[encoding]

        headers = {
            b'X-ReviewBoard-Event': event.encode('utf-8'),
            b'Content-Type': webhook_target.encoding.encode('utf-8'),
            b'Content-Length': len(body),
            b'User-Agent':
                ('ReviewBoard-WebHook/%s' % get_package_version())
                .encode('utf-8'),
        }

        if webhook_target.secret:
            signer = hmac.new(webhook_target.secret.encode('utf-8'), body,
                              hashlib.sha1)
            headers[b'X-Hub-Signature'] = \
                ('sha1=%s' % signer.hexdigest()).encode('utf-8')

        logging.info('Dispatching webhook for event %s to %s',
                     event, webhook_target.url)
        try:
            url = webhook_target.url
            url_parts = urlsplit(url)

            if url_parts.username or url_parts.password:
                netloc = url_parts.netloc.split('@', 1)[1]
                url = urlunsplit(
                    (url_parts.scheme, netloc, url_parts.path,
                     url_parts.params, url_parts.query))

                password_mgr = HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(
                    None, url, url_parts.username, url_parts.password)
                handler = HTTPBasicAuthHandler(password_mgr)
                opener = build_opener(handler)
            else:
                opener = build_opener()

            opener.open(Request(url.encode('utf-8'), body, headers))
        except Exception as e:
            logging.exception('Could not dispatch WebHook to %s: %s',
                              webhook_target.url, e)


def _serialize_review(review, request):
    return {
        'review_request': review.review_request,
        'review': review,
        'diff_comments': review.comments.all(),
        'file_attachment_comments': review.file_attachment_comments.all(),
        'screenshot_comments': review.screenshot_comments.all(),
        'general_comments': review.general_comments.all(),
    }


def _serialize_reply(reply, request):
    return {
        'review_request': reply.review_request,
        'reply': reply,
        'diff_comments': reply.comments.all(),
        'file_attachment_comments': reply.file_attachment_comments.all(),
        'screenshot_comments': reply.screenshot_comments.all(),
        'general_comments': reply.general_comments.all(),
    }


def review_request_closed_cb(user, review_request, close_type, **kwargs):
    event = 'review_request_closed'
    webhook_targets = WebHookTarget.objects.for_event(
        event, review_request.local_site_id, review_request.repository_id)

    if review_request.local_site_id:
        local_site_name = review_request.local_site.name
    else:
        local_site_name = None

    if webhook_targets:
        if close_type == review_request.SUBMITTED:
            close_type = 'submitted'
        elif close_type == review_request.DISCARDED:
            close_type = 'discarded'
        else:
            logging.error('Unexpected close type %s for review request %s '
                          'when dispatching webhook.',
                          type, review_request.pk)
            return

        if not user:
            user = review_request.submitter

        request = FakeHTTPRequest(user, local_site_name=local_site_name)
        payload = {
            'event': event,
            'closed_by': user,
            'close_type': close_type,
            'review_request': review_request,
        }

        try:
            dispatch_webhook_event(request, webhook_targets, event, payload)
        except ValueError:
            # The error has already been logged. Don't impact the caller.
            pass


def review_request_published_cb(user, review_request, changedesc,
                                **kwargs):
    event = 'review_request_published'
    webhook_targets = WebHookTarget.objects.for_event(
        event, review_request.local_site_id, review_request.repository_id)

    if review_request.local_site_id:
        local_site_name = review_request.local_site.name
    else:
        local_site_name = None

    if webhook_targets:
        request = FakeHTTPRequest(user, local_site_name=local_site_name)
        payload = {
            'event': event,
            'is_new': changedesc is None,
            'review_request': review_request,
        }

        if changedesc:
            payload['change'] = changedesc

        try:
            dispatch_webhook_event(request, webhook_targets, event, payload)
        except ValueError:
            # The error has already been logged. Don't impact the caller.
            pass


def review_request_reopened_cb(user, review_request, **kwargs):
    event = 'review_request_reopened'
    webhook_targets = WebHookTarget.objects.for_event(
        event, review_request.local_site_id, review_request.repository_id)

    if review_request.local_site_id:
        local_site_name = review_request.local_site.name
    else:
        local_site_name = None

    if webhook_targets:
        if not user:
            user = review_request.submitter

        request = FakeHTTPRequest(user, local_site_name=local_site_name)
        payload = {
            'event': event,
            'reopened_by': user,
            'review_request': review_request,
        }

        try:
            dispatch_webhook_event(request, webhook_targets, event, payload)
        except ValueError:
            # The error has already been logged. Don't impact the caller.
            pass


def review_published_cb(user, review, **kwargs):
    event = 'review_published'
    review_request = review.review_request
    webhook_targets = WebHookTarget.objects.for_event(
        event, review_request.local_site_id, review_request.repository_id)

    if review_request.local_site_id:
        local_site_name = review_request.local_site.name
    else:
        local_site_name = None

    if webhook_targets:
        request = FakeHTTPRequest(user, local_site_name=local_site_name)
        payload = _serialize_review(review, request)
        payload['event'] = event

        try:
            dispatch_webhook_event(request, webhook_targets, event, payload)
        except ValueError:
            # The error has already been logged. Don't impact the caller.
            pass


def reply_published_cb(user, reply, **kwargs):
    event = 'reply_published'
    review_request = reply.review_request
    webhook_targets = WebHookTarget.objects.for_event(
        event, review_request.local_site_id, review_request.repository_id)

    if review_request.local_site_id:
        local_site_name = review_request.local_site.name
    else:
        local_site_name = None

    if webhook_targets:
        request = FakeHTTPRequest(user, local_site_name=local_site_name)
        payload = _serialize_reply(reply, request)
        payload['event'] = event

        try:
            dispatch_webhook_event(request, webhook_targets, event, payload)
        except ValueError:
            # The error has already been logged. Don't impact the caller.
            pass


def connect_signals():
    review_request_closed.connect(review_request_closed_cb,
                                  sender=ReviewRequest)
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
    review_request_reopened.connect(review_request_reopened_cb,
                                    sender=ReviewRequest)

    review_published.connect(review_published_cb, sender=Review)
    reply_published.connect(reply_published_cb, sender=Review)
