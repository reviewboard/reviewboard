from __future__ import unicode_literals

import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import six
from djblets.features.testing import override_feature_check
from djblets.webapi.errors import INVALID_ATTRIBUTE, INVALID_FORM_DATA
from djblets.webapi.testing.decorators import webapi_test_template
from kgb import SpyAgency

from reviewboard import scmtools
from reviewboard.diffviewer.commit_utils import (serialize_validation_info,
                                                 update_validation_info)
from reviewboard.diffviewer.features import dvcs_feature
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.reviews.models import DefaultReviewer
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.errors import DIFF_TOO_BIG
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_item_mimetype,
                                                diff_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_draft_diff_item_url,
                                           get_draft_diff_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ExtraDataListMixin, BaseWebAPITestCase):
    """Testing the DraftDiffResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/'
    resource = resources.draft_diff

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
            items = [self.create_diffset(review_request, draft=True)]
        else:
            items = []

        return (get_draft_diff_list_url(review_request, local_site_name),
                diff_list_mimetype,
                items)

    def test_get_not_owner(self):
        """Testing the GET review-requests/<id>/draft/diffs/ API
        without owner with Permission Denied error
        """
        review_request = self.create_review_request(create_repository=True)
        self.assertNotEqual(review_request.submitter, self.user)
        self.create_diffset(review_request, draft=True)

        self.api_get(get_draft_diff_list_url(review_request),
                     expected_status=403)

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

        if post_valid_data:
            diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                      content_type='text/x-patch')
            post_data = {
                'path': diff,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            }
        else:
            post_data = {}

        return (get_draft_diff_list_url(review_request, local_site_name),
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
        """Testing the POST review-requests/<id>/draft/diffs/ API
        with Invalid Form Data
        """
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)

        rsp = self.api_post(get_draft_diff_list_url(review_request),
                            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('path', rsp['fields'])

        # Now test with a valid path and an invalid basedir.
        # This is necessary because basedir is "optional" as defined by
        # the resource, but may be required by the form that processes the
        # diff.
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_draft_diff_list_url(review_request),
            {'path': diff},
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('basedir', rsp['fields'])

    def test_post_diffs_too_big(self):
        """Testing the POST review-requests/<id>/draft/diffs/ API
        with diff exceeding max size
        """
        repository = self.create_repository()
        review_request = self.create_review_request(repository=repository,
                                                    submitter=self.user)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        with self.siteconfig_settings({'diffviewer_max_diff_size': 2},
                                      reload_settings=False):
            rsp = self.api_post(
                get_draft_diff_list_url(review_request),
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

    @webapi_test_template
    def test_post_diff_with_history(self):
        """Testing the POST <URL> API with a diff and a review request created
        with history support
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    create_with_history=True)

        with override_feature_check(dvcs_feature.feature_id, True):
            rsp = self.api_post(
                get_draft_diff_list_url(review_request),
                {
                    'path': SimpleUploadedFile(
                        'diff', self.DEFAULT_GIT_FILEDIFF_DATA_DIFF),
                    'basedir': '',
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
            rsp = self.api_post(get_draft_diff_list_url(review_request), {},
                                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        item_rsp = rsp['diff']

        diff = DiffSet.objects.get(pk=item_rsp['id'])
        self.compare_item(item_rsp, diff)
        self.assertEqual(diff.files.count(), 0)

    @webapi_test_template
    def test_post_empty_dvcs_disabled(self):
        """Testing the POST <URL> API without a diff with the DVCS feature
        disabled
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    create_repository=True,
                                                    create_with_history=False)

        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            rsp = self.api_post(get_draft_diff_list_url(review_request), {},
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
        group = self.create_review_group(name='group1')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1',
            file_regex='.')
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(review_request.repository)

        diff = SimpleUploadedFile('diff', self.DEFAULT_GIT_README_DIFF,
                                  content_type='text/x-patch')

        rsp = self.api_post(
            get_draft_diff_list_url(review_request),
            {
                'path': diff,
                'basedir': '/trunk',
                'base_commit_id': '1234',
            },
            expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        draft = review_request.get_draft()
        self.assertEqual(list(draft.target_groups.all()), [group])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(SpyAgency, ExtraDataItemMixin, BaseWebAPITestCase):
    """Testing the DraftDiffResource item APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-requests/<id>/draft/diffs/<revision>/'
    resource = resources.draft_diff

    def setup_http_not_allowed_item_test(self, user):
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        return get_draft_diff_item_url(review_request, 1)

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
        diffset = self.create_diffset(review_request, draft=True)

        return (get_draft_diff_item_url(review_request, diffset.revision,
                                        local_site_name),
                diff_item_mimetype,
                diffset)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/draft/diffs/<revision>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=self.user)
        diffset = self.create_diffset(review_request, draft=True)

        self._testHttpCaching(
            get_draft_diff_item_url(review_request, diffset.revision),
            check_etags=True)

    def test_get_not_owner(self):
        """Testing the GET review-requests/<id>/draft/diffs/<revision>/ API
        without owner with Permission Denied error
        """
        review_request = self.create_review_request(create_repository=True)
        self.assertNotEqual(review_request.submitter, self.user)
        diffset = self.create_diffset(review_request, draft=True)

        self.api_get(
            get_draft_diff_item_url(review_request, diffset.revision),
            expected_status=403)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)
        diffset = self.create_diffset(review_request, draft=True)

        return (get_draft_diff_item_url(review_request, diffset.revision,
                                        local_site_name),
                diff_item_mimetype,
                {},
                diffset,
                [])

    def check_put_result(self, user, item_rsp, diffset):
        diffset = DiffSet.objects.get(pk=diffset.pk)
        self.compare_item(item_rsp, diffset)

    @webapi_test_template
    def test_put_finalize(self):
        """Testing the PUT <URL> API with finalize_commit_series=1"""
        def _get_file_exists(repository, path, revision,
                             base_commit_id=None, request=None):
            self.assertEqual(path, 'README')
            self.assertEqual(revision, '94bdd3e')

            return True

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_get_file_exists)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            commit = self.create_diffcommit(diffset=diffset)

            filediff = FileDiff.objects.get()

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            validation_info = update_validation_info(
                {},
                commit_id=commit.commit_id,
                parent_id=commit.parent_id,
                filediffs=[filediff])

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_mimetype=diff_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.compare_item(rsp['diff'], diffset)

    @webapi_test_template
    def test_put_finalized_with_parent(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 and a parent
        diff
        """
        def _get_file_exists(repository, path, revision,
                             base_commit_id=None, request=None):
            self.assertEqual(path, 'README')
            self.assertEqual(revision, 'f00f00')

            return True

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_get_file_exists)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            commit = self.create_diffcommit(diffset=diffset)

            filediff = FileDiff.objects.get()
            filediff.parent_diff = (
                b'diff --git a/README b/README\n'
                b'index f00f00..94bdd3e\n'
                b'--- a/README\n'
                b'+++ b/README\n'
            )
            filediff.extra_data[FileDiff._IS_PARENT_EMPTY_KEY] = True
            filediff.save(update_fields=('extra_data',))

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            parent_diff = SimpleUploadedFile('parent_diff',
                                             filediff.parent_diff,
                                             content_type='text/x-patch')

            validation_info = update_validation_info(
                {},
                commit_id=commit.commit_id,
                parent_id=commit.parent_id,
                filediffs=[filediff])

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'parent_diff': parent_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp['diff'], diffset)

    @webapi_test_template
    def test_put_finalize_adds_default_reviewers(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 adds
        default reviewers
        """
        def _get_file_exists(repository, path, revision,
                             base_commit_id=None, request=None):
            self.assertEqual(path, 'README')
            self.assertEqual(revision, '94bdd3e')

            return True

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_get_file_exists)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)

            # Create the state needed for the default reviewer.
            group = self.create_review_group(name='group1')

            default_reviewer = DefaultReviewer.objects.create(
                name='default1',
                file_regex='.')
            default_reviewer.groups.add(group)
            default_reviewer.repository.add(review_request.repository)

            # Create the state needed for the diff to post.
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            commit = self.create_diffcommit(diffset=diffset)

            filediff = FileDiff.objects.get()

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            validation_info = update_validation_info(
                {},
                commit_id=commit.commit_id,
                parent_id=commit.parent_id,
                filediffs=[filediff])

            # Post the diff.
            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_mimetype=diff_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.compare_item(rsp['diff'], diffset)

            draft = review_request.get_draft()
            self.assertEqual(list(draft.target_groups.all()), [group])

    @webapi_test_template
    def test_put_finalize_adds_default_reviewers_first_time_only(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 doesn't
        add default reviewers a second time
        """
        def _get_file_exists(repository, path, revision,
                             base_commit_id=None, request=None):
            self.assertEqual(path, 'README')
            self.assertEqual(revision, '94bdd3e')

            return True

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    call_fake=_get_file_exists)

        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)

            # Create the state needed for the default reviewer.
            group = self.create_review_group(name='group1')

            default_reviewer = DefaultReviewer.objects.create(
                name='default1',
                file_regex='.')
            default_reviewer.groups.add(group)
            default_reviewer.repository.add(review_request.repository)

            # Create the initial diffset. This should prevent a default
            # reviewer from being applied, since we're not publishing the first
            # diff on a review request.
            self.create_diffset(review_request=review_request)

            # Create the state needed for the diff to post.
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)

            commit = self.create_diffcommit(diffset=diffset)

            filediff = FileDiff.objects.get()

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            validation_info = update_validation_info(
                {},
                commit_id=commit.commit_id,
                parent_id=commit.parent_id,
                filediffs=[filediff])

            # Post the diff.
            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_mimetype=diff_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.compare_item(rsp['diff'], diffset)

            draft = review_request.get_draft()
            self.assertEqual(list(draft.target_groups.all()), [])

    @webapi_test_template
    def test_put_finalize_again(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when the
        diff is already finalized
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)

            diffset.finalize_commit_series(
                cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
                validation_info=None,
                validate=False,
                save=True)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info({}),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': INVALID_ATTRIBUTE.msg,
            },
            'reason': 'This diff is already finalized.',
        })

    @webapi_test_template
    def test_put_finalize_missing_fields(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 with missing
        request fields
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'cumulative_diff': [
                    'This field is required when finalize_commit_series is '
                    'set.',
                ],
                'validation_info': [
                    'This field is required when finalize_commit_series is '
                    'set.',
                ],
            },
        })

    @webapi_test_template
    def test_put_finalize_review_request_without_history(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when the
        review request was created without commit history support
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info({}),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': INVALID_ATTRIBUTE.msg,
            },
            'reason': 'This review request was not created with commit '
                      'history support.',
        })

    @webapi_test_template
    def test_put_finalize_dvcs_feature_disabled(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when the
        DVCS feature is disabled
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=False):
            review_request = self.create_review_request(
                create_repository=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info({}),
                },
                expected_mimetype=diff_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.compare_item(rsp['diff'], diffset)

    @webapi_test_template
    def test_put_finalize_empty_commit_series(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 for an empty
        commit series
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info({}),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_ATTRIBUTE.code,
                'msg': INVALID_ATTRIBUTE.msg,
            },
            'reason': 'Cannot finalize an empty commit series.',
        })

    @webapi_test_template
    def test_put_finalize_invalid_validation_info_base64(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when
        validation_info is invalid base64
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': 'foo',
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'validation_info': [
                    'Could not parse field: Incorrect padding',
                ],
            },
        })

    @webapi_test_template
    def test_put_finalize_invalid_validation_info_json_format(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when
        validation_info is invalid json
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info('foo'),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'validation_info': [
                    'Could not parse field: Invalid format.',
                ],
            },
        })

    @webapi_test_template
    def test_put_finalize_invalid_validation_info_not_json(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when
        validation_info is JSON in the incorrect format
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            self.create_diffcommit(diffset=diffset)

            cumulative_diff = SimpleUploadedFile('diff', b'',
                                                 content_type='text/x-patch')
            validation_info = base64.b64encode(b'AAAAAAA').decode('utf-8')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': validation_info,
                },
                expected_status=400)

        # Python 2 and 3 differ in the error contents you'll get when
        # attempting to load non-JSON data.
        if six.PY3:
            expected_error = (
                'Could not parse field: Expecting value: line 1 '
                'column 1 (char 0)'
            )
        else:
            expected_error = \
                'Could not parse field: No JSON object could be decoded'

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'validation_info': [expected_error],
            },
        })

    @webapi_test_template
    def test_put_finalize_validation_info_extra_commits(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when
        validation_info contains commits that do not exist
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)
            commit = self.create_diffcommit(diffset=diffset)
            filediff = commit.files.first()

            validation_info = update_validation_info(
                {},
                commit_id=commit.commit_id,
                parent_id=commit.parent_id,
                filediffs=[filediff])

            validation_info = update_validation_info(
                validation_info,
                commit_id='f00',
                parent_id=commit.commit_id,
                filediffs=[])

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'validation_info': [
                    'The following commits are specified in validation_info '
                    'but do not exist: f00'
                ],
            },
        })

    @webapi_test_template
    def test_put_finalize_validation_info_missing_commits(self):
        """Testing the PUT <URL> API with finalize_commit_series=1 when
        validation_info does not contain all commits
        """
        with override_feature_check(dvcs_feature.feature_id, enabled=True):
            review_request = self.create_review_request(
                create_repository=True,
                create_with_history=True,
                submitter=self.user)
            diffset = self.create_diffset(review_request=review_request,
                                          draft=True)

            commits = [
                self.create_diffcommit(diffset=diffset, **kwargs)
                for kwargs in (
                    {'commit_id': 'r1', 'parent_id': 'r0'},
                    {'commit_id': 'r2', 'parent_id': 'r1'},
                )
            ]

            filediff = commits[0].files.first()

            validation_info = update_validation_info(
                {},
                commit_id=commits[0].commit_id,
                parent_id=commits[0].parent_id,
                filediffs=[filediff])

            cumulative_diff = SimpleUploadedFile('diff', filediff.diff,
                                                 content_type='text/x-patch')

            rsp = self.api_put(
                get_draft_diff_item_url(review_request, diffset.revision),
                {
                    'finalize_commit_series': True,
                    'cumulative_diff': cumulative_diff,
                    'validation_info': serialize_validation_info(
                        validation_info),
                },
                expected_status=400)

        self.assertEqual(rsp, {
            'stat': 'fail',
            'err': {
                'code': INVALID_FORM_DATA.code,
                'msg': INVALID_FORM_DATA.msg,
            },
            'fields': {
                'validation_info': [
                    'The following commits exist but are not present in '
                    'validation_info: r2',
                ],
            }
        })
