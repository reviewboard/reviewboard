from __future__ import unicode_literals

import logging
from collections import OrderedDict
from datetime import datetime

from django.contrib.auth.models import User
from django.template import TemplateSyntaxError
from django.utils import six
from django.utils.safestring import mark_safe
from django.utils.six.moves.urllib.request import OpenerDirector
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.notifications.models import WebHookTarget
from reviewboard.notifications.webhooks import (FakeHTTPRequest,
                                                dispatch_webhook_event,
                                                normalize_webhook_payload,
                                                render_custom_content)
from reviewboard.reviews.models import ReviewRequestDraft
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


if six.PY3:
    # Python 3 doesn't have a long type, which generally makes life easier,
    # except that we want to continue to test with long values in Python 2 for
    # WebHook payloads to avoid regressions. To get around this, we'll just
    # provide a dummy long() that actually returns an int, which is fine for
    # our testing.
    long = int


class WebHookPayloadTests(SpyAgency, TestCase):
    """Tests for payload rendering."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    @add_fixtures(['test_scmtools', 'test_users'])
    def test_diffset_rendered(self):
        """Testing JSON-serializability of DiffSets in WebHook payloads"""
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_original=False)
        WebHookTarget.objects.create(url=self.ENDPOINT_URL,
                                     events='review_request_published')

        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(create_repository=True,
                                                    target_people=[user])
        self.create_diffset(review_request)
        review_request.publish(review_request.submitter)

        self.assertTrue(OpenerDirector.open.spy.called)

        self.create_diffset(review_request, draft=True)
        review_request.publish(review_request.submitter)
        self.assertEqual(len(OpenerDirector.open.spy.calls), 2)


class WebHookCustomContentTests(TestCase):
    """Unit tests for render_custom_content."""

    def test_with_valid_template(self):
        """Testing render_custom_content with a valid template"""
        s = render_custom_content(
            '{% if mybool %}{{s1}}{% else %}{{s2}}{% endif %}',
            {
                'mybool': True,
                's1': 'Hi!',
                's2': 'Bye!',
            })

        self.assertEqual(s, 'Hi!')

    def test_with_blocked_block_tag(self):
        """Testing render_custom_content with blocked {% block %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'block'"):
            render_custom_content('{% block foo %}{% endblock %})')

    def test_with_blocked_debug_tag(self):
        """Testing render_custom_content with blocked {% debug %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'debug'"):
            render_custom_content('{% debug %}')

    def test_with_blocked_extends_tag(self):
        """Testing render_custom_content with blocked {% extends %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'extends'"):
            render_custom_content('{% extends "base.html" %}')

    def test_with_blocked_include_tag(self):
        """Testing render_custom_content with blocked {% include %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'include'"):
            render_custom_content('{% include "base.html" %}')

    def test_with_blocked_load_tag(self):
        """Testing render_custom_content with blocked {% load %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'load'"):
            render_custom_content('{% load i18n %}')

    def test_with_blocked_ssi_tag(self):
        """Testing render_custom_content with blocked {% ssi %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'ssi'"):
            render_custom_content('{% ssi "foo.html" %}')

    def test_with_unknown_vars(self):
        """Testing render_custom_content with unknown variables"""
        s = render_custom_content('{{settings.DEBUG}};{{settings.DATABASES}}')
        self.assertEqual(s, ';')


class WebHookDispatchTests(SpyAgency, TestCase):
    """Unit tests for dispatching webhooks."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    def test_dispatch_custom_payload(self):
        """Testing dispatch_webhook_event with custom payload"""
        custom_content = (
            '{\n'
            '{% for i in items %}'
            '  "item{{i}}": true{% if not forloop.last %},{% endif %}\n'
            '{% endfor %}'
            '}')
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=custom_content)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'items': [1, 2, 3],
            },
            expected_content_type='application/json',
            expected_data=(
                b'{\n'
                b'  "item1": true,\n'
                b'  "item2": true,\n'
                b'  "item3": true\n'
                b'}'
            ))

    def test_dispatch_non_ascii_custom_payload(self):
        """Testing dispatch_webhook_event with non-ASCII custom payload"""
        non_ascii_content = '{"sign": "{{sign|escapejs}}"}'

        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=non_ascii_content)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={'sign': '\u00A4'},
            expected_content_type='application/json',
            expected_data='{"sign": "\u00A4"}'.encode('utf-8')
        )

    def test_dispatch_form_data(self):
        """Testing dispatch_webhook_event with Form Data payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_FORM_DATA)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'items': [1, 2, 3],
            },
            expected_content_type='application/x-www-form-urlencoded',
            expected_data=b'payload=%7B%22items%22%3A+%5B1%2C+2%2C+3%5D%7D')

    def test_dispatch_non_ascii_form_data(self):
        """Testing dispatch_webhook_event with non-ASCII Form Data payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_FORM_DATA)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'sign': '\u00A4',
            },
            expected_content_type='application/x-www-form-urlencoded',
            expected_data=b'payload=%7B%22sign%22%3A+%22%5Cu00a4%22%7D')

    def test_dispatch_json(self):
        """Testing dispatch_webhook_event with JSON payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        payload = OrderedDict()
        payload['items'] = [1, 2, long(3), 4.5, True, 'hi']
        payload['tuple'] = (1, 2, long(3), 4.5, True, 'hi')
        payload['dict'] = {
            'key': 'value',
        }
        payload['ordered_dict'] = OrderedDict([
            (True, True),
            (False, False),
        ])
        payload[b'bytes'] = b'bytes'
        payload[mark_safe('safe')] = mark_safe('safe')
        payload[1] = 1
        payload[2.5] = 2.5
        payload[None] = None

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload=payload,
            expected_content_type='application/json',
            expected_data=(
                b'{"1": 1,'
                b' "2.5": 2.5,'
                b' "bytes": "bytes",'
                b' "dict": {"key": "value"},'
                b' "items": [1, 2, 3, 4.5, true, "hi"],'
                b' "null": null,'
                b' "ordered_dict": {"False": false, "True": true},'
                b' "safe": "safe",'
                b' "tuple": [1, 2, 3, 4.5, true, "hi"]}'
            ))

    def test_dispatch_non_ascii_json(self):
        """Testing dispatch_webhook_event with non-ASCII JSON payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'sign': '\u00A4',
            },
            expected_content_type='application/json',
            expected_data='{"sign": "\\u00a4"}'.encode('utf-8'))

    def test_dispatch_xml(self):
        """Testing dispatch_webhook_event with XML payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_XML)

        payload = OrderedDict()
        payload['items'] = [1, 2, long(3), 4.5, True, 'hi']
        payload['tuple'] = (1, 2, long(3), 4.5, True, 'hi')
        payload['dict'] = {
            'key': 'value',
        }
        payload['ordered_dict'] = OrderedDict([
            (True, True),
            (False, False),
        ])
        payload[b'bytes'] = b'bytes'
        payload[mark_safe('safe')] = mark_safe('safe')
        payload[1] = 1

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload=payload,
            expected_content_type='application/xml',
            expected_data=(
                b'<?xml version="1.0" encoding="utf-8"?>\n'
                b'<rsp>\n'
                b' <items>\n'
                b'  <array>\n'
                b'   <item>1</item>\n'
                b'   <item>2</item>\n'
                b'   <item>3</item>\n'
                b'   <item>4.5</item>\n'
                b'   <item>1</item>\n'
                b'   <item>hi</item>\n'
                b'  </array>\n'
                b' </items>\n'
                b' <tuple>\n'
                b'  <array>\n'
                b'   <item>1</item>\n'
                b'   <item>2</item>\n'
                b'   <item>3</item>\n'
                b'   <item>4.5</item>\n'
                b'   <item>1</item>\n'
                b'   <item>hi</item>\n'
                b'  </array>\n'
                b' </tuple>\n'
                b' <dict>\n'
                b'  <key>value</key>\n'
                b' </dict>\n'
                b' <ordered_dict>\n'
                b'  <True>1</True>\n'
                b'  <False>0</False>\n'
                b' </ordered_dict>\n'
                b' <bytes>bytes</bytes>\n'
                b' <safe>safe</safe>\n'
                b' <int value="1">1</int>\n'
                b'</rsp>'
            ))

    def test_dispatch_non_ascii_xml(self):
        """Testing dispatch_webhook_event with non-ASCII XML payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_XML)

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'sign': '\u00A4',
            },
            expected_content_type='application/xml',
            expected_data=(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<rsp>\n'
                ' <sign>\u00A4</sign>\n'
                '</rsp>'
            ).encode('utf-8'))

    def test_dispatch_with_secret(self):
        """Testing dispatch_webhook_event with HMAC secret"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                secret='foobar123')

        self._test_dispatch(
            handler=handler,
            event='my-event',
            payload={
                'items': [1, 2, 3],
            },
            expected_content_type='application/json',
            expected_data=b'{"items": [1, 2, 3]}',
            expected_sig_header=(b'sha1='
                                 b'46f8529ef47da2291eeb475f0d0c0a6f58f88f8b')
        )

    def test_dispatch_invalid_template(self):
        """Testing dispatch_webhook_event with an invalid template"""
        handler = WebHookTarget(events='my-event', url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=r'{% invalid_block_tag %}')

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_fake=lambda *args, **kwargs: None)

        dispatch_webhook_event(request=FakeHTTPRequest(None),
                               webhook_targets=[handler],
                               event='my-event',
                               payload='{}')

        self.assertFalse(OpenerDirector.open.spy.called)
        self.assertTrue(logging.exception.spy.called)

        log_call = logging.exception.spy.last_call
        self.assertIsInstance(log_call.args[1], TemplateSyntaxError)
        self.assertEqual(six.text_type(log_call.args[1]),
                         "Invalid block tag: 'invalid_block_tag'")

    def test_dispatch_invalid_end_tag(self):
        """Testing dispatch_webhook_event with an invalid end tag in template
        """
        handler = WebHookTarget(
            events='my-event',
            url=self.ENDPOINT_URL,
            encoding=WebHookTarget.ENCODING_JSON,
            use_custom_content=True,
            custom_content=r'{% if 1 %}{% bad_tag %}')

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_fake=lambda *args, **kwargs: None)

        dispatch_webhook_event(request=FakeHTTPRequest(None),
                               webhook_targets=[handler],
                               event='my-event',
                               payload='{}')

        self.assertFalse(OpenerDirector.open.spy.called)
        self.assertTrue(logging.exception.spy.called)

        log_call = logging.exception.spy.last_call
        self.assertIsInstance(log_call.args[1], TemplateSyntaxError)
        self.assertEqual(six.text_type(log_call.args[1]),
                         "Invalid block tag: 'bad_tag', expected 'elif', "
                         "'else' or 'endif'")

    def test_dispatch_render_error(self):
        """Testing dispatch_webhook_event with an unencodable object"""
        class Unencodable(object):
            pass

        handler = WebHookTarget(events='my-event', url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_fake=lambda *args, **kwargs: None)

        message = (
            '%r is not a valid data type for values in WebHook payloads.'
            % Unencodable
        )

        with self.assertRaisesMessage(ValueError, message):
            dispatch_webhook_event(
                FakeHTTPRequest(None),
                [handler],
                'my-event', {
                    'unencodable': Unencodable(),
                })

        self.assertFalse(OpenerDirector.open.called)
        self.assertTrue(logging.exception.called)

        last_call_args = logging.exception.last_call.args
        self.assertEqual(
            last_call_args[0],
            'WebHook payload passed to dispatch_webhook_event containing '
            'invalid data types: %s')
        self.assertIsInstance(last_call_args[1], TypeError)

    def test_dispatch_cannot_open(self):
        """Testing dispatch_webhook_event with an unresolvable URL"""
        def _urlopen(opener, *args, **kwargs):
            raise IOError('')

        handler = WebHookTarget.objects.create(
            events='my-event',
            url=self.ENDPOINT_URL,
            encoding=WebHookTarget.ENCODING_JSON)

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_fake=_urlopen)

        dispatch_webhook_event(request=FakeHTTPRequest(None),
                               webhook_targets=[handler, handler],
                               event='my-event',
                               payload='{}')

        self.assertEqual(len(OpenerDirector.open.spy.calls), 2)
        self.assertTrue(len(logging.exception.spy.calls), 2)
        self.assertIsInstance(logging.exception.spy.calls[0].args[2], IOError)
        self.assertIsInstance(logging.exception.spy.calls[1].args[2], IOError)

    def _test_dispatch(self, handler, event, payload, expected_content_type,
                       expected_data, expected_sig_header=None):
        def _urlopen(opener, request, *args, **kwargs):
            self.assertEqual(request.get_full_url(), self.ENDPOINT_URL)
            self.assertEqual(request.headers[b'X-reviewboard-event'],
                             event.encode('utf-8'))
            self.assertEqual(request.headers[b'Content-type'],
                             expected_content_type.encode('utf-8'))
            self.assertEqual(request.data, expected_data)
            self.assertEqual(request.headers[b'Content-length'],
                             len(expected_data))

            if expected_sig_header:
                self.assertIn(b'X-hub-signature', request.headers)
                self.assertEqual(request.headers[b'X-hub-signature'],
                                 expected_sig_header)
            else:
                self.assertNotIn(b'X-hub-signature', request.headers)

            # Check that all sent data are binary strings.
            for h in request.headers:
                self.assertIsInstance(h, six.binary_type)
                self.assertNotIsInstance(request.headers[h], six.text_type)

            self.assertIsInstance(request.data, six.binary_type)

        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_fake=_urlopen)

        # We need to ensure that logging.exception is not called
        # in order to avoid silent swallowing of test assertion failures
        self.spy_on(logging.exception)

        request = FakeHTTPRequest(None)
        dispatch_webhook_event(request, [handler], event, payload)

        # Assuming that if logging.exception is called, an assertion
        # error was raised - and should thus be raised further.
        if logging.exception.spy.called:
            raise logging.exception.spy.calls[0].args[2]


class WebHookSignalDispatchTests(SpyAgency, TestCase):
    """Unit tests for dispatching webhooks by signals."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    fixtures = ['test_users']

    def setUp(self):
        super(WebHookSignalDispatchTests, self).setUp()

        self.spy_on(OpenerDirector.open,
                    owner=OpenerDirector,
                    call_original=False)
        self.spy_on(dispatch_webhook_event)
        self.spy_on(normalize_webhook_payload)

    def test_review_request_closed_submitted(self):
        """Testing webhook dispatch from 'review_request_closed' signal
        with submitted
        """
        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request(publish=True)
        review_request.close(review_request.SUBMITTED)

        payload = self._check_dispatch_results(target, 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'submitted')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_closed_submitted_local_site(self):
        """Testing webhook dispatch from 'review_request_closed' signal with
        submitted for a local site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL,
                                              local_site=local_site)

        review_request = self.create_review_request(local_site=local_site,
                                                    publish=True)
        review_request.close(review_request.SUBMITTED)

        payload = self._check_dispatch_results(target, 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'submitted')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_closed_discarded(self):
        """Testing webhook dispatch from 'review_request_closed' signal
        with discarded
        """
        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.close(review_request.DISCARDED)

        payload = self._check_dispatch_results(target, 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'discarded')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_closed_discarded_local_site(self):
        """Testing webhook dispatch from 'review_request_closed' signal with
        discarded for a local site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL,
                                              local_site=local_site)

        review_request = self.create_review_request(local_site=local_site,
                                                    publish=True)
        review_request.close(review_request.DISCARDED)

        payload = self._check_dispatch_results(target, 'review_request_closed')
        self.assertEqual(payload['closed_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['close_type'], 'discarded')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_published(self):
        """Testing webhook dispatch from 'review_request_published' signal"""
        target = WebHookTarget.objects.create(
            events='review_request_published',
            url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review_request.publish(review_request.submitter)

        payload = self._check_dispatch_results(target,
                                               'review_request_published')
        self.assertIn('is_new', payload)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_published_local_site(self):
        """Testing webhook dispatch from 'review_request_published' signal for
        a local site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(
            events='review_request_published', url=self.ENDPOINT_URL,
            local_site=local_site)

        review_request = self.create_review_request(local_site=local_site)
        review_request.publish(review_request.submitter)

        payload = self._check_dispatch_results(target,
                                               'review_request_published')
        self.assertIn('is_new', payload)
        self.assertNotIn('change', payload)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_published_with_change(self):
        """Testing webhook dispatch from 'review_request_published' signal
        with change description
        """
        review_request = self.create_review_request()
        review_request.target_people.add(User.objects.get(username='doc'))
        review_request.publish(review_request.submitter)

        target = WebHookTarget.objects.create(
            events='review_request_published',
            url=self.ENDPOINT_URL)

        draft = ReviewRequestDraft.create(review_request)
        draft.summary = 'New summary'
        draft.save()
        review_request.publish(review_request.submitter)

        payload = self._check_dispatch_results(target,
                                               'review_request_published')
        self.assertIn('is_new', payload)
        self.assertIn('change', payload)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_reopened(self):
        """Testing webhook dispatch from 'review_request_reopened' signal"""
        target = WebHookTarget.objects.create(
            events='review_request_reopened',
            url=self.ENDPOINT_URL)

        review_request = self.create_review_request(publish=True)
        review_request.close(review_request.SUBMITTED)
        review_request.reopen()

        payload = self._check_dispatch_results(target,
                                               'review_request_reopened')
        self.assertEqual(payload['reopened_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_request_reopened_local_site(self):
        """Testing webhook dispatch from 'review_request_reopened' signal
        for a local site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(events='review_request_reopened',
                                              url=self.ENDPOINT_URL,
                                              local_site=local_site)

        review_request = self.create_review_request(local_site=local_site,
                                                    publish=True)
        review_request.close(review_request.SUBMITTED)
        review_request.reopen()

        payload = self._check_dispatch_results(target,
                                               'review_request_reopened')
        self.assertEqual(payload['reopened_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    @add_fixtures(['test_scmtools'])
    def test_review_published(self):
        """Testing webhook dispatch from 'review_published' signal"""
        target = WebHookTarget.objects.create(events='review_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request(create_repository=True)
        review = self.create_review(review_request)

        # 1 diff comment.
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        diff_comment_1 = self.create_diff_comment(review, filediff)

        # 2 screenshot comments.
        screenshot = self.create_screenshot(review_request)
        screenshot_comment_1 = self.create_screenshot_comment(review,
                                                              screenshot)
        screenshot_comment_2 = self.create_screenshot_comment(review,
                                                              screenshot)

        # 3 file attachment comments.
        file_attachment = self.create_file_attachment(review_request)
        file_attachment_comment_1 = self.create_file_attachment_comment(
            review, file_attachment)
        file_attachment_comment_2 = self.create_file_attachment_comment(
            review, file_attachment)
        file_attachment_comment_3 = self.create_file_attachment_comment(
            review, file_attachment)

        # 4 general comments.
        general_comment_1 = self.create_general_comment(review)
        general_comment_2 = self.create_general_comment(review)
        general_comment_3 = self.create_general_comment(review)
        general_comment_4 = self.create_general_comment(review)

        review.publish()

        payload = self._check_dispatch_results(target, 'review_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['review']['id'], review.pk)

        self.assertIn('diff_comments', payload)
        comments = payload['diff_comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['id'], diff_comment_1.pk)

        self.assertIn('screenshot_comments', payload)
        comments = payload['screenshot_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['id'], screenshot_comment_1.pk)
        self.assertEqual(comments[1]['id'], screenshot_comment_2.pk)

        self.assertIn('file_attachment_comments', payload)
        comments = payload['file_attachment_comments']
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0]['id'], file_attachment_comment_1.pk)
        self.assertEqual(comments[1]['id'], file_attachment_comment_2.pk)
        self.assertEqual(comments[2]['id'], file_attachment_comment_3.pk)

        self.assertIn('general_comments', payload)
        comments = payload['general_comments']
        self.assertEqual(len(comments), 4)
        self.assertEqual(comments[0]['id'], general_comment_1.pk)
        self.assertEqual(comments[1]['id'], general_comment_2.pk)
        self.assertEqual(comments[2]['id'], general_comment_3.pk)
        self.assertEqual(comments[3]['id'], general_comment_4.pk)

    def test_review_published_local_site(self):
        """Testing webhook dispatch from 'review_published' signal for a local
        site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(events='review_published',
                                              url=self.ENDPOINT_URL,
                                              local_site=local_site)

        review_request = self.create_review_request(local_site=local_site,
                                                    publish=True)
        review = self.create_review(review_request)
        review.publish()

        payload = self._check_dispatch_results(target, 'review_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['review']['id'], review.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)

    @add_fixtures(['test_scmtools'])
    def test_reply_published(self):
        """Testing webhook dispatch from 'reply_published' signal"""
        target = WebHookTarget.objects.create(events='reply_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request(create_repository=True)
        review = self.create_review(review_request)
        reply = self.create_reply(review)

        # 1 diff comment.
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        diff_comment_1 = self.create_diff_comment(
            reply, filediff,
            reply_to=self.create_diff_comment(review, filediff))

        # 2 screenshot comments.
        screenshot = self.create_screenshot(review_request)
        screenshot_comment_1 = self.create_screenshot_comment(
            reply, screenshot,
            reply_to=self.create_screenshot_comment(review, screenshot))
        screenshot_comment_2 = self.create_screenshot_comment(
            reply, screenshot,
            reply_to=self.create_screenshot_comment(review, screenshot))

        # 3 file attachment comments.
        file_attachment = self.create_file_attachment(review_request)
        file_attachment_comment_1 = self.create_file_attachment_comment(
            reply, file_attachment,
            reply_to=self.create_file_attachment_comment(review,
                                                         file_attachment))
        file_attachment_comment_2 = self.create_file_attachment_comment(
            reply, file_attachment,
            reply_to=self.create_file_attachment_comment(review,
                                                         file_attachment))
        file_attachment_comment_3 = self.create_file_attachment_comment(
            reply, file_attachment,
            reply_to=self.create_file_attachment_comment(review,
                                                         file_attachment))

        # 4 general comments.
        general_comment_1 = self.create_general_comment(
            reply,
            reply_to=self.create_general_comment(review))
        general_comment_2 = self.create_general_comment(
            reply,
            reply_to=self.create_general_comment(review))
        general_comment_3 = self.create_general_comment(
            reply,
            reply_to=self.create_general_comment(review))
        general_comment_4 = self.create_general_comment(
            reply,
            reply_to=self.create_general_comment(review))

        review.publish()
        reply.publish()

        payload = self._check_dispatch_results(target, 'reply_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['reply']['id'], reply.pk)

        self.assertIn('diff_comments', payload)
        comments = payload['diff_comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['id'], diff_comment_1.pk)

        self.assertIn('screenshot_comments', payload)
        comments = payload['screenshot_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]['id'], screenshot_comment_1.pk)
        self.assertEqual(comments[1]['id'], screenshot_comment_2.pk)

        self.assertIn('file_attachment_comments', payload)
        comments = payload['file_attachment_comments']
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0]['id'], file_attachment_comment_1.pk)
        self.assertEqual(comments[1]['id'], file_attachment_comment_2.pk)
        self.assertEqual(comments[2]['id'], file_attachment_comment_3.pk)

        self.assertIn('general_comments', payload)
        comments = payload['general_comments']
        self.assertEqual(len(comments), 4)
        self.assertEqual(comments[0]['id'], general_comment_1.pk)
        self.assertEqual(comments[1]['id'], general_comment_2.pk)
        self.assertEqual(comments[2]['id'], general_comment_3.pk)
        self.assertEqual(comments[3]['id'], general_comment_4.pk)

        # Test for bug 3999
        self.assertEqual(payload['reply']['links']['diff_comments']['href'],
                         'http://example.com/api/review-requests/1/reviews/1/'
                         'replies/2/diff-comments/')

    def test_reply_published_local_site(self):
        """Testing webhook dispatch from 'reply_published' signal for a local
        site
        """
        local_site = LocalSite.objects.create(name='test-site')
        local_site.users.add(User.objects.get(username='doc'))

        target = WebHookTarget.objects.create(events='reply_published',
                                              url=self.ENDPOINT_URL,
                                              local_site=local_site)

        review_request = self.create_review_request(local_site=local_site,
                                                    publish=True)
        review = self.create_review(review_request)
        reply = self.create_reply(review)
        reply.publish()

        payload = self._check_dispatch_results(target, 'reply_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['reply']['id'], reply.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)

    def _check_dispatch_results(self, target, event):
        """Check the results from a WebHook dispatch.

        This will ensure that
        :py:meth:`~reviewboard.notifications.webhooks.dispatch_webhook_event`
        has been called with the appropriate arguments, that the payload
        contains only safe types, and that both the event in the payload and in
        the HTTP header are correct.

        Args:
            target (reviewboard.notifications.models.WebHookTarget):
                The target the event is being dispatched to.

            event (unicode):
                The name of the event.

        Returns:
            dict:
            The normalized payload being dispatched.
        """
        self.assertEqual(len(dispatch_webhook_event.calls), 1)
        self.assertTrue(dispatch_webhook_event.last_called_with(
            webhook_targets=[target],
            event=event))

        payload = normalize_webhook_payload.last_call.return_value
        self._check_webhook_payload(payload)
        self.assertEqual(payload['event'], event)

        request = OpenerDirector.open.last_call.args[0]
        self.assertEqual(request.get_header(b'X-reviewboard-event'),
                         event.encode('utf-8'))

        return payload

    def _check_webhook_payload(self, payload):
        """Check the contents of a WebHook payload.

        This will check the payload to ensure that only certain data types are
        present and that unwanted types (like model instances) are not found.

        Args:
            payload (object):
                The payload or subset of a payload to validate.
        """
        if payload is not None:
            self.assertIn(type(payload),
                          (bool, datetime, dict, int, float, long, list,
                           six.text_type, OrderedDict))

        if type(payload) in (dict, OrderedDict):
            for key, value in six.iteritems(payload):
                if key is not None:
                    self.assertIn(type(key), (bool, int, float, long,
                                              six.text_type))

                self._check_webhook_payload(value)
        elif type(payload) is list:
            for i in payload:
                self._check_webhook_payload(i)
