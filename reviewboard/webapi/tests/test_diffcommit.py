"""Unit tests for the DiffCommitResource."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.features.testing import override_feature_checks
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.reviews.models import ReviewRequest
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diffcommit_item_mimetype,
                                                diffcommit_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import ExtraDataItemMixin
from reviewboard.webapi.tests.urls import (get_diffcommit_item_url,
                                           get_diffcommit_list_url)


def compare_diffcommit(self, item_rsp, item):
    """Compare a serialized DiffCommit to the original.

    Args:
        item_rsp (dict):
            The serialized response.

        item (reviewboard.diffviewer.models.diffcommit.DiffCommit):
            The DiffCommit to compare against.

    Raises:
        AssertionError:
            The serialized response is not equivalent to the original
            DiffCommit.
    """
    self.assertEqual(item_rsp['id'], item.pk)
    self.assertEqual(item_rsp['commit_id'], item.commit_id)
    self.assertEqual(item_rsp['parent_id'], item.parent_id)
    self.assertEqual(item_rsp['commit_message'], item.commit_message)
    self.assertEqual(item_rsp['author_name'], item.author_name)
    self.assertEqual(item_rsp['author_email'], item.author_email)
    self.assertEqual(item_rsp['committer_name'], item.committer_name)
    self.assertEqual(item_rsp['committer_email'], item.committer_email)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Tests for DiffCommitResource list resource."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = 'review-request/<id>/diffs/<revision>/commits/'
    resource = resources.diffcommit

    compare_item = compare_diffcommit

    def setup_http_not_allowed_list_test(self, user):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            create_with_history=True,
            public=True)

        diffset = self.create_diffset(review_request=review_request)
        return get_diffcommit_list_url(review_request, diffset.revision)

    def setup_review_request_child_test(self, review_request):
        review_request.extra_data = review_request.extra_data or {}
        review_request.extra_data[
            ReviewRequest._CREATED_WITH_HISTORY_EXTRA_DATA_KEY] = True
        review_request.save(update_fields=('extra_data',))

        diffset = self.create_diffset(review_request=review_request)

        return (get_diffcommit_list_url(review_request,
                                        diffset.revision),
                diffcommit_list_mimetype)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            repository=repository,
            public=True)
        diffset = self.create_diffset(review_request=review_request)
        items = []

        if populate_items:
            items.append(self.create_diffcommit(diffset=diffset,
                                                repository=repository))

        return (get_diffcommit_list_url(review_request,
                                        diffset.revision,
                                        local_site_name=local_site_name),
                diffcommit_list_mimetype,
                items)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, ReviewRequestChildItemMixin,
                        BaseWebAPITestCase):
    """Tests for DiffCommitResource item resource."""

    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = \
        'review-request/<id>/diffs/<revision>/commits/<commit-id>/'
    resource = resources.diffcommit

    compare_item = compare_diffcommit

    def setup_review_request_child_test(self, review_request):
        diffset = self.create_diffset(review_request=review_request)
        review_request.extra_data[
            ReviewRequest._CREATED_WITH_HISTORY_EXTRA_DATA_KEY] = True
        review_request.save(update_fields=('extra_data',))
        commit = self.create_diffcommit(diffset=diffset,
                                        repository=review_request.repository)

        return (get_diffcommit_item_url(review_request,
                                        diffset.revision,
                                        commit.commit_id),
                diffcommit_item_mimetype)

    def setup_http_not_allowed_item_test(self, user):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            public=True)
        diffset = self.create_diffset(review_request=review_request)
        commit = self.create_diffcommit(diffset=diffset,
                                        repository=repository)
        return get_diffcommit_item_url(review_request, diffset.revision,
                                       commit.commit_id)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            with_local_site=with_local_site)
        diffset = self.create_diffset(review_request)
        commit = self.create_diffcommit(diffset=diffset,
                                        repository=repository)

        return (get_diffcommit_item_url(review_request, diffset.revision,
                                        commit.commit_id, local_site_name),
                diffcommit_item_mimetype,
                commit)

    @webapi_test_template
    def test_get_patch(self):
        """Testing the GET <URL> API with Accept: text/x-patch"""
        url = self.setup_basic_get_test(self.user,
                                        with_local_site=False,
                                        local_site_name=None)[0]

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url,
                           expected_mimetype='text/x-patch',
                           expected_json=False,
                           HTTP_ACCEPT='text/x-patch')

        self.assertEqual(self.DEFAULT_GIT_FILEDIFF_DATA_DIFF, rsp)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_patch_local_site(self):
        """Testing the GET <URL> API with Accept: text/x-patch on a Local Site
        """
        url = self.setup_basic_get_test(
            User.objects.get(username='doc'),
            with_local_site=True,
            local_site_name=self.local_site_name)[0]

        self.client.login(username='doc', password='doc')

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url,
                           expected_mimetype='text/x-patch',
                           expected_json=False,
                           HTTP_ACCEPT='text/x-patch')

        self.assertEqual(self.DEFAULT_GIT_FILEDIFF_DATA_DIFF, rsp)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_patch_local_site_no_access(self):
        """Testing the GET <URL> API with Accept: text/x-patch on a Local Site
        without access
        """
        url = self.setup_basic_get_test(
            User.objects.get(username='doc'),
            with_local_site=True,
            local_site_name=self.local_site_name)[0]

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url,
                           expected_status=403,
                           HTTP_ACCEPT='text/x-patch')

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @webapi_test_template
    def test_get_patch_private_repository(self):
        """Testing the GET <URL> API with Accept: text/x-patch on a private
        repository
        """
        doc = User.objects.get(username='doc')

        repository = self.create_repository(tool_name='Git', public=False)
        repository.users = [doc]

        review_request = self.create_review_request(repository=repository,
                                                    submitter=doc)
        diffset = self.create_diffset(review_request)
        commit = self.create_diffcommit(diffset=diffset, repository=repository)

        self.client.login(username='doc', password='doc')

        with override_feature_checks(self.override_features):
            rsp = self.api_get(
                get_diffcommit_item_url(review_request, diffset.revision,
                                        commit.commit_id),
                expected_mimetype='text/x-patch',
                expected_json=False,
                HTTP_ACCEPT='text/x-patch')

        self.assertEqual(self.DEFAULT_GIT_FILEDIFF_DATA_DIFF, rsp)

    @webapi_test_template
    def test_get_patch_private_repository_no_access(self):
        """Testing the GET <URL> API with Accept: text/x-patch on a private
        repository
        """
        doc = User.objects.get(username='doc')

        repository = self.create_repository(tool_name='Git', public=False)
        repository.users = [doc]

        review_request = self.create_review_request(repository=repository,
                                                    submitter=doc)
        diffset = self.create_diffset(review_request)
        commit = self.create_diffcommit(diffset=diffset, repository=repository)

        with override_feature_checks(self.override_features):
            rsp = self.api_get(
                get_diffcommit_item_url(review_request, diffset.revision,
                                        commit.commit_id),
                expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(
            repository=repository,
            submitter=user,
            with_local_site=with_local_site)
        diffset = self.create_diffset(review_request)
        commit = self.create_diffcommit(diffset=diffset,
                                        repository=repository)

        return (get_diffcommit_item_url(review_request,
                                        diffset.revision,
                                        commit.commit_id,
                                        local_site_name=local_site_name),
                diffcommit_item_mimetype,
                {},
                commit,
                [])

    def check_put_result(self, user, item_rsp, item):
        self.compare_item(item_rsp, item)
