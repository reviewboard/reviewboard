"""Unit tests for RootFileAttachmentCommentResource."""

from datetime import timedelta
from django.utils import timezone
from djblets.testing.decorators import add_fixtures
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    file_attachment_comment_list_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import \
    get_root_file_attachment_comment_list_url


class ResourceListTests(BaseWebAPITestCase,
                        metaclass=BasicTestsMetaclass):
    """Testing the RootFileAttachmentCommentResource API."""

    fixtures = ['test_users']
    sample_api_url = 'file-attachment-comments/'
    resource = resources.root_file_attachment_comment
    test_http_methods = ('GET',)

    def compare_item(self, item_rsp, comment):
        """Compare a comment item to a comment returned from the API.

        Args:
            item_rsp (dict):
                The serialized comment returned from the API.

            comment (reviewboard.reviews.models.FileAttachmentComment):
                The comment instance to compare to.

        Raises:
            AssertionError:
                The API response was not equivalent to the object.
        """
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)

        if comment.rich_text:
            self.assertEqual(item_rsp['text_type'], 'markdown')
        else:
            self.assertEqual(item_rsp['text_type'], 'plain')

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, user=user)
        comment = self.create_file_attachment_comment(review, file_attachment)

        if populate_items:
            items = [comment]
        else:
            items = []

        return (
            get_root_file_attachment_comment_list_url(local_site_name),
            file_attachment_comment_list_mimetype,
            items)

    @webapi_test_template
    def test_comment_is_same_as_canonical_comment(self):
        """Testing the GET <URL>/ API returns a proper data type"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        comment = self._create_file_attachment_comment(review_request, review)

        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp[self.resource.list_result_key][0], comment)

    @webapi_test_template
    def test_get_with_counts_only(self):
        """"Testing the GET <URL>/?counts-only=1 API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        self._create_file_attachment_comment(review_request, review)

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'counts-only': 1,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.file_attachment_comments.count())

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get(self):
        """"Testing the GET <URL>/? API returns only comments from reviews
        and review requests that the requester has access to
        """
        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Comment from a published review on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=True)
        comment1 = self._create_file_attachment_comment(review_request,
                                                        review1)

        # Comment from an unpublished review on a publicly-accessible
        # review request.
        review2 = self.create_review(review_request, publish=False)
        self._create_file_attachment_comment(review_request, review2)

        # Comment from a published review owned by the requester on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request,
                                     user=self.user,
                                     publish=True)
        comment3 = self._create_file_attachment_comment(review_request,
                                                        review3)

        # Comment from an unpublished review owned by the requester on a
        # publicly-accessible review request.
        review4 = self.create_review(review_request,
                                     user=self.user,
                                     publish=False)
        comment4 = self._create_file_attachment_comment(review_request,
                                                        review4)

        # Published review request from a private repository the requester
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Comment from a published review on a private repository the requester
        # does not have access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review5)

        # Comment from an unpublished review on a private repository the
        # requester does not have access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review6)

        # An invite-only review group used to limit access for the following
        # review requests.
        group = self.create_review_group(invite_only=True)

        # Comment from a published review from a review request that has an
        # invite-only review group not accessible to the requester, but they
        # have access to through being a targeted reviewer.
        review_request_targetted = self.create_review_request(publish=True)
        review_request_targetted.target_groups.add(group)
        review_request_targetted.target_people.add(self.user)
        review7 = self.create_review(review_request_targetted, publish=True)
        comment7 = self._create_file_attachment_comment(
            review_request_targetted,
            review7)

        # Comment from a published review from a review request that has an
        # invite-only review group not accessible to the requester, and that
        # they do not have access to because they are not listed as a
        # target reviewer.
        review_request_untargetted = self.create_review_request(publish=True)
        review_request_untargetted.target_groups.add(group)
        review8 = self.create_review(review_request_untargetted, publish=True)
        self._create_file_attachment_comment(
            review_request_untargetted,
            review8)

        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 4)
        self.compare_item(rsp_items[0], comment1)
        self.compare_item(rsp_items[1], comment3)
        self.compare_item(rsp_items[2], comment4)
        self.compare_item(rsp_items[3], comment7)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_by_repo(self):
        """Testing the GET <URL>/ API returns only comments from
        repositories that the requester has access to
        """
        # Comment from a public repository.
        repo1 = self.create_repository(name='repo1', public=True)
        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self._create_file_attachment_comment(review_request1,
                                                        review1)

        # Comment from a private repository that the requester has
        # access to from being listed in the repository's users list.
        repo2 = self.create_repository(name='repo2', public=False)
        repo2.users.add(self.user)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)
        comment2 = self._create_file_attachment_comment(review_request2,
                                                        review2)

        # An invite-only review group that the requester has access to.
        group_accessible = self.create_review_group(invite_only=True)
        group_accessible.users.add(self.user)

        # Comment from a private repository that the requester has
        # access to through being a member of a targeted review group.
        repo3 = self.create_repository(name='repo3', public=False)
        repo3.review_groups.add(group_accessible)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)
        comment3 = self._create_file_attachment_comment(review_request3,
                                                        review3)

        # Comment from a private repository that the requester does
        # not have access to.
        repo4 = self.create_repository(name='repo4', public=False)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo4)
        review4 = self.create_review(review_request4, publish=True)
        self._create_file_attachment_comment(review_request4, review4)

        # Comment from a private repository that the requester has access
        # to through being a member of a targeted review group and
        # being listed on the repository's users list.
        repo5 = self.create_repository(name='repo5', public=False)
        repo5.review_groups.add(group_accessible)
        repo5.users.add(self.user)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo5)
        review5 = self.create_review(review_request5, publish=True)
        comment5 = self._create_file_attachment_comment(review_request5,
                                                        review5)

        # An invite-only review group that the requester does not have
        # access to.
        group_inaccessible = self.create_review_group(invite_only=True)

        # Comment from a private repository that targets an invite-only review
        # group, but that the requester has access to from being listed in the
        # repository's users list.
        repo6 = self.create_repository(name='repo6', public=False)
        repo6.review_groups.add(group_inaccessible)
        repo6.users.add(self.user)
        review_request6 = self.create_review_request(publish=True,
                                                     repository=repo6)
        review6 = self.create_review(review_request6, publish=True)
        comment6 = self._create_file_attachment_comment(review_request6,
                                                        review6)

        # Comment from a private repository that targets an invite-only review
        # group and that the requester does not have access to.
        repo7 = self.create_repository(name='repo7', public=False)
        repo7.review_groups.add(group_inaccessible)
        review_request7 = self.create_review_request(publish=True,
                                                     repository=repo7)
        review7 = self.create_review(review_request7, publish=True)
        self._create_file_attachment_comment(review_request7, review7)

        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 5)
        self.compare_item(rsp_items[0], comment1)
        self.compare_item(rsp_items[1], comment2)
        self.compare_item(rsp_items[2], comment3)
        self.compare_item(rsp_items[3], comment5)
        self.compare_item(rsp_items[4], comment6)

    @webapi_test_template
    def test_get_by_review_group(self):
        """Testing the GET <URL>/ API returns only comments associated
        with review groups that the requester has access to
        """
        # Comment that the requester has access to from being in a public
        # review group that is targeted by the review request.
        group1 = self.create_review_group(name='group1', invite_only=False)
        group1.users.add(self.user)
        review_request1 = self.create_review_request(publish=True)
        review_request1.target_groups.add(group1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self._create_file_attachment_comment(review_request1,
                                                        review1)

        # Comment that the requester has access to from being in an invite-only
        # review group that is targeted by the review request.
        group2 = self.create_review_group(name='group2', invite_only=True)
        group2.users.add(self.user)
        review_request2 = self.create_review_request(publish=True)
        review_request2.target_groups.add(group2)
        review2 = self.create_review(review_request2, publish=True)
        comment2 = self._create_file_attachment_comment(review_request2,
                                                        review2)

        # Comment that the requester has access to since there is a public
        # review group that is targeted by the review request.
        group3 = self.create_review_group(name='group3', invite_only=False)
        review_request3 = self.create_review_request(publish=True)
        review_request3.target_groups.add(group3)
        review3 = self.create_review(review_request3, publish=True)
        comment3 = self._create_file_attachment_comment(review_request3,
                                                        review3)

        # Comment that the requester does not have access to since there is an
        # invite-only review group that is targeted by the review request.
        group4 = self.create_review_group(name='group4', invite_only=True)
        review_request4 = self.create_review_request(publish=True)
        review_request4.target_groups.add(group4)
        review4 = self.create_review(review_request4, publish=True)
        self._create_file_attachment_comment(review_request4, review4)

        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], comment1)
        self.compare_item(rsp_items[1], comment2)
        self.compare_item(rsp_items[2], comment3)

    @add_fixtures(['test_scmtools', 'test_site'])
    @webapi_test_template
    def test_get_by_local_site(self):
        """Testing the GET <URL> API returns only comments from local
        sites that the requester has access to
        """
        # Comment from a private local site that the requester has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(self.user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self._create_file_attachment_comment(review_request1,
                                                        review1)

        # Comment from a private local site that the requester does not have
        # access to.
        local_site2 = self.get_local_site('local-site-2')
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)
        self._create_file_attachment_comment(review_request2, review2)

        # Comment from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)
        self._create_file_attachment_comment(review_request3, review3)

        # Comment from a global site.
        review_request4 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review4 = self.create_review(review_request4, publish=True)
        comment4 = self._create_file_attachment_comment(review_request4,
                                                        review4)

        # Testing that only comments from the given local site are returned.
        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(
                local_site_name=local_site1.name),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

        # Testing that the requester is not authorized to make requests
        # to a local site that they do not have access to.
        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(
                local_site_name=local_site2.name),
            {'counts-only': 1},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

        # Testing that comments from local sites do not leak into results
        # from the global site.
        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(),
            {},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment4)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_review_id(self):
        """"Testing the GET <URL>/?review-id=<id> API returns only comments
        from reviews that the requester has access to
        """
        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Comment from a published review on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=True)
        comment1 = self._create_file_attachment_comment(review_request,
                                                        review1)

        # Comment from an unpublished review on a publicly-accessible
        # review request.
        review2 = self.create_review(review_request, publish=False)
        self._create_file_attachment_comment(review_request, review2)

        # Comment from a published review owned by the requester on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request,
                                     user=self.user,
                                     publish=True)
        self._create_file_attachment_comment(review_request, review3)

        # Comment from an unpublished review owned by the requester on a
        # publicly-accessible review request.
        review4 = self.create_review(review_request,
                                     user=self.user,
                                     publish=False)
        comment4 = self._create_file_attachment_comment(review_request,
                                                        review4)

        # Published review request from a private repository the requester
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Comment from a published review on a private repository the requester
        # does not have access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review5)

        # Comment from an unpublished review on a private repository the
        # requester does not have access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review6)

        # Testing that only comments from the given review are returned.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-id': review1.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

        # Testing that no comments get returned when querying for an
        # unpublished review that the requester does not have access to.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-id': review2.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

        # Testing that comments from an unpublished review that the requester
        # has access to get returned.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-id': review4.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment4)

        # Testing that no comments get returned when querying for a published
        # review on a private repository the requester does not have access to.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-id': review5.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

        # Testing that no comments get returned when querying for a review
        # that doesn't exist.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-id': -1,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_review_request(self):
        """"Testing the GET <URL>/?review-request-id=<id> API returns
        only comments from review requests that the requester has access to
        """
        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Comment from a published review on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=True)
        comment1 = self._create_file_attachment_comment(review_request,
                                                        review1)

        # Comment from an unpublished review on a publicly-accessible
        # review request.
        review2 = self.create_review(review_request, publish=False)
        self._create_file_attachment_comment(review_request, review2)

        # Comment from a published review owned by the requester on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request,
                                     user=self.user,
                                     publish=True)
        comment3 = self._create_file_attachment_comment(review_request,
                                                        review3)

        # Comment from an unpublished review owned by the requester on a
        # publicly-accessible review request.
        review4 = self.create_review(review_request,
                                     user=self.user,
                                     publish=False)
        comment4 = self._create_file_attachment_comment(review_request,
                                                        review4)

        # Published review request from a private repository the requester
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Comment from a published review on a private repository the requester
        # does not have access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review5)

        # Comment from an unpublished review on a private repository the
        # requester does not have access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)
        self._create_file_attachment_comment(review_request_inaccessible,
                                             review6)

        # Testing that only comments from the given review request
        # are returned.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-request-id': review_request.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 3)
        self.compare_item(rsp_items[0], comment1)
        self.compare_item(rsp_items[1], comment3)
        self.compare_item(rsp_items[2], comment4)

        # Testing that no comments are returned when the requester does
        # not have access to the given review request.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-request-id': review_request_inaccessible.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_review_request_from_local_site(self):
        """"Testing the GET <URL>/?review-request-id=<id> API with a LocalSite
        bound review request ID
        """
        # Comment from a review request on the global site.
        review_request1 = self.create_review_request(publish=True)
        review1 = self.create_review(review_request1, publish=True)
        comment1 = self._create_file_attachment_comment(review_request1,
                                                        review1)

        # Comment from a review request on a local site.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(self.user)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site1)
        review2 = self.create_review(review_request2, user=self.user,
                                     publish=True)
        comment2 = self._create_file_attachment_comment(review_request2,
                                                        review2,
                                                        text='localsite')

        # Testing that passing the local ID of a review request from a local
        # site properly returns comments from that review request.
        rsp = self.api_get(
            get_root_file_attachment_comment_list_url(
                local_site_name=local_site1.name),
            {'review-request-id': review_request2.local_id},
            expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment2)

        # Testing that comments from the local site review request do not leak
        # into the results when querying for a review request whose global ID
        # is the same as the local ID of the local site review request.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'review-request-id': review_request1.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

    @webapi_test_template
    def test_get_with_user(self):
        """"Testing the GET <URL>/?user=<user-name> API returns comments
        by user
        """
        review_request = self.create_review_request(publish=True)

        user1 = self.create_user(username='user1')

        review1 = self.create_review(review_request, publish=True, user=user1)
        comment1 = self._create_file_attachment_comment(review_request,
                                                        review1)

        review2 = self.create_review(review_request, publish=False, user=user1)
        self._create_file_attachment_comment(review_request, review2)

        user2 = self.create_user(username='user2')

        review3 = self.create_review(review_request, publish=True, user=user2)
        self._create_file_attachment_comment(review_request, review3)

        review4 = self.create_review(review_request, publish=False, user=user2)
        self._create_file_attachment_comment(review_request, review4)

        # Testing that only comments by the given user that the requester
        # has access to are returned.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'user': 'user1',
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

        # Testing that no comments are returned when the given user
        # doesn't exist.
        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'user': 'user3',
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 0)

    @webapi_test_template
    def test_get_with_file_attachment_id(self):
        """"Testing the GET <URL>/?file-attachment-id=<id> API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        file_attachment1 = self.create_file_attachment(review_request)
        comment1 = self.create_file_attachment_comment(review,
                                                       file_attachment1)

        file_attachment2 = self.create_file_attachment(review_request)
        comment2 = self.create_file_attachment_comment(review,
                                                       file_attachment2)

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'file-attachment-id': file_attachment1.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'file-attachment-id': file_attachment2.id,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment2)

    @webapi_test_template
    def test_get_with_file_attachment_name(self):
        """"Testing the GET general-comments/?file-name=<id> API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        file_attachment1 = self.create_file_attachment(review_request,
                                                       orig_filename='one')
        comment1 = self.create_file_attachment_comment(review,
                                                       file_attachment1)

        file_attachment2 = self.create_file_attachment(review_request,
                                                       orig_filename='two')
        self.create_file_attachment_comment(review, file_attachment2)

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'file-name': file_attachment1.orig_filename,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

    @webapi_test_template
    def test_get_by_last_updated_from_includes_from_date(self):
        """Testing the GET <URL>/?last-updated-from=<date> API
        returns only comments within the from date
        """
        now = timezone.now()

        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, publish=True,
                                    timestamp=(now - timedelta(hours=1)))

        # Comment created within the from date.
        comment1 = self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(now + timedelta(hours=1)))

        # Comment created on the from date.
        comment2 = self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=now)

        # Comment created outside of the from date.
        self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(now - timedelta(hours=1)))

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'last-updated-from': now.isoformat(),
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 2)
        self.compare_item(rsp_items[0], comment2)
        self.compare_item(rsp_items[1], comment1)

    @webapi_test_template
    def test_get_by_last_updated_to_includes_to_date(self):
        """Testing the GET <URL>/?last-updated-to=<date>
        API returns only comments within the to date
        """
        now = timezone.now()

        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(review_request, publish=True,
                                    timestamp=(now - timedelta(hours=1)))

        # Comment created within the to date.
        comment1 = self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(now - timedelta(hours=1)))

        # Comment created on the to date.
        self.create_file_attachment_comment(review,
                                            file_attachment,
                                            timestamp=now)

        # Comment created outside of the to date.
        self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(now + timedelta(hours=1)))

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'last-updated-to': now.isoformat(),
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment1)

    @webapi_test_template
    def test_get_by_last_updated_to_and_from_simple_date_format(self):
        """Testing the GET
        <URL>/?last-updated-from=<date>&last-updated-to=<date>
        API returns only comments within the from and to date
        """
        timestamp_from = timezone.now()
        timestamp_to = timezone.now() + timedelta(hours=1)

        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)
        review = self.create_review(
            review_request,
            publish=True,
            timestamp=(timestamp_from - timedelta(minutes=30)))

        # Comment created within the from and to date.
        comment = self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(timestamp_from + timedelta(minutes=30)))

        # Comment created before the from date.
        self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(timestamp_from - timedelta(minutes=30)))

        # Comment created after the to date.
        self.create_file_attachment_comment(
            review,
            file_attachment,
            timestamp=(timestamp_to + timedelta(minutes=30)))

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'last-updated-from': timestamp_from.isoformat(),
            'last-updated-to': timestamp_to.isoformat(),
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        rsp_items = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(rsp_items[0], comment)

    @webapi_test_template
    def test_get_with_is_reply(self):
        """Testing the GET <URL>/?is-reply=1 API"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        comment1 = self._create_file_attachment_comment(review_request, review)

        comment2 = self._create_file_attachment_comment(review_request,
                                                        review,
                                                        reply_to=comment1)

        rsp = self.api_get(get_root_file_attachment_comment_list_url(), {
            'is-reply': 1,
        }, expected_mimetype=file_attachment_comment_list_mimetype)
        items_rsp = rsp[self.resource.list_result_key]

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['total_results'], 1)
        self.compare_item(items_rsp[0], comment2)

    def _create_file_attachment_comment(self,
                                        review_request,
                                        review,
                                        **kwargs):
        """Creates a file attachment comment.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that the comment will be on.

            review (reviewboard.reviews.models.Review):
                The review that the comment will be on.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`create_file_attachment_comment`.

        Returns:
            reviewboard.reviews.models.FileAttachmentComment:
            The comment.
        """
        file_attachment = self.create_file_attachment(review_request)

        return self.create_file_attachment_comment(review,
                                                   file_attachment,
                                                   **kwargs)
