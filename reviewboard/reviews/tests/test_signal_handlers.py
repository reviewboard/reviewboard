"""Tests for reviewboard.reviews.signal_handlers.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
from django_assert_queries.testing import assert_queries
from django.contrib.auth.models import User
from django.db.models import Q, Value

from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.diffviewer.models.diffcommit import DiffCommit
from reviewboard.reviews.models import (Comment,
                                        FileAttachmentComment,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        StatusUpdate)
from reviewboard.reviews.signal_handlers import (
    _on_review_request_deleted,
    _on_review_request_draft_deleted)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from django_assert_queries.query_comparator import ExpectedQueries


class OnReviewRequestDraftDeletedTests(kgb.SpyAgency, TestCase):
    """Tests _on_review_request_draft_deleted() signal handler.

    Version Added:
        6.0
    """

    fixtures = ['test_scmtools', 'test_users']

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()
        self.review_request = self.create_review_request(
            create_repository=True,
            publish=True)
        self.draft = self.create_review_request_draft(self.review_request)

    def test_with_file_attachments(self) -> None:
        """Testing _on_review_request_draft_deleted deletes new and new
        revision draft file attachments
        """
        self.spy_on(_on_review_request_draft_deleted)

        review_request = self.review_request
        draft = self.draft
        changedesc = draft.changedesc

        assert draft is not None
        assert changedesc is not None

        published_file_attachment = self.create_file_attachment(
            review_request,
            caption='Published')
        new_file_attachment = self.create_file_attachment(
            review_request,
            caption='New',
            draft=True)
        new_revision_file_attachment = self.create_file_attachment(
            review_request,
            attachment_history=published_file_attachment.attachment_history,
            attachment_revision=(
                published_file_attachment.attachment_revision + 1),
            caption='New Revision',
            draft=True)

        # Clear the review request's caches so we'll re-fetch the draft.
        review_request.clear_local_caches()

        queries: ExpectedQueries = [
            {
                'model': ReviewRequestDraft.target_groups.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.target_people.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.depends_on.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_file_attachments',
                },
                'where': Q(drafts__id=1),
            },
            {
                'model': FileAttachmentHistory,
                'where': Q(id=2),
            },
            {
                'model': FileAttachmentHistory,
                'where': Q(id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_file_attachments': 'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(file_attachment__in=[new_revision_file_attachment]),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(diff_against_file_attachment__in=[
                    new_revision_file_attachment,
                ]),
            },
            {
                'model': ReviewRequest.file_attachments.through,
                'where': Q(fileattachment__in=[new_revision_file_attachment]),
            },
            {
                'model': ReviewRequest.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_revision_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(fileattachment__in=[new_revision_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_revision_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[new_file_attachment.pk]),
            },
            {
                'model': FileAttachment,
                'type': 'DELETE',
                'where': Q(id__in=[new_revision_file_attachment.pk]),
            },
            {
                'model': FileAttachmentHistory,
                'type': 'UPDATE',
                'where': Q(pk=published_file_attachment.pk),
            },
            {
                'limit': 1,
                'model': FileAttachmentHistory,
                'values_select': ('latest_revision',),
                'where': Q(pk=published_file_attachment.pk),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(file_attachment__in=[new_file_attachment]),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(diff_against_file_attachment__in=[
                    new_file_attachment,
                ]),
            },
            {
                'model': ReviewRequest.file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequest.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[published_file_attachment.pk]),
            },
            {
                'model': FileAttachment,
                'type': 'DELETE',
                'where': Q(id__in=[new_file_attachment.pk]),
            },
            {
                'model': FileAttachmentHistory,
                'type': 'UPDATE',
                'where': Q(pk=new_file_attachment.pk),
            },
            {
                'limit': 1,
                'model': FileAttachmentHistory,
                'values_select': ('latest_revision',),
                'where': Q(pk=new_file_attachment.pk),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(changedescs__id=changedesc.pk),
            },
            {
                'model': ReviewRequest.changedescs.through,
                'where': Q(changedescription__in=[changedesc]),
            },
            {
                'model': StatusUpdate,
                'where': Q(change_description__in=[changedesc]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(changedesc__in=[changedesc]),
            },
            {
                'model': ChangeDescription,
                'type': 'DELETE',
                'where': Q(id__in=[changedesc.pk]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[
                    new_file_attachment.pk,
                    published_file_attachment.pk,
                ]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'DELETE',
                'where': Q(id__in=[draft.pk]),
            },
        ]

        with assert_queries(queries):
            self.draft.delete()

        all_attachments = list(FileAttachment.objects.all())

        self.assertSpyCalled(_on_review_request_draft_deleted)
        self.assertNotIn(new_file_attachment, all_attachments)
        self.assertNotIn(new_revision_file_attachment, all_attachments)
        self.assertIn(published_file_attachment, all_attachments)

    def test_with_one_file_attachment(self) -> None:
        """Testing _on_review_request_draft_deleted deletes a new file
        attachment
        """
        self.spy_on(_on_review_request_draft_deleted)

        review_request = self.review_request
        draft = self.draft
        changedesc = draft.changedesc

        assert draft is not None
        assert changedesc is not None

        published_file_attachment = self.create_file_attachment(
            review_request,
            caption='Published')
        new_file_attachment = self.create_file_attachment(
            review_request,
            draft=True,
            caption='New')

        # Clear the review request's caches so we'll re-fetch the draft.
        review_request.clear_local_caches()

        queries: ExpectedQueries = [
            {
                'model': ReviewRequestDraft.target_groups.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.target_people.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.depends_on.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_file_attachments',
                },
                'where': Q(drafts__id=1),
            },
            {
                'model': FileAttachmentHistory,
                'where': Q(id=2),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_file_attachments': 'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(file_attachment__in=[new_file_attachment]),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(diff_against_file_attachment__in=[
                    new_file_attachment,
                ]),
            },
            {
                'model': ReviewRequest.file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequest.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[new_file_attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[published_file_attachment.pk]),
            },
            {
                'model': FileAttachment,
                'type': 'DELETE',
                'where': Q(id__in=[new_file_attachment.pk]),
            },
            {
                'model': FileAttachmentHistory,
                'type': 'UPDATE',
                'where': Q(pk=new_file_attachment.pk),
            },
            {
                'limit': 1,
                'model': FileAttachmentHistory,
                'values_select': ('latest_revision',),
                'where': Q(pk=new_file_attachment.pk),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(changedescs__id=changedesc.pk),
            },
            {
                'model': ReviewRequest.changedescs.through,
                'where': Q(changedescription__in=[changedesc]),
            },
            {
                'model': StatusUpdate,
                'where': Q(change_description__in=[changedesc]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(changedesc__in=[changedesc]),
            },
            {
                'model': ChangeDescription,
                'type': 'DELETE',
                'where': Q(id__in=[changedesc.pk]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[published_file_attachment.pk]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'DELETE',
                'where': Q(id__in=[draft.pk]),
            },
        ]

        with assert_queries(queries, with_tracebacks=True):
            draft.delete()

        all_attachments = list(FileAttachment.objects.all())

        self.assertSpyCalled(_on_review_request_draft_deleted)
        self.assertNotIn(new_file_attachment, all_attachments)
        self.assertIn(published_file_attachment, all_attachments)

    def test_with_no_file_attachments(self) -> None:
        """Testing _on_review_request_draft_deleted when there's no
        draft file attachments on the review request
        """
        self.spy_on(_on_review_request_draft_deleted)

        # 13 queries:
        #
        #   1-7. Fetch review request draft info and relations
        #  8-12. Delete the change description
        #    13. Delete the review request draft
        with self.assertNumQueries(13):
            self.draft.delete()

        self.assertSpyCalled(_on_review_request_draft_deleted)

    def test_with_change_description(self) -> None:
        """Testing _on_review_request_draft_deleted with a change description
        """
        self.spy_on(_on_review_request_draft_deleted)
        changedesc = ChangeDescription.objects.create(
            user=User.objects.get(username='doc'),
            public=False,
            text='x')

        self.draft.changedesc = changedesc
        self.draft.save()

        # 13 queries:
        #
        #  1-7. Fetch review request draft info and relations
        # 8-12. Delete the change description
        #   13. Delete the review request draft
        with self.assertNumQueries(13):
            self.draft.delete()

        self.assertNotIn(changedesc, ChangeDescription.objects.all())

    def test_with_diff_and_diff_file_attachment(self) -> None:
        """Testing _on_review_request_draft_deleted with a diff and diff file
        attachment
        """
        self.spy_on(_on_review_request_draft_deleted)

        review_request = self.review_request
        draft = self.draft
        changedesc = draft.changedesc

        assert draft is not None
        assert changedesc is not None

        diffset = self.create_diffset(
            repository=review_request.repository)
        draft.diffset = diffset
        draft.save(update_fields=('diffset',))

        filediff = self.create_filediff(diffset)
        attachment = self.create_diff_file_attachment(filediff)

        # Clear the review request's caches so we'll re-fetch the draft.
        review_request.clear_local_caches()

        queries: ExpectedQueries = [
            {
                'model': ReviewRequestDraft.target_groups.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.target_people.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_screenshots.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'model': ReviewRequestDraft.depends_on.through,
                'where': Q(reviewrequestdraft__in=[draft]),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_file_attachments',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_file_attachments': 'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_file_attachments',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(changedescs__id=changedesc.pk),
            },
            {
                'model': ReviewRequest.changedescs.through,
                'where': Q(changedescription__in=[changedesc]),
            },
            {
                'model': StatusUpdate,
                'where': Q(change_description__in=[changedesc]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(changedesc__in=[changedesc]),
            },
            {
                'model': ChangeDescription,
                'type': 'DELETE',
                'where': Q(id__in=[changedesc.pk]),
            },
            {
                'model': DiffCommit,
                'where': Q(diffset__in=[diffset]),
            },
            {
                'model': FileDiff,
                'where': Q(diffset__in=[diffset]),
            },
            {
                'model': FileAttachment,
                'where': Q(added_in_filediff__in=[filediff]),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(file_attachment__in=[attachment]),
            },
            {
                'model': FileAttachmentComment,
                'where': Q(diff_against_file_attachment__in=[attachment]),
            },
            {
                'model': ReviewRequest.file_attachments.through,
                'where': Q(fileattachment__in=[attachment]),
            },
            {
                'model': ReviewRequest.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[attachment]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'where': Q(fileattachment__in=[attachment]),
            },
            {
                'model': ReviewRequestDraft.inactive_file_attachments.through,
                'where': Q(fileattachment__in=[attachment]),
            },
            {
                'model': Comment,
                'where': Q(filediff__in=[filediff]),
            },
            {
                'model': Comment,
                'where': Q(interfilediff__in=[filediff]),
            },
            {
                'model': Review,
                'where': Q(reviewed_diffset__in=[diffset]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'UPDATE',
                'where': Q(diffset__in=[diffset]),
            },
            {
                'model': FileDiff,
                'type': 'DELETE',
                'where': Q(id__in=[filediff.pk]),
            },
            {
                'model': ReviewRequest.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[attachment.pk]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[attachment.pk]),
            },
            {
                'model': DiffSet,
                'type': 'DELETE',
                'where': Q(id__in=[diffset.pk]),
            },
            {
                'model': FileAttachment,
                'type': 'DELETE',
                'where': Q(id__in=[attachment.pk]),
            },
            {
                'model': ReviewRequestDraft.file_attachments.through,
                'type': 'DELETE',
                'where': Q(id__in=[attachment.pk]),
            },
            {
                'model': ReviewRequestDraft,
                'type': 'DELETE',
                'where': Q(id__in=[draft.pk]),
            },
        ]

        with assert_queries(queries):
            draft.delete()

        self.assertNotIn(attachment, FileAttachment.objects.all())
        self.assertNotIn(filediff, FileDiff.objects.all())
        self.assertNotIn(diffset, DiffSet.objects.all())

    def test_handler_does_not_delete_published_data(self) -> None:
        """Testing that _on_review_request_draft_deleted running after a draft
        publish does not delete data that is now part of the review request
        """
        self.spy_on(_on_review_request_draft_deleted)

        user = User.objects.get(username='doc')

        diffset = self.create_diffset(
            repository=self.review_request.repository)
        self.draft.diffset = diffset

        changedesc = ChangeDescription.objects.create(
            user=user,
            public=False,
            text='x')
        self.draft.changedesc = changedesc

        attachment = self.create_file_attachment(self.review_request,
                                                 draft=True)

        self.draft.save()

        self.draft.target_people.add(user)
        self.review_request.publish(user)

        self.assertIn(diffset, DiffSet.objects.all())
        self.assertIn(changedesc, ChangeDescription.objects.all())
        self.assertTrue(attachment, FileAttachment.objects.all())


class OnReviewRequestDeletedTests(kgb.SpyAgency, TestCase):
    """Tests for the _on_review_request_deleted signal handler.

    Version Added:
        7.0
    """

    fixtures = ['test_scmtools', 'test_users']

    def test_cleans_up_related_changedescs(self) -> None:
        """Testing _on_review_request_deleted deletes related ChangeDescription
        objects
        """
        self.spy_on(_on_review_request_deleted)

        review_request = self.create_review_request(
            publish=True)

        c = ChangeDescription.objects.create(
            user=User.objects.get(username='doc'),
            public=True,
            text='x')
        review_request.changedescs.add(c)

        self.assertEqual(ChangeDescription.objects.count(), 1)

        # 36 queries:
        #
        #  1-11. Update profiles and counts.
        # 12-29. Fetch review request and related object data.
        # 30-31. Delete change description and relation.
        # 32-35. Delete other related data.
        #    36. Delete review request.
        with self.assertNumQueries(36):
            review_request.delete()

        self.assertSpyCalled(_on_review_request_deleted)
        self.assertEqual(ChangeDescription.objects.count(), 0)

    def test_cleans_up_related_diffset_history(self) -> None:
        """Testing _on_review_request_deleted deletes related DiffSetHistory
        object
        """
        self.spy_on(_on_review_request_deleted)

        review_request = self.create_review_request(
            create_repository=True,
            publish=True)

        self.create_diffset(review_request)
        self.create_diffset(review_request, revision=2)

        self.assertEqual(DiffSetHistory.objects.count(), 1)

        # 35 queries:
        #
        #  1-11. Update profiles and counts.
        # 12-31. Fetch review request and related object data.
        #    32. Set diffset_history relation to NULL.
        #    33. Delete diffset history.
        #    34. Delete diffsets.
        #    35. Delete review request.
        with self.assertNumQueries(35):
            review_request.delete()

        self.assertSpyCalled(_on_review_request_deleted)
        self.assertEqual(DiffSetHistory.objects.count(), 0)

    def test_cleans_up_related_file_attachments(self) -> None:
        """Testing _on_review_request_deleted deletes related file attachments
        """
        self.spy_on(_on_review_request_deleted)

        review_request = self.create_review_request(
            create_repository=True,
            publish=True)

        self.create_file_attachment(review_request, active=True)
        self.create_file_attachment(review_request, active=False)

        self.assertEqual(FileAttachment.objects.count(), 2)
        self.assertEqual(FileAttachmentHistory.objects.count(), 2)
        self.assertEqual(review_request.file_attachments_count, 1)
        self.assertEqual(review_request.inactive_file_attachments_count, 1)

        # 51 queries:
        #
        #  1-11. Update profiles and counts.
        # 12-35. Fetch review request and related object data.
        # 36-39. Remove file attachment and file attachment history relations.
        #    40. Delete file attachments.
        # 41-44. Perform file attachment relation bookkeeping.
        # 45-47. Delete diffset history.
        # 48-50. Clean up file attachment relations.
        #    51. Delete review request.
        with self.assertNumQueries(51):
            review_request.delete()

        self.assertSpyCalled(_on_review_request_deleted)
        self.assertEqual(FileAttachment.objects.count(), 0)
        self.assertEqual(FileAttachmentHistory.objects.count(), 0)

    def test_cleans_up_related_screenshots(self) -> None:
        """Testing _on_review_request_deleted deletes related screenshots"""
        self.spy_on(_on_review_request_deleted)

        review_request = self.create_review_request(
            create_repository=True,
            publish=True)

        self.create_screenshot(review_request, active=True)
        self.create_screenshot(review_request, active=False)

        self.assertEqual(Screenshot.objects.count(), 2)
        self.assertEqual(review_request.screenshots_count, 1)
        self.assertEqual(review_request.inactive_screenshots_count, 1)

        # 51 queries:
        #
        #  1-11. Update profiles and counts.
        # 12-35. Fetch review request and related object data.
        # 36-41. Remove screenshot relations.
        #    42. Delete screenshots.
        # 43-45. Delete diffset history.
        # 46-47. Clean up screenshot relations..
        #    48. Delete review request.
        with self.assertNumQueries(48):
            review_request.delete()

        self.assertSpyCalled(_on_review_request_deleted)
        self.assertEqual(Screenshot.objects.count(), 0)
