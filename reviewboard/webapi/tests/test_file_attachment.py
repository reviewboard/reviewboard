from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Q
from djblets.webapi.errors import INVALID_FORM_DATA, PERMISSION_DENIED

from reviewboard.accounts.models import Profile
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.reviews.models import (
    ReviewRequest,
    ReviewRequestDraft)
from reviewboard.reviews.models.review_request import FileAttachmentState
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (file_attachment_item_mimetype,
                                                file_attachment_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_file_attachment_item_url,
                                           get_file_attachment_list_url)


class ResourceListTests(ReviewRequestChildListMixin,
                        BaseWebAPITestCase,
                        ExtraDataListMixin,
                        metaclass=BasicTestsMetaclass):
    """Testing the FileAttachmentResource list APIs."""
    fixtures = ['test_users']
    basic_get_fixtures = ['test_scmtools']
    sample_api_url = 'review-requests/<id>/file-attachments/'
    resource = resources.file_attachment

    def setup_review_request_child_test(self, review_request):
        return (get_file_attachment_list_url(review_request),
                file_attachment_list_mimetype)

    def setup_http_not_allowed_item_test(self, user):
        review_request = self.create_review_request(
            submitter=user,
            publish=True)

        return get_file_attachment_list_url(review_request)

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['extra_data'], attachment.extra_data)
        self.assertEqual(item_rsp['filename'], attachment.filename)
        self.assertEqual(item_rsp['revision'], attachment.attachment_revision)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        review_request = self.create_review_request(
            create_repository=True,
            with_local_site=with_local_site,
            submitter=user)

        if populate_items:
            # This is the file attachment that should be returned.
            items = [
                self.create_file_attachment(review_request,
                                            orig_filename='logo1.png'),
            ]

            # This attachment shouldn't be shown in the results. It represents
            # a file to be shown in the diff viewer.
            self.create_file_attachment(review_request,
                                        orig_filename='logo2.png',
                                        repo_path='/logo.png',
                                        repo_revision='123',
                                        repository=review_request.repository)

            # This attachment shouldn't be shown either, for the same
            # reasons.
            diffset = self.create_diffset(review_request)
            filediff = self.create_filediff(diffset,
                                            source_file='/logo3.png',
                                            dest_file='/logo3.png',
                                            source_revision='123',
                                            dest_detail='124')
            self.create_file_attachment(review_request,
                                        orig_filename='logo3.png',
                                        added_in_filediff=filediff)
        else:
            items = []

        return (get_file_attachment_list_url(review_request, local_site_name),
                file_attachment_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        return (get_file_attachment_list_url(review_request, local_site_name),
                file_attachment_item_mimetype,
                {'path': open(self.get_sample_image_filename(), 'rb')},
                [review_request])

    def check_post_result(self, user, rsp, review_request):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn('file_attachment', rsp)
        item_rsp = rsp['file_attachment']

        attachment = FileAttachment.objects.get(pk=item_rsp['id'])
        self.assertIn(attachment, draft.file_attachments.all())
        self.assertNotIn(attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, attachment)

    def test_post_not_owner(self):
        """Testing the POST review-requests/<id>/file-attachments/ API
        without owner
        """
        review_request = self.create_review_request()
        self.assertNotEqual(review_request.submitter, self.user)

        with open(self.get_sample_image_filename(), 'rb') as f:
            self.assertTrue(f)
            rsp = self.api_post(
                get_file_attachment_list_url(review_request),
                {
                    'caption': 'logo',
                    'path': f,
                },
                expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_post_with_attachment_history_id(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a
        file attachment history
        """
        review_request = self.create_review_request(
            submitter=self.user, publish=True, target_people=[self.user])
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request.file_attachment_histories.add(history)

        self.assertEqual(history.latest_revision, 0)

        with open(self.get_sample_image_filename(), 'rb') as f:
            self.assertTrue(f)
            rsp = self.api_post(
                get_file_attachment_list_url(review_request),
                {
                    'path': f,
                    'attachment_history': history.pk,
                },
                expected_mimetype=file_attachment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertEqual(rsp['file_attachment']['attachment_history_id'],
                             history.pk)

            history = FileAttachmentHistory.objects.get(pk=history.pk)
            self.assertEqual(history.latest_revision, 1)

            review_request.get_draft().publish()

            # Add a second revision
            f.seek(0)
            rsp = self.api_post(
                get_file_attachment_list_url(review_request),
                {
                    'path': f,
                    'attachment_history': history.pk,
                },
                expected_mimetype=file_attachment_item_mimetype)

            self.assertEqual(rsp['stat'], 'ok')
            self.assertEqual(rsp['file_attachment']['attachment_history_id'],
                             history.pk)

            history = FileAttachmentHistory.objects.get(pk=history.pk)
            self.assertEqual(history.latest_revision, 2)

    def test_post_with_attachment_history_id_wrong_review_request(self):
        """Testing the POST review-requests/<id>/file-attachments/ API with a
        file attachment history belonging to a different reiew request
        """
        review_request_1 = self.create_review_request(submitter=self.user,
                                                      publish=True)
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request_1.file_attachment_histories.add(history)

        review_request_2 = self.create_review_request(submitter=self.user,
                                                      publish=True)

        self.assertEqual(history.latest_revision, 0)

        with open(self.get_sample_image_filename(), 'rb') as f:
            self.assertTrue(f)
            rsp = self.api_post(
                get_file_attachment_list_url(review_request_2),
                {
                    'path': f,
                    'attachment_history': history.pk,
                },
                expected_status=400)

            self.assertEqual(rsp['stat'], 'fail')
            self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)

            history = FileAttachmentHistory.objects.get(pk=history.pk)
            self.assertEqual(history.latest_revision, 0)


class ResourceItemTests(ReviewRequestChildItemMixin,
                        BaseWebAPITestCase,
                        ExtraDataItemMixin,
                        metaclass=BasicTestsMetaclass):
    """Testing the FileAttachmentResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/file-attachments/<id>/'
    resource = resources.file_attachment

    def setup_review_request_child_test(self, review_request):
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment),
                file_attachment_item_mimetype)

    def compare_item(self, item_rsp, attachment):
        self.assertEqual(item_rsp['id'], attachment.pk)
        self.assertEqual(item_rsp['extra_data'], attachment.extra_data)
        self.assertEqual(item_rsp['filename'], attachment.filename)
        self.assertEqual(item_rsp['revision'], attachment.attachment_revision)
        self.assertEqual(item_rsp['absolute_url'],
                         attachment.get_absolute_url())

    def setup_http_not_allowed_list_test(self, user):
        review_request = self.create_review_request(
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return get_file_attachment_item_url(file_attachment)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                [review_request, file_attachment])

    def check_delete_result(self, user, review_request, file_attachment):
        draft = review_request.get_draft()
        self.assertIsNotNone(draft)
        self.assertIn(file_attachment, draft.inactive_file_attachments.all())
        self.assertNotIn(file_attachment, draft.file_attachments.all())
        self.assertIn(file_attachment, review_request.file_attachments.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                file_attachment_item_mimetype,
                file_attachment)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/file-attachments/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)

        self._testHttpCaching(get_file_attachment_item_url(file_attachment),
                              check_etags=True)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            submitter=user)
        file_attachment = self.create_file_attachment(review_request)

        return (get_file_attachment_item_url(file_attachment, local_site_name),
                file_attachment_item_mimetype,
                {'caption': 'My new caption'},
                file_attachment,
                [review_request])

    def check_put_result(self, user, item_rsp, file_attachment,
                         review_request):
        file_attachment = FileAttachment.objects.get(pk=file_attachment.pk)
        self.assertEqual(item_rsp['id'], file_attachment.pk)
        self.assertEqual(file_attachment.draft_caption, 'My new caption')

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        self.assertIn(file_attachment, draft.file_attachments.all())
        self.assertIn(file_attachment, review_request.file_attachments.all())
        self.compare_item(item_rsp, file_attachment)

    def test_put_with_caption(self) -> None:
        """Testing the PUT review-requests/<id>/draft/file-attachments/<id>/
        with setting a new caption and when a draft already exists
        """
        review_request = self.create_review_request(submitter=self.user)
        file_attachment = self.create_file_attachment(review_request)
        review_request_draft = self.create_review_request_draft(review_request)

        # 12 queries:
        #
        #  1. Fetch review request
        #  2. Fetch request user
        #  3. Fetch request user's Profile
        #  4. Fetch review request
        #  5. Fetch review request draft
        #  6. Fetch  file attachments
        #  7. Fetch review request draft
        #  8. Save any file attachment updates
        #  9. Save the review request draft last_updated field
        # 10. Fetch review request
        # 11. Fetch review request
        # 12. Fetch review request
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
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
                get_file_attachment_item_url(file_attachment),
                {
                    'caption': 'Updated caption',
                },
                expected_mimetype=file_attachment_item_mimetype)

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
        #  1. Fetch review request
        #  2. Fetch request user
        #  3. Fetch request user's Profile
        #  4. Fetch review request
        #  5. Fetch review request draft
        #  6. Fetch file attachment
        #  7. Fetch review request draft
        #  8. Save any file attachment updates
        #  9. Fetch review request when getting file attachment state
        # 10. Fetch active file attachments when getting file attachment state
        # 11. Fetch review request draft when getting file attachment state
        # 12. Fetch inactive draft file attachments when getting file
        #     attachment state
        # 13. Fetch file attachment IDs matching history ID
        # 14. Fetch inactive draft file attachments
        # 15. Remove file attachment from inactive draft file attachments
        # 16. Update inactive draft file attachments count
        # 17. Fetch inactive draft file attachments count
        # 18. Fetch active draft file attachments
        # 19. Add file attachment to active draft file attachments
        # 20. Update active draft file attachments count
        # 21. Fetch active draft file attachments count
        # 22. Save the review request draft last_updated field
        # 23. Fetch review request
        # 24. Fetch review request
        # 25. Fetch review request
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
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
                get_file_attachment_item_url(file_attachment),
                {
                    'pending_deletion': False,
                },
                expected_mimetype=file_attachment_item_mimetype)

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
        #  1. Fetch review request
        #  2. Fetch request user
        #  3. Fetch request user's Profile
        #  4. Fetch review request
        #  5. Fetch review request draft
        #  6. Fetch file attachment
        #  7. Fetch review request draft
        #  8. Save any file attachment updates
        #  9. Fetch review request when getting file attachment state
        # 10. Fetch active file attachments when getting file attachment state
        # 11. Fetch review request draft when getting file attachment state
        # 12. Fetch inactive draft file attachments when getting file
        #     attachment state
        # 13. Fetch file attachment IDs matching history ID
        # 14. Fetch inactive draft file attachments
        # 15. Remove file attachment from inactive draft file attachments
        # 16. Update inactive draft file attachments count
        # 17. Fetch inactive draft file attachments count
        # 18. Fetch active draft file attachments
        # 19. Add file attachment to active draft file attachments
        # 20. Update active draft file attachments count
        # 21. Fetch active draft file attachments count
        # 22. Save the review request draft last_updated field
        # 23. Fetch review request
        # 24. Fetch review request
        # 25. Fetch review request
        queries = [
            {
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(file_attachments__id=file_attachment.pk),
            },
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
                'where': Q(id__in=[file_attachment_2.pk, file_attachment.pk]),
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
                get_file_attachment_item_url(file_attachment),
                {
                    'pending_deletion': False,
                },
                expected_mimetype=file_attachment_item_mimetype)

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
        self.create_review_request_draft(review_request)

        rsp = self.api_put(
            get_file_attachment_item_url(file_attachment),
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
