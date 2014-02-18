from __future__ import unicode_literals

from django.utils import six

from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import \
    file_attachment_comment_list_mimetype
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.urls import get_file_attachment_comment_list_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the FileAttachmentCommentResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/file-attachments/<id>/comments/'
    resource = resources.file_attachment_comment

    def setup_review_request_child_test(self, review_request):
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_comment_list_url(file_attachment),
                file_attachment_comment_list_mimetype)

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(submitter=user,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request)

        return get_file_attachment_comment_list_url(file_attachment)

    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)

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

        if populate_items:
            review = self.create_review(review_request, publish=True)
            items = [
                self.create_file_attachment_comment(review, file_attachment),
            ]
        else:
            items = []

        return (get_file_attachment_comment_list_url(file_attachment,
                                                     local_site_name),
                file_attachment_comment_list_mimetype,
                items)


# Satisfy the linter check. This resource is a list only, and doesn't
# support items.
ResourceItemTests = None
