from djblets.features.testing import override_feature_check
from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import root_item_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_root_url


class ResourceTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Testing the RootResource APIs."""
    fixtures = ['test_users']
    sample_api_url = '/'
    resource = resources.root
    test_http_methods = ('DELETE', 'PUT', 'POST')

    def setup_http_not_allowed_item_test(self, user):
        return get_root_url()

    def setup_http_not_allowed_list_test(self, user):
        return get_root_url()

    def test_get(self):
        """Testing the GET / API"""
        rsp = self.api_get(get_root_url(),
                           expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('uri_templates', rsp)
        self.assertIn('repository', rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/api/repositories/{repository_id}/')

        self._check_common_root_fields(rsp)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site(self):
        """Testing the GET / API with local sites"""
        self._login_user(local_site=True)
        rsp = self.api_get(get_root_url('local-site-1'),
                           expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('uri_templates', rsp)
        self.assertIn('repository', rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-1/api/'
                         'repositories/{repository_id}/')

        self._check_common_root_fields(rsp)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET / API without access to local site"""
        self.api_get(get_root_url('local-site-1'), expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_with_site_and_cache(self):
        """Testing the GET / API with multiple local sites"""
        # djblets had a bug where the uri_templates were cached without any
        # consideration of the local site (or, more generally, the base uri).
        # In this case, fetching /s/<local_site>/api/ might return uri
        # templates for someone else's site. This was breaking rbt post.
        self.test_get_with_site()

        rsp = self.api_get(get_root_url('local-site-2'),
                           expected_mimetype=root_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('uri_templates', rsp)
        self.assertIn('repository', rsp['uri_templates'])
        self.assertEqual(rsp['uri_templates']['repository'],
                         'http://testserver/s/local-site-2/api/'
                         'repositories/{repository_id}/')

    def test_get_capability_dvcs_enabled(self):
        """Testing the GET / API for capabilities with the DVCS feature enabled
        """
        with override_feature_check(dvcs_feature.feature_id, True):
            rsp = self.api_get(get_root_url(),
                               expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn('review_requests', caps)

        review_request_caps = caps['review_requests']
        self.assertIn('supports_history', review_request_caps)
        self.assertTrue(review_request_caps['supports_history'])

    def test_get_capability_dvcs_disabled(self):
        """Testing the GET / API for capabilities with the DVCS feature
        disabled
        """
        with override_feature_check(dvcs_feature.feature_id, False):
            self.assertFalse(dvcs_feature.is_enabled())
            rsp = self.api_get(get_root_url(),
                               expected_mimetype=root_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('capabilities', rsp)

        caps = rsp['capabilities']
        self.assertIn('review_requests', caps)
        self.assertNotIn('supports_history', caps['review_requests'])

    def test_get_uri_templates(self):
        """Testing that the RootResource has a URI templates dictionary that
        matches our expectations
        """
        expected_uri_templates = {
            'all_file_attachment_comment':
                'http://testserver/api/file-attachment-comments/{comment_id}/',
            'all_file_attachment_comments':
                'http://testserver/api/file-attachment-comments/',
            'all_general_comment':
                'http://testserver/api/general-comments/{comment_id}/',
            'all_general_comments': 'http://testserver/api/general-comments/',
            'all_reviews': 'http://testserver/api/reviews/',
            'all_reviews_file_attachment_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'file-attachments/{file_attachment_id}/'
                'file-attachment-comments/',
            'api_token':
                'http://testserver/api/users/{username}/api-tokens/'
                '{api_token_id}/',
            'api_tokens': 'http://testserver/api/users/{username}/api-tokens/',
            'archived_review_request':
                'http://testserver/api/users/{username}/'
                'archived-review-requests/{review_request_id}/',
            'archived_review_requests':
                'http://testserver/api/users/{username}/'
                'archived-review-requests/',
            'branches':
                'http://testserver/api/repositories/{repository_id}/branches/',
            'change':
                'http://testserver/api/review-requests/{review_request_id}/'
                'changes/{change_id}/',
            'changes':
                'http://testserver/api/review-requests/{review_request_id}/'
                'changes/',
            'commit':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/commits/{commit_id}/',
            'commit_validation': 'http://testserver/api/validation/commits/',
            'commits':
                'http://testserver/api/repositories/{repository_id}/commits/',
            'default_reviewer':
                'http://testserver/api/default-reviewers/'
                '{default_reviewer_id}/',
            'default_reviewers': 'http://testserver/api/default-reviewers/',
            'diff':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/',
            'diff_commits':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/commits/',
            'diff_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/diff-comments/'
                '{comment_id}/',
            'diff_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/diff-comments/',
            'diff_context':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diff-context/',
            'diff_file_attachment':
                'http://testserver/api/repositories/{repository_id}/'
                'diff-file-attachments/{file_attachment_id}/',
            'diff_file_attachments':
                'http://testserver/api/repositories/{repository_id}/'
                'diff-file-attachments/',
            'diff_validation': 'http://testserver/api/validation/diffs/',
            'diffs':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/',
            'draft':
                'http://testserver/api/review-requests/{review_request_id}/'
                'draft/',
            'extension': 'http://testserver/api/extensions/{extension_name}/',
            'extensions': 'http://testserver/api/extensions/',
            'file':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/files/{filediff_id}/',
            'file_attachment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'file-attachments/{file_attachment_id}/',
            'file_attachment_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/file-attachment-comments/{comment_id}/',
            'file_attachment_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/file-attachment-comments/',
            'file_attachments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'file-attachments/',
            'file_diff_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/files/{filediff_id}/diff-comments/',
            'files':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/files/',
            'general_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/general-comments/{comment_id}/',
            'general_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/general-comments/',
            'group': 'http://testserver/api/groups/{group_name}/',
            'groups': 'http://testserver/api/groups/',
            'hosting_service':
                'http://testserver/api/hosting-services/{hosting_service_id}/',
            'hosting_service_account':
                'http://testserver/api/hosting-service-accounts/{account_id}/',
            'hosting_service_accounts':
                'http://testserver/api/hosting-service-accounts/',
            'hosting_services': 'http://testserver/api/hosting-services/',
            'info': 'http://testserver/api/info/',
            'last_update':
                'http://testserver/api/review-requests/{review_request_id}/'
                'last-update/',
            'muted_review_request':
                'http://testserver/api/users/{username}/muted-review-requests/'
                '{review_request_id}/',
            'muted_review_requests':
                'http://testserver/api/users/{username}/'
                'muted-review-requests/',
            'oauth_app': 'http://testserver/api/oauth-apps/{app_id}/',
            'oauth_apps': 'http://testserver/api/oauth-apps/',
            'oauth_token':
                'http://testserver/api/oauth-tokens/{oauth_token_id}/',
            'oauth_tokens': 'http://testserver/api/oauth-tokens/',
            'original_file':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/files/{filediff_id}/original-file/',
            'patched_file':
                'http://testserver/api/review-requests/{review_request_id}/'
                'diffs/{diff_revision}/files/{filediff_id}/patched-file/',
            'remote_repositories':
                'http://testserver/api/hosting-service-accounts/{account_id}/'
                'remote-repositories/',
            'remote_repository':
                'http://testserver/api/hosting-service-accounts/{account_id}/'
                'remote-repositories/{repository_id}/',
            'replies':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/',
            'reply':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/',
            'reply_draft':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/draft/',
            'repositories': 'http://testserver/api/repositories/',
            'repository':
                'http://testserver/api/repositories/{repository_id}/',
            'repository_info':
                'http://testserver/api/repositories/{repository_id}/info/',
            'repository_group':
                'http://testserver/api/repositories/{repository_id}/groups/'
                '{group_name}/',
            'repository_groups':
                'http://testserver/api/repositories/{repository_id}/groups/',
            'repository_user':
                'http://testserver/api/repositories/{repository_id}/users/'
                '{username}/',
            'repository_users':
                'http://testserver/api/repositories/{repository_id}/users/',
            'review':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/',
            'review_diff_comment':
                'http://testserver/api/review-diff-comments/{comment_id}/',
            'review_diff_comments':
                'http://testserver/api/review-diff-comments/',
            'review_draft':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/draft/',
            'review_group_user':
                'http://testserver/api/groups/{group_name}/users/{username}/',
            'review_group_users':
                'http://testserver/api/groups/{group_name}/users/',
            'review_reply_file_attachment_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/'
                'file-attachment-comments/{comment_id}/',
            'review_reply_file_attachment_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/'
                'file-attachment-comments/',
            'review_reply_general_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/general-comments/'
                '{comment_id}/',
            'review_reply_general_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/general-comments/',
            'review_reply_screenshot_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/screenshot-comments/'
                '{comment_id}/',
            'review_reply_screenshot_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/replies/{reply_id}/screenshot-comments/',
            'review_request':
                'http://testserver/api/review-requests/{review_request_id}/',
            'review_requests': 'http://testserver/api/review-requests/',
            'reviews':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/',
            'root': 'http://testserver/api/',
            'screenshot':
                'http://testserver/api/review-requests/{review_request_id}/'
                'screenshots/{screenshot_id}/',
            'screenshot_comment':
                'http://testserver/api/review-requests/{review_request_id}/'
                'reviews/{review_id}/screenshot-comments/{comment_id}/',
            'screenshot_comments':
                'http://testserver/api/review-requests/{review_request_id}/'
                'screenshots/{screenshot_id}/screenshot-comments/',
            'screenshots':
                'http://testserver/api/review-requests/{review_request_id}/'
                'screenshots/',
            'search': 'http://testserver/api/search/{username}/',
            'session': 'http://testserver/api/session/',
            'status_update':
                'http://testserver/api/review-requests/{review_request_id}/'
                'status-updates/{status_update_id}/',
            'status_updates':
                'http://testserver/api/review-requests/{review_request_id}/'
                'status-updates/',
            'user': 'http://testserver/api/users/{username}/',
            'user_file_attachment':
                'http://testserver/api/users/{username}/user-file-attachments/'
                '{file_attachment_id}/',
            'user_file_attachments':
                'http://testserver/api/users/{username}/'
                'user-file-attachments/',
            'users': 'http://testserver/api/users/',
            'validation': 'http://testserver/api/validation/',
            'watched': 'http://testserver/api/users/{username}/watched/',
            'watched_review_group':
                'http://testserver/api/users/{username}/watched/'
                'review-groups/{watched_obj_id}/',
            'watched_review_groups':
                'http://testserver/api/users/{username}/watched/'
                'review-groups/',
            'watched_review_request':
                'http://testserver/api/users/{username}/watched/'
                'review-requests/{watched_obj_id}/',
            'watched_review_requests':
                'http://testserver/api/users/{username}/watched/'
                'review-requests/',
            'webhook': 'http://testserver/api/webhooks/{webhook_id}/',
            'webhooks': 'http://testserver/api/webhooks/'
        }

        rsp = self.api_get(get_root_url(),
                           expected_mimetype=root_item_mimetype)
        current_uri_templates = rsp['uri_templates']

        self.assertDictEqual(expected_uri_templates,
                             current_uri_templates)

    def _check_common_root_fields(self, item_rsp):
        self.assertIn('product', item_rsp)
        self.assertIn('site', item_rsp)
        self.assertIn('capabilities', item_rsp)

        caps = item_rsp['capabilities']
        self.assertIn('diffs', caps)

        diffs_caps = caps['diffs']
        self.assertTrue(diffs_caps['moved_files'])
        self.assertTrue(diffs_caps['base_commit_ids'])

        diff_validation_caps = diffs_caps['validation']
        self.assertTrue(diff_validation_caps['base_commit_ids'])

        review_request_caps = caps['review_requests']
        self.assertTrue(review_request_caps['commit_ids'])

        text_caps = caps['text']
        self.assertTrue(text_caps['markdown'])
