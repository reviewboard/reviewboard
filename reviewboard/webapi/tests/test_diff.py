from __future__ import unicode_literals

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six
from djblets.features.testing import override_feature_check
from djblets.webapi.errors import (INVALID_ATTRIBUTE, INVALID_FORM_DATA,
                                   PERMISSION_DENIED)
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import DefaultReviewer
from reviewboard.webapi.errors import DIFF_TOO_BIG
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_item_mimetype,
                                                diff_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_diff_item_url,
                                           get_diff_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ExtraDataListMixin, ReviewRequestChildListMixin,
                        BaseWebAPITestCase):
    """Testing the DiffResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/diffs/'
    resource = resources.diff

    def setup_review_request_child_test(self, review_request):
        return get_diff_list_url(review_request), diff_list_mimetype

    def compare_item(self, item_rsp, diffset):
        self.assertEqual(item_rsp['id'], diffset.pk)
        self.assertEqual(item_rsp['name'], diffset.name)
        self.assertEqual(item_rsp['revision'], diffset.revision)
        self.assertEqual(item_rsp['basedir'], diffset.basedir)
        self.assertEqual(item_rsp['base_commit_id'], diffset.base_commit_id)
        self.assertEqual(item_rsp['extra_data'], diffset.extra_data)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        if populate_items:
            items = [self.create_diffset(review_request)]
        else:
            items = []

        return (get_diff_list_url(review_request, local_site_name),
                diff_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            submitter=user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        if post_valid_data:
            post_data = {
                'path': diff,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            }
        else:
            post_data = {}

        return (get_diff_list_url(review_request, local_site_name),
                diff_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        self.assertIn('diff', rsp)
        item_rsp = rsp['diff']

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        diffset = DiffSet.objects.get(pk=item_rsp['id'])
        self.assertEqual(diffset, draft.diffset)
        self.compare_item(item_rsp, diffset)

    def test_post_with_missing_data(self):
        """Testing the POST review-requests/<id>/diffs/ API
        with Invalid Form Data
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        rsp = self.api_post(get_diff_list_url(review_request),
                            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('path', rsp['fields'])

        # Now test with a valid path and an invalid basedir.
        # This is necessary because basedir is "optional" as defined by
        # the resource, but may be required by the form that processes the
        # diff.
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_diff_list_url(review_request),
            {'path': diff},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('basedir', rsp['fields'])

    def test_post_too_big(self):
        """Testing the POST review-requests/<id>/diffs/ API
        with diff exceeding max size
        """
        repository = self.create_repository()
        review_request = self.create_review_request(
            repository=repository,
            submitter=self.user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        with self.siteconfig_settings({'diffviewer_max_diff_size': 2},
                                      reload_settings=False):
            rsp = self.api_post(
                get_diff_list_url(review_request),
                {
                    'path': diff,
                    'basedir': "/trunk",
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DIFF_TOO_BIG.code)
        self.assertIn('reason', rsp)
        self.assertIn('max_size', rsp)
        self.assertEqual(rsp['max_size'], 2)

    def test_post_not_owner(self):
        """Testing the POST review-requests/<id>/diffs/ API
        without owner
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_diff_list_url(review_request),
            {
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_no_repository(self):
        """Testing the POST review-requests/<id>/diffs API
        with a ReviewRequest that has no repository
        """
        review_request = self.create_review_request(submitter=self.user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_diff_list_url(review_request),
            {
                'path': diff,
                'basedir': '/trunk',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_ATTRIBUTE.code)

    @webapi_test_template
    def test_post_with_history(self):
        """Testing the POST <URL> API with a diff and a review request created
        with history support
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    create_with_history=True)

        diff = SimpleUploadedFile('diff',
                                  self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                                  content_type='text/x-patch')

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            rsp = self.api_post(
                get_diff_list_url(review_request),
                {
                    'path': diff,
                },
                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertEqual(
            rsp['reason'],
            'This review request was created with support for multiple '
            'commits.\n\n'
            'Create an empty diff revision and upload commits to that '
            'instead.')

    @webapi_test_template
    def test_post_empty_with_history(self):
        """Testing the POST <URL> API creates an empty DiffSet for a review
        request created with history support with the DVCS feature enabled
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    create_with_history=True)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            rsp = self.api_post(get_diff_list_url(review_request), {},
                                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['diff']

        diff = DiffSet.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, diff)
        self.assertEqual(diff.files.count(), 0)
        self.assertEqual(diff.revision, 1)

    @webapi_test_template
    def test_post_empty_dvcs_disabled(self):
        """Testing the POST <URL> API without a diff with the DVCS feature
        disabled
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    create_with_history=False)

        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            rsp = self.api_post(get_diff_list_url(review_request), {},
                                expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertEqual(rsp['fields'], {
            'path': ['This field is required.'],
        })

    @webapi_test_template
    def test_post_adds_default_reviewers(self):
        """Testing the POST <URL> API adds default reviewers"""
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True)

        # Create the state needed for the default reviewer.
        group = self.create_review_group(name='group1')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1',
            file_regex='.')
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(review_request.repository)

        # Post the diff.
        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_diff_list_url(review_request),
            {'path': diff},
            expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft()
        self.assertEqual(list(draft.target_groups.all()), [group])

    @webapi_test_template
    def test_post_adds_default_reviewers_first_time_only(self):
        """Testing the POST <URL> API doesn't add default reviewers a second
        time
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True)

        # Create the initial diffset. This should prevent a default
        # reviewer from being applied, since we're not publishing the first
        # diff on a review request.
        self.create_diffset(review_request=review_request)

        # Create the state needed for the default reviewer.
        group = self.create_review_group(name='group1')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1',
            file_regex='.')
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(review_request.repository)

        # Post the diff.
        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_diff_list_url(review_request),
            {'path': diff},
            expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft()
        self.assertEqual(list(draft.target_groups.all()), [])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, ReviewRequestChildItemMixin,
                        BaseWebAPITestCase):
    """Testing the DiffResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/diffs/<revision>/'
    resource = resources.diff

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository:
            review_request.repository = self.create_repository()
            review_request.save()

        diffset = self.create_diffset(review_request)

        return (get_diff_item_url(review_request, diffset.revision),
                diff_item_mimetype)

    def setup_http_not_allowed_item_test(self, user):
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        return get_diff_item_url(review_request, 1)

    def compare_item(self, item_rsp, diffset):
        self.assertEqual(item_rsp['id'], diffset.pk)
        self.assertEqual(item_rsp['name'], diffset.name)
        self.assertEqual(item_rsp['revision'], diffset.revision)
        self.assertEqual(item_rsp['basedir'], diffset.basedir)
        self.assertEqual(item_rsp['base_commit_id'], diffset.base_commit_id)
        self.assertEqual(item_rsp['extra_data'], diffset.extra_data)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)
        diffset = self.create_diffset(review_request)

        return (get_diff_item_url(review_request, diffset.revision,
                                  local_site_name),
                diff_item_mimetype,
                diffset)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/diffs/<revision>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        self._testHttpCaching(
            get_diff_item_url(review_request, diffset.revision),
            check_etags=True)

    @webapi_test_template
    def test_get_with_patch_and_commit_history(self):
        """Testing the GET <API> API with Accept: x-patch and commit history
        contains only cumulative diff
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request=review_request)

        self.create_diffcommit(
            diffset=diffset,
            commit_id='r1',
            parent_id='r0',
            diff_contents=(
                b'diff --git a/ABC b/ABC\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- ABC\n'
                b'+++ ABC\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-line!\n'
                b'+line..\n'
            ))
        self.create_diffcommit(
            diffset=diffset,
            commit_id='r2',
            parent_id='r1',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 94bdd3e..197009f 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hello, world!\n'
                b'+Hi, world!\n'
            ))
        self.create_diffcommit(
            diffset=diffset,
            commit_id='r4',
            parent_id='r3',
            diff_contents=(
                b'diff --git a/README b/README\n'
                b'index 197009f..87abad9 100644\n'
                b'--- README\n'
                b'+++ README\n'
                b'@@ -1,1 +1,1 @@\n'
                b'-Hi, world!\n'
                b'+Yo, world.\n'
            ))

        cumulative_diff = (
            b'diff --git a/ABC b/ABC\n'
            b'index 94bdd3e..197009f 100644\n'
            b'--- ABC\n'
            b'+++ ABC\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-line!\n'
            b'+line..\n'
            b'diff --git a/README b/README\n'
            b'index 94bdd3e..87abad9 100644\n'
            b'--- README\n'
            b'+++ README\n'
            b'@@ -1,1 +1,1 @@\n'
            b'-Hello, world!\n'
            b'+Yo, world.\n'
        )

        diffset.finalize_commit_series(
            cumulative_diff=cumulative_diff,
            validation_info=None,
            validate=False,
            save=True)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            rsp = self.api_get(get_diff_item_url(review_request,
                                                 diffset.revision),
                               HTTP_ACCEPT='text/x-patch',
                               expected_json=False,
                               expected_mimetype='text/x-patch')

        self.assertEqual(rsp, cumulative_diff)

    @webapi_test_template
    def test_get_links_fields_dvcs_enabled(self):
        """Testing the GET <URL> API does includes DVCS-specific fields and
        links when the DVCS feature is enabled
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            rsp = self.api_get(get_diff_item_url(review_request,
                                                 diffset.revision),
                               expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff', rsp)

        item_rsp = rsp['diff']
        self.assertIn('links', item_rsp)
        self.assertIn('commits', item_rsp['links'])

        self.assertIn('commit_count', item_rsp)

    @webapi_test_template
    def test_get_links_fields_dvcs_disabled(self):
        """Testing the GET <URL> API does not includes DVCS-specific fields and
        links when the DVCS feature is enabled
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)

        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            rsp = self.api_get(get_diff_item_url(review_request,
                                                 diffset.revision),
                               expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn('diff', rsp)

        item_rsp = rsp['diff']
        self.assertIn('links', item_rsp)
        self.assertNotIn('commits', item_rsp['links'])
        self.assertNotIn('commit_count', item_rsp)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)
        diffset = self.create_diffset(review_request)

        return (get_diff_item_url(review_request, diffset.revision,
                                  local_site_name),
                diff_item_mimetype,
                {},
                diffset,
                [])

    def check_put_result(self, user, item_rsp, diffset):
        diffset = DiffSet.objects.get(pk=diffset.pk)
        self.compare_item(item_rsp, diffset)
