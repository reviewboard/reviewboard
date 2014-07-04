from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import filediff_comment_list_mimetype
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.urls import get_filediff_comment_list_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the FileDiffCommentResource list APIs."""
    fixtures = ['test_users', 'test_scmtools']
    sample_api_url = \
        'review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/'
    resource = resources.filediff_comment

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository_id:
            # The group tests don't create a repository by default.
            review_request.repository = self.create_repository()
            review_request.save()

        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)
        self.create_review(review_request, publish=True)

        return (get_filediff_comment_list_url(filediff),
                filediff_comment_list_mimetype)

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(create_repository=True,
                                                    submitter=user,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        return get_filediff_comment_list_url(filediff)

    def compare_item(self, item_rsp, filediff):
        self.assertEqual(item_rsp['id'], filediff.pk)
        self.assertEqual(item_rsp['text'], filediff.text)

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
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        if populate_items:
            review = self.create_review(review_request, publish=True)
            items = [
                self.create_diff_comment(review, filediff),
            ]
        else:
            items = []

        return (get_filediff_comment_list_url(filediff, local_site_name),
                filediff_comment_list_mimetype,
                items)

    def test_get_as_anonymous(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        as an anonymous user
        """
        diff_comment_text = 'Sample comment.'

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff,
                                           text=diff_comment_text)

        self.client.logout()

        rsp = self.api_get(get_filediff_comment_list_url(filediff),
                           expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], comment.text)

    def test_get_with_line(self):
        """Testing the
        GET review-requests/<id>/diffs/<revision>/files/<id>/diff-comments/ API
        with ?line=
        """
        diff_comment_text = 'Sample comment.'
        diff_comment_line = 10

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        self.create_diff_comment(review, filediff,
                                 text=diff_comment_text,
                                 first_line=diff_comment_line)
        self.create_diff_comment(review, filediff,
                                 first_line=diff_comment_line + 1)

        rsp = self.api_get(get_filediff_comment_list_url(filediff), {
            'line': diff_comment_line,
        }, expected_mimetype=filediff_comment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(len(rsp['diff_comments']), 1)
        self.assertEqual(rsp['diff_comments'][0]['text'], diff_comment_text)
        self.assertEqual(rsp['diff_comments'][0]['first_line'],
                         diff_comment_line)


# Satisfy the linter check. This resource is a list only, and doesn't
# support items.
ResourceItemTests = None
