"""Unit tests for the ReviewBoardGateway hosting service."""

from __future__ import unicode_literals

import hashlib
import hmac
import logging

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils.safestring import SafeText
from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.core import Branch, Commit
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.errors import RepositoryNotFoundError
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class ReviewBoardGatewayTestCase(HostingServiceTestCase):
    """Base test case for the ReviewBoardGateway hosting service."""

    service_name = 'rbgateway'

    default_use_hosting_url = True
    default_account_data = {
        'private_token': encrypt_password('abc123'),
    }

    default_http_credentials = {
        'headers': {
            'PRIVATE-TOKEN': 'abc123',
        },
    }

    default_repository_extra_data = {
        'rbgateway_repo_name': 'myrepo',
    }


class ReviewBoardGatwayClientTests(ReviewBoardGatewayTestCase):
    """Unit tests for ReviewBoardGatewayClient."""

    def test_request_includes_private_token(self):
        """Testing ReviewBoardGatewayClient API requests include PRIVATE-TOKEN
        header
        """
        with self.setup_http_test(payload=b'{}',
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(rbgateway_repo_name='myrepo')

            request = ctx.client.open_http_request.calls[0].args[0]
            self.assertEqual(request.get_header('PRIVATE-TOKEN'),
                             'abc123')


class ReviewBoardGatewayTests(ReviewBoardGatewayTestCase):
    """Unit tests for the ReviewBoardGateway hosting service."""

    def test_service_support(self):
        """Testing ReviewBoardGateway service support capabilities"""
        self.assertTrue(self.service_class.supports_repositories)
        self.assertTrue(self.service_class.supports_post_commit)
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_ssh_key_association)

    def test_repo_field_values(self):
        """Testing ReviewBoardGateway.get_repository_fields for Git"""
        self.assertEqual(
            self.get_repository_fields(
                'Git',
                fields={
                    'hosting_url': 'https://example.com',
                    'rbgateway_repo_name': 'myrepo',
                }
            ),
            {
                'path': 'https://example.com/repos/myrepo/path',
            })

    def test_get_repository_hook_instructions(self):
        """Testing ReviewBoardGateway.get_repository_hook_instructions"""
        account = self.create_hosting_account()
        repository = self.create_repository(hosting_account=account)
        hooks_uuid = repository.get_or_create_hooks_uuid()

        request = RequestFactory().get(path='/')
        request.user = User.objects.create(username='test-user')

        content = repository.hosting_service.get_repository_hook_instructions(
            request=request,
            repository=repository)

        self.assertIsInstance(content, SafeText)
        self.assertIn(
            ('"url": '
             '"http://example.com/repos/1/rbgateway/hooks/close-submitted/"'),
            content)
        self.assertIn(
            '"secret": "%s",' % hooks_uuid,
            content)
        self.assertIn('Review Board supports closing', content)

    def test_authorize(self):
        """Testing ReviewBoardGateway.authorize"""
        hosting_account = self.create_hosting_account(data={})
        self.assertFalse(hosting_account.is_authorized)

        with self.setup_http_test(payload=b'{"private_token": "abc123"}',
                                  hosting_account=hosting_account,
                                  expected_http_calls=1) as ctx:
            ctx.service.authorize(username='myuser',
                                  password='mypass',
                                  hosting_url='https://example.com')

        self.assertTrue(hosting_account.is_authorized)
        self.assertEqual(
            decrypt_password(hosting_account.data['private_token']),
            'abc123')

        ctx.assertHTTPCall(
            0,
            url='https://example.com/session',
            method='POST',
            body=b'',
            credentials={
                'username': 'myuser',
                'password': 'mypass',
            },
            headers={
                'Content-Length': '0',
            })

    def test_check_repository(self):
        """Testing ReviewBoardGateway.check_repository"""
        paths = {
            '/repos/myrepo/path': {
                'webhooks': [],
            },
        }

        with self.setup_http_test(self.make_handler_for_paths(paths),
                                  expected_http_calls=1) as ctx:
            ctx.service.check_repository(rbgateway_repo_name='myrepo')

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/myrepo/path',
            headers=None)

    def test_check_repository_with_invalid_repo(self):
        """Testing ReviewBoardGateway.check_repository with invalid
        repository
        """
        with self.setup_http_test(status_code=404,
                                  expected_http_calls=1) as ctx:
            with self.assertRaises(RepositoryNotFoundError):
                ctx.service.check_repository(rbgateway_repo_name='invalid')

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/invalid/path',
            headers=None)

    def test_get_branches_git(self):
        """Testing ReviewBoardGateway.get_branches for a Git repository"""
        payload = self.dump_json([
            {
                'name': 'master',
                'id': 'c272edcac05b00e15440d6274723b639e3acbd7c',
            },
            {
                'name': 'im_a_branch',
                'id': '83904e6acb60e7ec0dcaae6c09a579ab44d0cf38',
            }
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/myrepo/branches',
            headers=None)

        self.assertEqual(
            branches,
            [
                Branch(id='master',
                       commit='c272edcac05b00e15440d6274723b639e3acbd7c',
                       default=True),
                Branch(id='im_a_branch',
                       commit='83904e6acb60e7ec0dcaae6c09a579ab44d0cf38'),
            ])

    def test_get_branches_hg(self):
        """Testing ReviewBoardGateway.get_branches for an Hg repository"""
        payload = self.dump_json([
            {
                'name': 'default',
                'id': '9b1153b8a8eb2f7b1661ed7695c432f5a2b25729',
            },
            {
                'name': 'some-bookmark',
                'id': '0731875ed7a14bdd53503b27b30a08a0452068cf',
            },
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository(tool_name='Mercurial')
            branches = ctx.service.get_branches(repository)

        ctx.assertHTTPCall(
            0,
            url='https://example.com/repos/myrepo/branches',
            headers=None)

        self.assertEqual(
            branches,
            [
                Branch(id='default',
                       commit='9b1153b8a8eb2f7b1661ed7695c432f5a2b25729',
                       default=True),
                Branch(id='some-bookmark',
                       commit='0731875ed7a14bdd53503b27b30a08a0452068cf'),
            ])


    def test_get_commits(self):
        """Testing ReviewBoardGateway.get_commits"""
        payload = self.dump_json([
            {
                'author': 'Author 1',
                'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
                'date': '2015-02-13 22:34:01 -0700',
                'message': 'Message 1',
                'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            },
            {
                'author': 'Author 2',
                'id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
                'date': '2015-02-13 22:32:42 -0700',
                'message': 'Message 2',
                'parent_id': 'fa1330719893098ae397356e8125c2aa45b49221',
            },
            {
                'author': 'Author 3',
                'id': 'fa1330719893098ae397356e8125c2aa45b49221',
                'date': '2015-02-12 16:01:48 -0700',
                'message': 'Message 3',
                'parent_id': '',
            }
        ])

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            commits = ctx.service.get_commits(
                repository=repository,
                branch='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/repos/myrepo/branches/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6/commits'),
            headers=None)

        self.assertEqual(
            commits,
            [
                Commit(author_name='Author 1',
                       date='2015-02-13 22:34:01 -0700',
                       id='bfdde95432b3af879af969bd2377dc3e55ee46e6',
                       message='Message 1',
                       parent='304c53c163aedfd0c0e0933776f09c24b87f5944'),
                Commit(author_name='Author 2',
                       date='2015-02-13 22:32:42 -0700',
                       id='304c53c163aedfd0c0e0933776f09c24b87f5944',
                       message='Message 2',
                       parent='fa1330719893098ae397356e8125c2aa45b49221'),
                Commit(author_name='Author 3',
                       date='2015-02-12 16:01:48 -0700',
                       id='fa1330719893098ae397356e8125c2aa45b49221',
                       message='Message 3',
                       parent=''),
            ])

        for commit in commits:
            self.assertIsNone(commit.diff)

    def test_get_change(self):
        """Testing ReviewBoardGateway.get_change"""
        diff = (
            'diff --git a/test b/test\n'
            'index 9daeafb9864cf43055ae93beb0afd6c7d144bfa4..'
            'dced80a85fe1e8f13dd5ea19923e5d2e8680020d 100644\n'
            '--- a/test\n'
            '+++ b/test\n'
            '@@ -1 +1,3 @@\n'
            ' test\n'
            '+\n'
            '+test\n'
        )

        payload = self.dump_json({
            'author': 'Some Author',
            'id': 'bfdde95432b3af879af969bd2377dc3e55ee46e6',
            'date': '2015-02-13 22:34:01 -0700',
            'message': 'My Message',
            'parent_id': '304c53c163aedfd0c0e0933776f09c24b87f5944',
            'diff': diff,
        })

        with self.setup_http_test(payload=payload,
                                  expected_http_calls=1) as ctx:
            repository = ctx.create_repository()
            change = ctx.service.get_change(
                repository=repository,
                revision='bfdde95432b3af879af969bd2377dc3e55ee46e6')

        ctx.assertHTTPCall(
            0,
            url=('https://example.com/repos/myrepo/commits/'
                 'bfdde95432b3af879af969bd2377dc3e55ee46e6'),
            headers=None)

        self.assertEqual(
            change,
            Commit(author_name='Some Author',
                   date='2015-02-13 22:34:01 -0700',
                   id='bfdde95432b3af879af969bd2377dc3e55ee46e6',
                   message='My Message',
                   parent='304c53c163aedfd0c0e0933776f09c24b87f5944'))
        self.assertEqual(change.diff, diff.encode('utf-8'))


class CloseSubmittedHookTests(ReviewBoardGatewayTestCase):
    """Unit tests for ReviewBoardGateway's close-submitted hook."""

    fixtures = ['test_users', 'test_scmtools']

    def test_close_submitted_hook_git(self):
        """Testing the ReviewBoardGateway close-submitted hook with a Git
        repository
        """
        self._test_post_commit_hook(tool_name='Git')

    def test_close_submiteed_hook_git_unpublished(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        unpublished review request in a Git repository
        """
        self._test_post_commit_hook(tool_name='Git', publish=False)

    @add_fixtures(['test_site'])
    def test_close_submiteed_hook_git_local_site_unpublished(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        unpublished review request in a Git repository on a Local Site
        """
        self._test_post_commit_hook(
            tool_name='Git',
            local_site=LocalSite.objects.get(name=self.local_site_name),
            publish=False)

    def test_close_submitted_hook_git_tag_target(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Git repository and a tag target
        """
        self._test_post_commit_hook(
            tool_name='Git',
            expected_close_msg='Pushed to release-1.0.7 (bbbbbbb)',
            target_tags=['release-1.0.7', 'some-tag'])

    def test_close_submitted_hook_git_no_target(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Git repository and no target information
        """
        self._test_post_commit_hook(
            tool_name='Git',
            expected_close_msg='Pushed to bbbbbbb',
            target_branch=None)

    def test_close_submitted_hook_hg(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Mercurial repository
        """
        self._test_post_commit_hook(tool_name='Mercurial')

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_hg_local_site(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Mercurial repository on a Local Site
        """
        self._test_post_commit_hook(
            tool_name='Mercurial',
            local_site=LocalSite.objects.get(name=self.local_site_name))

    def test_close_submitted_hook_hg_unpublished(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        unpublished review request in a Mercurial repository
        """
        self._test_post_commit_hook(tool_name='Mercurial', publish=False)

    @add_fixtures(['test_site'])
    def test_close_submitted_hook_hg_local_site_unpublished(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        unpublished review request in a Mercurial repository on a Local Site
        """
        self._test_post_commit_hook(
            tool_name='Mercurial',
            local_site=LocalSite.objects.get(name=self.local_site_name),
            publish=False)

    def test_close_submitted_hook_hg_bookmark_target(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Mercurial repository and a bookmark target
        """
        self._test_post_commit_hook(
            tool_name='Mercurial',
            expected_close_msg='Pushed to dev-work (bbbbbbb)',
            target_bookmarks=['dev-work'])

    def test_close_submitted_hook_hg_tag_target(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Mercurial repository and a tag target
        """
        self._test_post_commit_hook(
            tool_name='Mercurial',
            expected_close_msg='Pushed to @ (bbbbbbb)',
            target_branch='default',
            target_tags=['@', 'tip'])

    def test_close_submitted_hook_hg_no_target(self):
        """Testing the ReviewBoardGateway close-submitted hook with an
        Mercurial repository and no target information
        """
        self._test_post_commit_hook(
            tool_name='Mercurial',
            expected_close_msg='Pushed to bbbbbbb',
            target_branch=None)

    def test_close_submitted_hook_invalid_signature(self):
        """Testing the ReviewBoardGateway close-submitted hook with an invalid
        signature
        """
        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        payload = self.dump_json({
            'event': 'push',
            'commits': [],
        })
        signature = hmac.new(
            b'this is not the secret key',
            payload,
            hashlib.sha1).hexdigest()

        rsp = self.client.post(
            url,
            payload,
            content_type='application/x-www-form-urlencoded',
            HTTP_X_RBG_SIGNATURE=signature,
            HTTP_X_RBG_EVENT='push')

        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.content, b'Bad signature.')

    def test_close_submitted_hook_malformed_payload(self):
        """Testing the ReviewBoardGateway close-submitted hook with a malformed
        signature
        """
        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        payload = 'event=push&commit_id=bbbbbbb&branch=master'
        signature = hmac.new(
            repository.get_or_create_hooks_uuid().encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha1).hexdigest()

        rsp = self.client.post(
            url,
            payload,
            content_type='application/x-www-form-urlencoded',
            HTTP_X_RBG_SIGNATURE=signature,
            HTTP_X_RBG_EVENT='push')

        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.content, b'Invalid payload format.')

    def test_close_submitted_hook_incomplete_payload(self):
        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        payload = self.dump_json({
            'event': 'push',
        })
        signature = hmac.new(
            repository.get_or_create_hooks_uuid().encode('utf-8'),
            payload,
            hashlib.sha1).hexdigest()

        rsp = self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_RBG_SIGNATURE=signature,
            HTTP_X_RBG_EVENT='push')

        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.content, b'Invalid payload; expected "commits".')

    def test_close_submitted_hook_invalid_event(self):
        """Testing the ReviewBoardGateway close-submitted hook endpoint with an
        invalid event
        """
        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        payload = self.dump_json({
            'event': 'unknown-event',
            'repository': 'foo',
        })
        signature = hmac.new(
            repository.get_or_create_hooks_uuid().encode('utf-8'),
            payload,
            hashlib.sha1).hexdigest()

        rsp = self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_RBG_SIGNATURE=signature,
            HTTP_X_RBG_EVENT='unknown-event')

        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(rsp.content,
                         b'Only "ping" and "push" events are supported.')

    def test_close_submitted_hook_with_invalid_review_request(self):
        """Testing the ReviewBoardGateway close-submitted hook endpoint with an
        invalid review request
        """
        self.spy_on(logging.error)

        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url='/r/9999/',
            repository_name=repository.name,
            secret=repository.get_or_create_hooks_uuid())
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)
        self.assertEqual(review_request.changedescs.count(), 0)

        self.assertTrue(logging.error.called_with(
            'close_all_review_requests: Review request #%s does not exist.',
            9999))

    def test_ping_event(self):
        """Testing the ReviewBoardGateway close submitted hook endpoint with
        event=ping
        """
        account = self.create_hosting_account()
        repository = self.create_repository(tool_name='Git',
                                            hosting_account=account)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=None,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        payload = self.dump_json({
            'event': 'ping',
            'repository': 'foo',
        })
        signature = hmac.new(
            repository.get_or_create_hooks_uuid().encode('utf-8'),
            payload,
            hashlib.sha1).hexdigest()

        rsp = self.client.post(
            url,
            payload,
            content_type='application/json',
            HTTP_X_RBG_SIGNATURE=signature,
            HTTP_X_RBG_EVENT='ping')

        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.content, b'')

    def _test_post_commit_hook(self, tool_name, local_site=None, publish=True,
                               expected_close_msg='Pushed to master (bbbbbbb)',
                               **kwargs):
        """Testing posting to a commit hook.

        This will simulate pushing a commit and posting the resulting webhook
        payload from RB Gateway to the handler for the hook.

        Args:
            tool_name (unicode):
                The name of the SCM tool to use.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site owning the review request.

            publish (bool):
                Whether or not to use a published review request.
        """
        account = self.create_hosting_account(local_site=local_site)
        repository = self.create_repository(tool_name=tool_name,
                                            hosting_account=account,
                                            local_site=local_site)

        review_request = self.create_review_request(repository=repository,
                                                    local_site=local_site,
                                                    publish=publish)

        self.assertEqual(review_request.status, review_request.PENDING_REVIEW)

        url = local_site_reverse(
            'rbgateway-hooks-close-submitted',
            local_site=local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': 'rbgateway',
            })

        response = self._post_commit_hook_payload(
            post_url=url,
            review_request_url=review_request.get_absolute_url(),
            repository_name=repository.name,
            secret=repository.get_or_create_hooks_uuid(),
            **kwargs)
        self.assertEqual(response.status_code, 200)

        review_request = ReviewRequest.objects.get(pk=review_request.pk)
        self.assertTrue(review_request.public)
        self.assertEqual(review_request.status, review_request.SUBMITTED)
        self.assertEqual(review_request.changedescs.count(), 1)

        changedesc = review_request.changedescs.get()
        self.assertEqual(changedesc.text, expected_close_msg)

    def _post_commit_hook_payload(self, post_url, repository_name,
                                  review_request_url, secret,
                                  event='push', target_branch='master',
                                  target_bookmarks=None, target_tags=None):
        """Post a payload for a hook for testing.

        Args:
            post_url (unicode):
                The URL to post to.

            repository_name (unicode):
                The name of the repository.

            review_request_url (unicode):
                The URL of the review request being represented in the
                payload.

            secret (unicode):
                The HMAC secret for the message.

            event (unicode, optional):
                The webhook event.

            target_branch (unicode, optional):
                The target branch to include in the payload.

            target_bookmarks (unicode, optional):
                The target Mercurial bookmarks to include in the payload.

            target_tags (unicode, optional):
                The target tags to include in the payload.

        Results:
            django.core.handlers.wsgi.WSGIRequest:
            The post request.
        """
        target = {}

        if target_branch is not None:
            target['branch'] = target_branch

        if target_bookmarks is not None:
            target['bookmarks'] = target_bookmarks

        if target_tags is not None:
            target['tags'] = target_tags

        payload = self.dump_json({
            'event': event,
            'repository': repository_name,
            'commits': [
                {
                    'id': 'b' * 40,
                    'message': (
                        'Commit message.\n\n'
                        'Reviewed at http://example.com%s'
                    ) % review_request_url,
                    'target': target,
                },
            ],
        })

        signature = hmac.new(secret.encode('utf-8'),
                             payload,
                             hashlib.sha1).hexdigest()

        return self.client.post(
            post_url,
            payload,
            content_type='application/json',
            HTTP_X_RBG_EVENT=event,
            HTTP_X_RBG_SIGNATURE=signature)
