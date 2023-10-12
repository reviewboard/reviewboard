from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.accounts.models import Profile
from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import (
    ReviewRequest,
    ReviewRequestDraft)
from reviewboard.reviews.models.review_request import FileAttachmentState
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    draft_file_attachment_item_mimetype,
    draft_file_attachment_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_draft_file_attachment_item_url,
                                           get_draft_file_attachment_list_url)


class ResourceListTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Testing the DraftFileAttachmentResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/file-attachments/'
    resource = resources.draft_file_attachment

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    def setup_http_not_allowed_item_test(self, user):
        review_request = self.create_review_request(
            submitter=user)

        return get_draft_file_attachment_list_url(review_request)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        if populate_items:
            items = [self.create_file_attachment(review_request, draft=True)]
        else:
            items = []

        return (get_draft_file_attachment_list_url(review_request,
                                                   local_site_name),
                draft_file_attachment_list_mimetype,
                items)

    def test_get_with_non_owner_superuser(self):
        """Testing the GET review-requests/<id>/draft/file-attachments/ API
        with non-owner as superuser
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        user = self._login_user(admin=True)
        self.assertNotEqual(user, review_request.submitter)

        rsp = self.api_get(
            get_draft_file_attachment_list_url(review_request),
            expected_mimetype=draft_file_attachment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        attachments = rsp['draft_file_attachments']
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]['id'], attachment.pk)

    @add_fixtures(['test_site'])
    def test_get_with_non_owner_local_site_admin(self):
        """Testing the GET review-requests/<id>/draft/file-attachments/ API
        with non-owner as LocalSite admin
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        attachment = self.create_file_attachment(review_request, draft=True)

        user = self._login_user(local_site=True, admin=True)
        self.assertNotEqual(user, review_request.submitter)
        self.assertFalse(user.is_superuser)

        rsp = self.api_get(
            get_draft_file_attachment_list_url(review_request,
                                               self.local_site_name),
            expected_mimetype=draft_file_attachment_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        attachments = rsp['draft_file_attachments']
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]['id'], attachment.pk)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        if post_valid_data:
            post_data = {
                'path': open(self.get_sample_image_filename(), 'rb'),
                'caption': 'New caption',
            }
        else:
            post_data = {}

        return (get_draft_file_attachment_list_url(review_request,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                post_data,
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn('draft_file_attachment', rsp)
        item_rsp = rsp['draft_file_attachment']

        attachment = FileAttachment.objects.get(pk=item_rsp['id'])
        self.assertIn(attachment, draft.file_attachments.all())
        self.assertNotIn(attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, attachment)

    def test_post_with_permission_denied_error(self):
        """Testing the POST review-requests/<id>/draft/file-attachments/ API
        with Permission Denied error
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        with open(self.get_sample_image_filename(), 'rb') as f:
            rsp = self.api_post(
                get_draft_file_attachment_list_url(review_request),
                {
                    'caption': 'Trophy',
                    'path': f,
                },
                expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ResourceItemTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Testing the DraftFileAttachmentResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/draft/file-attachments/<id>/'
    resource = resources.draft_file_attachment

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['filename'], attachment.filename)

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(
            submitter=user)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        return get_draft_file_attachment_item_url(review_request,
                                                  file_attachment.pk)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                [review_request, file_attachment])

    def check_delete_result(self, user, review_request, file_attachment):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertNotIn(file_attachment,
                         draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())
        self.assertNotIn(file_attachment,
                         review_request.file_attachments.all())
        self.assertNotIn(file_attachment,
                         review_request.inactive_file_attachments.all())

        with self.assertRaises(FileAttachment.DoesNotExist):
            FileAttachment.objects.get(pk=file_attachment.pk)

    def test_delete_file_with_non_owner_superuser(self):
        """Testing the DELETE review-requests/<id>/draft/file-attachments/<id>/
        API with non-owner as superuser
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        user = self._login_user(admin=True)
        self.api_delete(get_draft_file_attachment_item_url(review_request,
                                                           file_attachment.pk))

        self.check_delete_result(user, review_request, file_attachment)

    @add_fixtures(['test_site'])
    def test_delete_file_with_non_owner_local_site_admin(self):
        """Testing the DELETE review-requests/<id>/draft/file-attachments/<id>/
        API with non-owner as LocalSite admin
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        user = self._login_user(local_site=True, admin=True)
        self.assertNotEqual(user, self.user)

        self.api_delete(get_draft_file_attachment_item_url(
            review_request, file_attachment.pk, self.local_site_name))

        self.check_delete_result(user, review_request, file_attachment)

    def test_delete_file_with_publish(self):
        """Testing the DELETE review-requests/<id>/draft/file-attachments/<id>/
        API with published file attachment
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    target_people=[self.user])
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)
        review_request.get_draft().publish()

        self.api_delete(get_draft_file_attachment_item_url(review_request,
                                                           file_attachment.pk))

        draft = review_request.get_draft()
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)

        self.assertFalse(file_attachment.inactive_review_request.exists())
        self.assertIsNotNone(draft)
        self.assertIn(file_attachment,
                      draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)

        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                file_attachment)

    def test_get_with_caption(self) -> None:
        """Testing the GET review-requests/<id>/draft/file-attachments/<id>/
        with a draft caption
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(
            review_request,
            draft=True,
            caption='Published caption',
            draft_caption='Draft caption')

        rsp = self.api_get(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk),
            expected_mimetype=draft_file_attachment_item_mimetype)
        item_rsp = rsp['draft_file_attachment']

        file_attachment.refresh_from_db()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(item_rsp['caption'], 'Draft caption')
        self.assertEqual(file_attachment.draft_caption, 'Draft caption')
        self.assertEqual(file_attachment.caption, 'Published caption')

    def test_get_with_empty_caption(self) -> None:
        """Testing the GET review-requests/<id>/draft/file-attachments/<id>/
        with an empty draft caption
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(
            review_request,
            draft=True,
            caption='Published caption',
            draft_caption='')

        rsp = self.api_get(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk),
            expected_mimetype=draft_file_attachment_item_mimetype)
        item_rsp = rsp['draft_file_attachment']

        file_attachment.refresh_from_db()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(item_rsp['caption'], '')
        self.assertEqual(file_attachment.draft_caption, '')
        self.assertEqual(file_attachment.caption, 'Published caption')

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk,
                                                   local_site_name),
                draft_file_attachment_item_mimetype,
                {'caption': 'My new caption'},
                file_attachment,
                [])

    def check_put_result(self, user, item_rsp, file_attachment):
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(item_rsp['caption'], 'My new caption')
        self.assertEqual(file_attachment.draft_caption, 'My new caption')

    def test_put_with_empty_caption(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with an empty caption
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)

        rsp = self.api_put(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk),
            {
                'caption': '',
            },
            expected_mimetype=draft_file_attachment_item_mimetype)
        item_rsp = rsp['draft_file_attachment']

        file_attachment.refresh_from_db()

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(item_rsp['caption'], '')
        self.assertEqual(file_attachment.draft_caption, '')
        self.assertEqual(file_attachment.caption, 'My Caption')

    def test_put_with_non_owner_superuser(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        API with non-owner as superuser
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)

        user = self._login_user(admin=True)
        self.assertNotEqual(user, self.user)

        rsp = self.api_put(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk),
            {
                'caption': 'My new caption',
            },
            expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.check_put_result(user, rsp['draft_file_attachment'],
                              file_attachment)

    @add_fixtures(['test_site'])
    def test_put_file_with_non_owner_local_site_admin(self):
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        API with non-owner as LocalSite admin
        """
        review_request = self.create_review_request(submitter=self.user,
                                                    with_local_site=True,
                                                    publish=True)
        file_attachment = self.create_file_attachment(review_request,
                                                      draft=True)

        user = self._login_user(local_site=True, admin=True)
        self.assertNotEqual(user, self.user)

        rsp = self.api_put(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk,
                                               self.local_site_name),
            {
                'caption': 'My new caption',
            },
            expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.check_put_result(user, rsp['draft_file_attachment'],
                              file_attachment)

    def test_put_with_pending_deletion_true(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting pending_deletion to True
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)

        rsp = self.api_put(
            get_draft_file_attachment_item_url(review_request,
                                               file_attachment.pk),
            {
                'pending_deletion': True,
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], 105)
        self.assertEqual(
            rsp['fields'],
            {
                'pending_deletion': 'This can only be set to false to undo '
                                    'the pending deletion of a published file '
                                    'attachment. You cannot set this to true.',
            })

    def test_put_with_caption(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting a new caption and when a draft already exists
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request_draft = self.create_review_request_draft(review_request)

        # 12 queries:
        #
        #  1. Fetch request user
        #  2. Fetch request user's Profile
        #  3. Fetch review request
        #  4. Fetch review request draft
        #  5. Fetch file attachment
        #  6. Fetch review request draft
        #  7. Save any file attachment updates
        #  8. Save the review request draft last_updated field
        #  9. Fetch the review request draft
        # 10. Fetch review request
        # 11. Fetch review request
        # 12. Fetch review request
        queries = [
            {
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=self.user),
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter', 'repository'},
                'where': (Q(local_site=None) &
                          Q(pk=str(review_request.pk))),
            },
            {
                'model': ReviewRequestDraft,
                'select_related': {'review_request'},
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 4,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest_inactive_file_attachments',
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                    'reviews_reviewrequestdraft_file_attachments'
                },
                'where': (((Q(review_request=review_request) &
                            Q(added_in_filediff__isnull=True) &
                            Q(repository__isnull=True) &
                            Q(user__isnull=True)) |
                           Q(inactive_review_request=review_request) |
                           Q(drafts=review_request_draft) |
                           Q(inactive_drafts=review_request_draft)) &
                          Q(pk=str(review_request.pk)))
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'type': 'UPDATE',
                'where': Q(pk=file_attachment.pk),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk)
            },
            {
                'model': ReviewRequestDraft,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequestdraft_file_attachments',
                    'reviews_reviewrequestdraft',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'where': Q(id=review_request.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
        ]

        # The purpose of this test is to see what queries are being executed,
        # to compare against the queries executed during ``pending_deletion``
        # updates.
        with self.assertQueries(queries):
            rsp = self.api_put(
                get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk),
                {
                    'caption': 'Updated caption',
                },
                expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    def test_put_with_pending_deletion_false(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting pending_deletion to False for a file attachment that
        is currently pending deletion
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request_draft = self.create_review_request_draft(review_request)

        # "Delete" the file attachment.
        review_request_draft.inactive_file_attachments.add(file_attachment)
        review_request_draft.file_attachments.remove(file_attachment)

        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment),
            FileAttachmentState.PENDING_DELETION)

        del review_request._file_attachments_data

        # 25 queries:
        #
        #  1. Fetch request user
        #  2. Fetch request user's Profile
        #  3. Fetch review request
        #  4. Fetch review request draft
        #  5. Fetch file attachment
        #  6. Fetch review request draft
        #  7. Save any file attachment updates
        #  8. Fetch review request when getting file attachment state
        #  9. Fetch active file attachments when getting file attachment state
        # 10. Fetch review request draft when getting file attachment state
        # 11. Fetch inactive draft file attachments when getting file
        #     attachment state
        # 12. Fetch file attachment IDs matching history ID
        # 13. Fetch inactive draft file attachments
        # 14. Remove file attachment from inactive draft file attachments
        # 15. Update inactive draft file attachments count
        # 16. Fetch inactive draft file attachments count
        # 17. Fetch active draft file attachments
        # 18. Add file attachment to active draft file attachments
        # 19. Update active draft file attachments count
        # 20. Fetch active draft file attachments count
        # 21. Save the review request draft last_updated field
        # 22. Fetch review request draft
        # 23. Fetch review request
        # 24. Fetch review request
        # 25. Fetch review request
        queries = [
            {
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=self.user),
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter', 'repository'},
                'where': (Q(local_site=None) &
                          Q(pk=str(review_request.pk))),
            },
            {
                'model': ReviewRequestDraft,
                'select_related': {'review_request'},
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 4,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest_inactive_file_attachments',
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                    'reviews_reviewrequestdraft_file_attachments'
                },
                'where': (((Q(review_request=review_request) &
                            Q(added_in_filediff__isnull=True) &
                            Q(repository__isnull=True) &
                            Q(user__isnull=True)) |
                           Q(inactive_review_request=review_request) |
                           Q(drafts=review_request_draft) |
                           Q(inactive_drafts=review_request_draft)) &
                          Q(pk=str(review_request.pk)))
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'type': 'UPDATE',
                'where': Q(pk=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'where': Q(id=review_request.pk),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=review_request.pk),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                },
                'where': Q(inactive_drafts__id=review_request_draft.pk),
            },
            {
                'model': FileAttachment,
                'where': Q(
                    attachment_history=file_attachment.attachment_history_id),
                'values_select': ('pk',),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': (Q(reviewrequestdraft=(review_request_draft.pk,)) &
                          Q(fileattachment__in={file_attachment.pk})),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[file_attachment.pk]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'limit': 1,
                'values_select': ('inactive_file_attachments_count',),
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'values_select': ('fileattachment',),
                'where': (Q(fileattachment__in={file_attachment.pk}) &
                          Q(reviewrequestdraft=review_request_draft.pk)),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'limit': 1,
                'values_select': ('file_attachments_count',),
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk)
            },
            {
                'model': ReviewRequestDraft,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequestdraft_file_attachments',
                    'reviews_reviewrequestdraft',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'where': Q(id=review_request.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
        ]

        with self.assertQueries(queries):
            rsp = self.api_put(
                get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk),
                {
                    'pending_deletion': False,
                },
                expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment),
            FileAttachmentState.PUBLISHED)

    def test_put_with_pending_deletion_false_with_history(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting pending_deletion to False for a file attachment that
        is currently pending deletion and has a history of revisions
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        file_attachment_2 = self.create_file_attachment(
            review_request,
            attachment_history=file_attachment.attachment_history,
            attachment_revision=file_attachment.attachment_revision + 1)
        review_request_draft = self.create_review_request_draft(review_request)

        # "Delete" the file attachment and all revisions of it.
        review_request_draft.inactive_file_attachments.add(file_attachment)
        review_request_draft.file_attachments.remove(file_attachment)
        review_request_draft.inactive_file_attachments.add(file_attachment_2)
        review_request_draft.file_attachments.remove(file_attachment_2)

        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment),
            FileAttachmentState.PENDING_DELETION)
        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment_2),
            FileAttachmentState.PENDING_DELETION)

        del review_request._file_attachments_data

        # 25 queries:
        #
        #  1. Fetch request user
        #  2. Fetch request user's Profile
        #  3. Fetch review request
        #  4. Fetch review request draft
        #  5. Fetch file attachment
        #  6. Fetch review request draft
        #  7. Save any file attachment updates
        #  8. Fetch review request when getting file attachment state
        #  9. Fetch active file attachments when getting file attachment state
        # 10. Fetch review request draft when getting file attachment state
        # 11. Fetch inactive draft file attachments when getting file
        #     attachment state
        # 12. Fetch file attachment IDs matching history ID
        # 13. Fetch inactive draft file attachments
        # 14. Remove file attachments from inactive draft file attachments
        # 15. Update inactive draft file attachments count
        # 16. Fetch inactive draft file attachments count
        # 17. Fetch active draft file attachments
        # 18. Add file attachments to active draft file attachments
        # 19. Update active draft file attachments count
        # 20. Fetch active draft file attachments count
        # 21. Save the review request draft last_updated field
        # 22. Fetch review request draft
        # 23. Fetch review request
        # 24. Fetch review request
        # 25. Fetch review request
        queries = [
            {
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=self.user),
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter', 'repository'},
                'where': (Q(local_site=None) &
                          Q(pk=str(review_request.pk))),
            },
            {
                'model': ReviewRequestDraft,
                'select_related': {'review_request'},
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 4,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest_inactive_file_attachments',
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                    'reviews_reviewrequestdraft_file_attachments'
                },
                'where': (((Q(review_request=review_request) &
                            Q(added_in_filediff__isnull=True) &
                            Q(repository__isnull=True) &
                            Q(user__isnull=True)) |
                           Q(inactive_review_request=review_request) |
                           Q(drafts=review_request_draft) |
                           Q(inactive_drafts=review_request_draft)) &
                          Q(pk=str(review_request.pk)))
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'type': 'UPDATE',
                'where': Q(pk=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'where': Q(id=review_request.pk),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=review_request.pk),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                },
                'where': Q(inactive_drafts__id=review_request_draft.pk),
            },
            {
                'model': FileAttachment,
                'where': Q(
                    attachment_history=file_attachment.attachment_history_id),
                'values_select': ('pk',),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': (Q(reviewrequestdraft=(review_request_draft.pk,)) &
                          Q(fileattachment__in={file_attachment.pk,
                                                file_attachment_2.pk})),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[file_attachment_2.pk,
                                   file_attachment.pk]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'limit': 1,
                'values_select': ('inactive_file_attachments_count',),
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'values_select': ('fileattachment',),
                'where': (Q(fileattachment__in={file_attachment.pk,
                                                file_attachment_2.pk}) &
                          Q(reviewrequestdraft=review_request_draft.pk)),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'limit': 1,
                'values_select': ('file_attachments_count',),
                'where': Q(pk=review_request_draft.pk),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(pk=review_request_draft.pk)
            },
            {
                'model': ReviewRequestDraft,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequestdraft_file_attachments',
                    'reviews_reviewrequestdraft',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'where': Q(id=review_request.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
        ]

        with self.assertQueries(queries):
            rsp = self.api_put(
                get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk),
                {
                    'pending_deletion': False,
                },
                expected_mimetype=draft_file_attachment_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment),
            FileAttachmentState.PUBLISHED)
        self.assertEqual(
            review_request.get_file_attachment_state(file_attachment_2),
            FileAttachmentState.PUBLISHED)

    def test_put_with_pending_deletion_false_for_invalid(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting pending_deletion to False for a file attachment that isn't
        currently pending deletion
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request_draft = self.create_review_request_draft(review_request)

        # 11 queries:
        #
        #  1. Fetch request user
        #  2. Fetch request user's Profile
        #  3. Fetch review request
        #  4. Fetch review request draft
        #  5. Fetch file attachment
        #  6. Fetch review request draft
        #  7. Save any file attachment updates
        #  8. Fetch the review request
        #  9. Fetch file attachment
        # 10. Fetch review request draft
        # 11. Fetch file attachment
        queries = [
            {
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                'model': Profile,
                'where': Q(user=self.user),
            },
            {
                'model': ReviewRequest,
                'select_related': {'submitter', 'repository'},
                'where': (Q(local_site=None) &
                          Q(pk=str(review_request.pk))),
            },
            {
                'model': ReviewRequestDraft,
                'select_related': {'review_request'},
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 4,
                'tables': {
                    'reviews_reviewrequest_file_attachments',
                    'reviews_reviewrequest_inactive_file_attachments',
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                    'reviews_reviewrequestdraft_file_attachments'
                },
                'where': (((Q(review_request=review_request) &
                            Q(added_in_filediff__isnull=True) &
                            Q(repository__isnull=True) &
                            Q(user__isnull=True)) |
                           Q(inactive_review_request=review_request) |
                           Q(drafts=review_request_draft) |
                           Q(inactive_drafts=review_request_draft)) &
                          Q(pk=str(review_request.pk)))
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'type': 'UPDATE',
                'where': Q(pk=file_attachment.pk),
            },
            {
                'model': ReviewRequest,
                'tables': {
                    'reviews_reviewrequest',
                },
                'where': Q(id=review_request_draft.pk),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=review_request.pk),
            },
            {
                'model': ReviewRequestDraft,
                'limit': 21,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_file_attachments',
                },
                'where': Q(drafts__id=review_request_draft.pk),
            },
        ]

        with self.assertQueries(queries):
            rsp = self.api_put(
                get_draft_file_attachment_item_url(review_request,
                                                   file_attachment.pk),
                {
                    'pending_deletion': False,
                },
                expected_status=400)

        self.assertEqual(
            rsp,
            {
                'err': {
                    'code': 105,
                    'msg': 'One or more fields had errors',
                    'type': 'request-field-error',
                },
                'fields': {
                    'pending_deletion': (
                        'This can only be used to undo the pending '
                        'deletion of a file attachment. This file '
                        'attachment is not currently pending '
                        'deletion.'
                    ),
                },
                'stat': 'fail',
            })
