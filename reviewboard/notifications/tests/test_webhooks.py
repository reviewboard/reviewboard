from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.template import TemplateSyntaxError
from django.utils import six
from django.utils.six.moves.urllib.request import OpenerDirector
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.notifications.models import WebHookTarget
from reviewboard.notifications.webhooks import (FakeHTTPRequest,
                                                dispatch_webhook_event,
                                                render_custom_content)
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class WebHookPayloadTests(SpyAgency, TestCase):
    """Tests for payload rendering."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    @add_fixtures(['test_scmtools', 'test_users'])
    def test_diffset_rendered(self):
        """Testing JSON-serializability of DiffSets in WebHook payloads"""
        self.spy_on(OpenerDirector.open, call_original=False)
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
        """Tests render_custom_content with a valid template"""
        s = render_custom_content(
            '{% if mybool %}{{s1}}{% else %}{{s2}}{% endif %}',
            {
                'mybool': True,
                's1': 'Hi!',
                's2': 'Bye!',
            })

        self.assertEqual(s, 'Hi!')

    def test_with_blocked_block_tag(self):
        """Tests render_custom_content with blocked {% block %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'block'"):
            render_custom_content('{% block foo %}{% endblock %})')

    def test_with_blocked_debug_tag(self):
        """Tests render_custom_content with blocked {% debug %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'debug'"):
            render_custom_content('{% debug %}')

    def test_with_blocked_extends_tag(self):
        """Tests render_custom_content with blocked {% extends %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'extends'"):
            render_custom_content('{% extends "base.html" %}')

    def test_with_blocked_include_tag(self):
        """Tests render_custom_content with blocked {% include %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'include'"):
            render_custom_content('{% include "base.html" %}')

    def test_with_blocked_load_tag(self):
        """Tests render_custom_content with blocked {% load %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'load'"):
            render_custom_content('{% load i18n %}')

    def test_with_blocked_ssi_tag(self):
        """Tests render_custom_content with blocked {% ssi %}"""
        with self.assertRaisesMessage(TemplateSyntaxError,
                                      "Invalid block tag: 'ssi'"):
            render_custom_content('{% ssi "foo.html" %}')

    def test_with_unknown_vars(self):
        """Tests render_custom_content with unknown variables"""
        s = render_custom_content('{{settings.DEBUG}};{{settings.DATABASES}}')
        self.assertEqual(s, ';')


class WebHookDispatchTests(SpyAgency, TestCase):
    """Unit tests for dispatching webhooks."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    def test_dispatch_custom_payload(self):
        """Test dispatch_webhook_event with custom payload"""
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
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            ('{\n'
             '  "item1": true,\n'
             '  "item2": true,\n'
             '  "item3": true\n'
             '}'))

    def test_dispatch_non_ascii_custom_payload(self):
        """Testing dispatch_webhook_event with non-ASCII custom payload"""
        non_ascii_content = '{"sign": "{{sign|escapejs}}"}'

        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=non_ascii_content)

        self._test_dispatch(
            handler,
            'my-event',
            {'sign': '\u00A4'},
            'application/json',
            '{"sign": "\u00A4"}'.encode('utf-8')
        )

    def test_dispatch_form_data(self):
        """Test dispatch_webhook_event with Form Data payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_FORM_DATA)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/x-www-form-urlencoded',
            'payload=%7B%22items%22%3A+%5B1%2C+2%2C+3%5D%7D')

    def test_dispatch_non_ascii_form_data(self):
        """Testing dispatch_webhook_event with non-ASCII Form Data payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_FORM_DATA)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'sign': '\u00A4',
            },
            'application/x-www-form-urlencoded',
            'payload=%7B%22sign%22%3A+%22%5Cu00a4%22%7D')

    def test_dispatch_json(self):
        """Test dispatch_webhook_event with JSON payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            '{"items": [1, 2, 3]}')

    def test_dispatch_non_ascii_json(self):
        """Testing dispatch_webhook_event with non-ASCII JSON payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'sign': '\u00A4',
            },
            'application/json',
            '{"sign": "\\u00a4"}')

    def test_dispatch_xml(self):
        """Test dispatch_webhook_event with XML payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_XML)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/xml',
            ('<?xml version="1.0" encoding="utf-8"?>\n'
             '<rsp>\n'
             ' <items>\n'
             '  <array>\n'
             '   <item>1</item>\n'
             '   <item>2</item>\n'
             '   <item>3</item>\n'
             '  </array>\n'
             ' </items>\n'
             '</rsp>'))

    def test_dispatch_non_ascii_xml(self):
        """Testing dispatch_webhook_event with non-ASCII XML payload"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_XML)

        self._test_dispatch(
            handler,
            'my-event',
            {
                'sign': '\u00A4',
            },
            'application/xml',
            ('<?xml version="1.0" encoding="utf-8"?>\n'
             '<rsp>\n'
             ' <sign>\u00A4</sign>\n'
             '</rsp>').encode('utf-8'))

    def test_dispatch_with_secret(self):
        """Test dispatch_webhook_event with HMAC secret"""
        handler = WebHookTarget(events='my-event',
                                url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                secret='foobar123')

        self._test_dispatch(
            handler,
            'my-event',
            {
                'items': [1, 2, 3],
            },
            'application/json',
            '{"items": [1, 2, 3]}',
            'sha1=46f8529ef47da2291eeb475f0d0c0a6f58f88f8b')

    def test_dispatch_invalid_template(self):
        """Testing dispatch_webhook_event with an invalid template"""
        handler = WebHookTarget(events='my-event', url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON,
                                use_custom_content=True,
                                custom_content=r'{% invalid_block_tag %}')

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    call_fake=lambda *args, **kwargs: None)

        dispatch_webhook_event(FakeHTTPRequest(None), [handler], 'my-event',
                               None)

        self.assertFalse(OpenerDirector.open.spy.called)
        self.assertTrue(logging.exception.spy.called)
        self.assertIsInstance(logging.exception.spy.last_call.args[1],
                              TemplateSyntaxError)

    def test_dispatch_render_error(self):
        """Testing dispatch_webhook_event with an unencodable object"""
        class Unencodable(object):
            pass

        handler = WebHookTarget(events='my-event', url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open,
                    call_fake=lambda *args, **kwargs: None)

        dispatch_webhook_event(FakeHTTPRequest(None), [handler], 'my-event', {
            'unencodable': Unencodable(),
        })

        self.assertFalse(OpenerDirector.open.spy.called)
        self.assertTrue(logging.exception.spy.called)
        self.assertIsInstance(logging.exception.spy.last_call.args[1],
                              TypeError)

    def test_dispatch_cannot_open(self):
        """Testing dispatch_webhook_event with an unresolvable URL"""
        def _urlopen(opener, *args, **kwargs):
            raise IOError('')

        handler = WebHookTarget(events='my-event', url=self.ENDPOINT_URL,
                                encoding=WebHookTarget.ENCODING_JSON)

        self.spy_on(logging.exception)
        self.spy_on(OpenerDirector.open, call_fake=_urlopen)

        dispatch_webhook_event(FakeHTTPRequest(None), [handler, handler],
                               'my-event',
                               None)

        self.assertEqual(len(OpenerDirector.open.spy.calls), 2)
        self.assertTrue(len(logging.exception.spy.calls), 2)
        self.assertIsInstance(logging.exception.spy.calls[0].args[2], IOError)
        self.assertIsInstance(logging.exception.spy.calls[1].args[2], IOError)

    def _test_dispatch(self, handler, event, payload, expected_content_type,
                       expected_data, expected_sig_header=None):
        def _urlopen(opener, request, *args, **kwargs):
            self.assertEqual(request.get_full_url(), self.ENDPOINT_URL)
            self.assertEqual(request.headers['X-reviewboard-event'], event)
            self.assertEqual(request.headers['Content-type'],
                             expected_content_type)
            self.assertEqual(request.data, expected_data)
            self.assertEqual(request.headers['Content-length'],
                             len(expected_data))

            if expected_sig_header:
                self.assertIn('X-hub-signature', request.headers)
                self.assertEqual(request.headers['X-hub-signature'],
                                 expected_sig_header)
            else:
                self.assertNotIn('X-hub-signature', request.headers)

            # Check that all sent data are binary strings.
            self.assertIsInstance(request.get_full_url(), six.binary_type)

            for h in request.headers:
                self.assertIsInstance(h, six.binary_type)
                self.assertNotIsInstance(request.headers[h], six.text_type)

            self.assertIsInstance(request.data, six.binary_type)

        self.spy_on(OpenerDirector.open, call_fake=_urlopen)

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

        self.spy_on(dispatch_webhook_event, call_original=False)

    def test_review_request_closed_submitted(self):
        """Testing webhook dispatch from 'review_request_closed' signal
        with submitted
        """
        target = WebHookTarget.objects.create(events='review_request_closed',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request(publish=True)
        review_request.close(review_request.SUBMITTED)

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_closed')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_closed')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_published')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_published')
        self.assertIn('is_new', payload)
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_reopened')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_reopened')
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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_request_reopened')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_request_reopened')
        self.assertEqual(payload['reopened_by']['id'],
                         review_request.submitter.pk)
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)

    def test_review_published(self):
        """Testing webhook dispatch from 'review_published' signal"""
        target = WebHookTarget.objects.create(events='review_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review = self.create_review(review_request)
        review.publish()

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['review']['id'], review.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)
        self.assertIn('general_comments', payload)

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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'review_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'review_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['review']['id'], review.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)

    def test_reply_published(self):
        """Testing webhook dispatch from 'reply_published' signal"""
        target = WebHookTarget.objects.create(events='reply_published',
                                              url=self.ENDPOINT_URL)

        review_request = self.create_review_request()
        review = self.create_review(review_request)
        reply = self.create_reply(review)
        reply.publish()

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'reply_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'reply_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['reply']['id'], reply.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)
        self.assertIn('general_comments', payload)

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

        spy = dispatch_webhook_event.spy
        self.assertTrue(spy.called)
        self.assertEqual(len(spy.calls), 1)

        last_call = spy.last_call
        self.assertEqual(last_call.args[1], [target])
        self.assertEqual(last_call.args[2], 'reply_published')

        payload = last_call.args[3]
        self.assertEqual(payload['event'], 'reply_published')
        self.assertEqual(payload['review_request']['id'],
                         review_request.display_id)
        self.assertEqual(payload['reply']['id'], reply.pk)
        self.assertIn('diff_comments', payload)
        self.assertIn('screenshot_comments', payload)
        self.assertIn('file_attachment_comments', payload)
