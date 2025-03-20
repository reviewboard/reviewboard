"""Unit tests for reviewboard.reviews.views.ReviewRequestDetailView."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission, User
from django.db.models import Q, Value
from django.test.html import parse_html
from djblets.extensions.hooks import TemplateHook
from djblets.extensions.models import RegisteredExtension
from djblets.siteconfig.models import SiteConfiguration
from kgb import SpyAgency

from reviewboard.accounts.models import (ReviewRequestVisit,
                                         Profile,
                                         Trophy)
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.extensions.base import Extension, get_extension_manager
from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.reviews.detail import InitialStatusUpdatesEntry, ReviewEntry
from reviewboard.reviews.fields import get_review_request_fieldsets
from reviewboard.reviews.models import (Comment,
                                        GeneralComment,
                                        Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        StatusUpdate)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.db.query_comparator import ExpectedQueries


class ReviewRequestDetailViewTests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.views.ReviewRequestDetailView."""

    fixtures = ['test_users', 'test_scmtools', 'test_site']

    def test_get(self) -> None:
        """Testing ReviewRequestDetailView.get"""
        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='foo')
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        doc = User.objects.get(username='doc')

        queries: ExpectedQueries = [
            {
                'model': SiteConfiguration,
                'where': Q(site_id=1)
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'repository',
                    'submitter',
                },
                'where': Q(pk=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'model': Review,
                'order_by': ('-timestamp',),
                'select_related': {'user'},
                'where': (
                    Q(review_request=review_request) &
                    Q(public=True)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(public=True)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': StatusUpdate,
                'order_by': ('summary',),
                'where': Q(review_request=review_request),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(depends_on__id=1),
            },
            {
                'limit': 1,
                'model': Review,
                'order_by': ('timestamp',),
                'where': (
                    Q(review_request=review_request) &
                    Q(public=True)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'limit': 1,
                'model': ChangeDescription,
                'num_joins': 1,
                'order_by': ('timestamp',),
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'limit': 1,
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': Trophy,
                'where': Q(review_request=review_request),
            },
            {
                'model': Profile,
                'where': Q(user=doc),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(blocks__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/r/%d/' % review_request.id)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['review_request'].pk,
                         review_request.pk)

    def test_context(self) -> None:
        """Testing ReviewRequestDetailView context variables"""
        # Make sure this request is made while logged in, to catch the
        # login-only pieces of the review_detail view.
        self.client.login(username='admin', password='admin')

        admin = User.objects.get(username='admin')
        doc = User.objects.get(username='doc')

        # Prime the caches.
        admin.get_profile()
        doc.get_profile()

        username = 'admin'
        summary = 'This is a test summary'
        description = 'This is my description'
        testing_done = 'Some testing'

        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='foo')
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(
            publish=True,
            repository=repository,
            submitter=username,
            summary=summary,
            description=description,
            testing_done=testing_done)

        queries: ExpectedQueries = [
            {
                'model': SiteConfiguration,
                'where': Q(site_id=1)
            },
            {
                'model': User,
                'where': Q(pk=admin.pk),
            },
            {
                'model': Profile,
                'where': Q(user=admin),
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'repository',
                    'submitter',
                },
                'where': Q(pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=admin)
                ),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                'model': Review,
                'order_by': ('-timestamp',),
                'select_related': {'user'},
                'where': (
                    Q(review_request=review_request) &
                    (Q(public=True) |
                     Q(user_id=admin.pk))
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(public=True)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': StatusUpdate,
                'order_by': ('summary',),
                'where': Q(review_request=review_request),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(depends_on__id=1),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=admin.pk) &
                    Q(pk=1)
                ),
            },
            {
                'limit': 1,
                'model': Review,
                'order_by': ('timestamp',),
                'where': (
                    Q(review_request=review_request) &
                    Q(public=True)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'limit': 1,
                'model': ChangeDescription,
                'num_joins': 1,
                'order_by': ('timestamp',),
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': Review,
                'order_by': ('timestamp',),
                'where': (
                    Q(base_reply_to__isnull=True) &
                    Q(public=False) &
                    Q(review_request=review_request) &
                    Q(user=admin)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'limit': 1,
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=admin)
                ),
            },
            {
                'model': Trophy,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=admin.pk) &
                    Q(pk=1)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': Profile,
                'where': Q(user=admin),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(blocks__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/r/%s/' % review_request.pk)

        self.assertEqual(response.status_code, 200)

        review_request = response.context['review_request']
        self.assertEqual(review_request.submitter.username, username)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)
        self.assertEqual(review_request.testing_done, testing_done)
        self.assertEqual(review_request.pk, review_request.pk)

    def test_diff_comment_ordering(self) -> None:
        """Testing ReviewRequestDetailView and ordering of diff comments on a
        review
        """
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'

        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='foo')
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the users who will be commenting.
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        # Create the master review.
        main_review = self.create_review(review_request, user=user1)
        main_comment = self.create_diff_comment(main_review, filediff,
                                                text=comment_text_1)
        main_review.publish()

        # First reply
        reply1 = self.create_reply(
            main_review,
            user=user1,
            timestamp=(main_review.timestamp + timedelta(days=1)))
        self.create_diff_comment(reply1, filediff, text=comment_text_2,
                                 reply_to=main_comment)

        # Second reply
        reply2 = self.create_reply(
            main_review,
            user=user2,
            timestamp=(main_review.timestamp + timedelta(days=2)))
        self.create_diff_comment(reply2, filediff, text=comment_text_3,
                                 reply_to=main_comment)

        # Publish them out of order.
        reply2.publish()
        reply1.publish()

        # Make sure they published in the order expected.
        self.assertTrue(reply1.timestamp > reply2.timestamp)

        # Make sure they're looked up in the order expected.
        comments = list(
            Comment.objects
            .filter(review__review_request=review_request)
            .order_by('timestamp')
        )
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_3)
        self.assertEqual(comments[2].text, comment_text_2)

        # Prime the caches.
        user1.get_profile()
        user2.get_profile()

        # Now figure out the order on the page.
        queries: ExpectedQueries = [
            {
                'model': SiteConfiguration,
                'where': Q(site_id=1)
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'repository',
                    'submitter',
                },
                'where': Q(pk=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'model': Review,
                'order_by': ('-timestamp',),
                'select_related': {'user'},
                'where': (
                    Q(review_request=review_request) &
                    Q(public=True)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(public=True)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': FileDiff,
                'where': Q(diffset__in=[diffset]),
            },
            {
                'model': StatusUpdate,
                'order_by': ('summary',),
                'where': Q(review_request=review_request),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(depends_on__id=1),
            },
            {
                'model': Review.general_comments.through,
                'order_by': ('generalcomment__timestamp',),
                'select_related': True,
                'where': Q(review__in=[2, 3, 1]),
            },
            {
                'model': Review.comments.through,
                'order_by': (
                    'comment__filediff',
                    'comment__first_line',
                    'comment__timestamp',
                ),
                'select_related': True,
                'where': Q(review__in=[2, 3, 1]),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': Trophy,
                'where': Q(review_request=review_request),
            },
            {
                'model': Profile,
                'where': Q(user=user1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(blocks__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest_target_groups',
                },
                'where': Q(review_requests__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequest_target_people',
                },
                'where': Q(directed_review_requests__id=1),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/r/%d/' % review_request.pk)

        self.assertEqual(response.status_code, 200)

        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)
        comments = entry.comments['diff_comments']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].text, comment_text_1)

        replies = comments[0].public_replies()
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0].text, comment_text_3)
        self.assertEqual(replies[1].text, comment_text_2)

    def test_general_comment_ordering(self) -> None:
        """Testing ReviewRequestDetailView and ordering of general comments on
        a review
        """
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        # Create the users who will be commenting.
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        # Create the master review.
        main_review = self.create_review(review_request, user=user1)
        main_comment = self.create_general_comment(main_review,
                                                   text=comment_text_1)
        main_review.publish()

        # First reply
        reply1 = self.create_reply(
            main_review,
            user=user1,
            timestamp=(main_review.timestamp + timedelta(days=1)))
        self.create_general_comment(reply1, text=comment_text_2,
                                    reply_to=main_comment)

        # Second reply
        reply2 = self.create_reply(
            main_review,
            user=user2,
            timestamp=(main_review.timestamp + timedelta(days=2)))
        self.create_general_comment(reply2, text=comment_text_3,
                                    reply_to=main_comment)

        # Publish them out of order.
        reply2.publish()
        reply1.publish()

        # Make sure they published in the order expected.
        self.assertTrue(reply1.timestamp > reply2.timestamp)

        # Make sure they're looked up in the order expected.
        comments = list(
            GeneralComment.objects
            .filter(review__review_request=review_request)
            .order_by('timestamp')
        )
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_3)
        self.assertEqual(comments[2].text, comment_text_2)

    def test_file_attachments_visibility(self) -> None:
        """Testing ReviewRequestDetailView default visibility of file
        attachments
        """
        caption_1 = 'File Attachment 1'
        caption_2 = 'File Attachment 2'
        caption_3 = 'File Attachment 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')

        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='foo')
        repository = self.create_repository(hosting_account=account)

        review_request = self.create_review_request(repository=repository)

        # Add two file attachments. One active, one inactive.
        file_attachment1 = self.create_file_attachment(
            review_request,
            caption=caption_1)
        file_attachment2 = self.create_file_attachment(
            review_request,
            caption=caption_2,
            active=False)
        review_request.publish(user1)

        # Create a third file attachment on a draft.
        file_attachment3 = self.create_file_attachment(
            review_request,
            caption=caption_3,
            draft=True)

        # Create the review with comments for each screenshot.
        review = Review.objects.create(review_request=review_request,
                                       user=user1)
        review.file_attachment_comments.create(
            file_attachment=file_attachment1,
            text=comment_text_1)
        review.file_attachment_comments.create(
            file_attachment=file_attachment2,
            text=comment_text_2)
        review.publish()

        self.client.login(username='doc', password='doc')

        # Prime the caches.
        user1.get_profile()

        # Check that we can find all the objects we expect on the page.
        queries: ExpectedQueries = [
            {
                'model': SiteConfiguration,
                'where': Q(site_id=1)
            },
            {
                'model': User,
                'where': Q(pk=user1.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user1),
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'repository',
                    'submitter',
                },
                'where': Q(pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                'model': Review,
                'order_by': ('-timestamp',),
                'select_related': {'user'},
                'where': (
                    Q(review_request=review_request) &
                    (Q(public=True) |
                     Q(user_id=user1.pk))
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(public=True)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': StatusUpdate,
                'order_by': ('summary',),
                'where': Q(review_request=review_request),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(depends_on__id=1),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=user1.pk) &
                    Q(pk=1)
                ),
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
                'where': Q(id=1),
            },
            {
                'model': FileAttachmentHistory,
                'where': Q(id=3),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_inactive_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                },
                'where': Q(inactive_drafts__id=1),
            },
            {
                'model': Review.general_comments.through,
                'order_by': ('generalcomment__timestamp',),
                'select_related': True,
                'where': Q(review__in=[1]),
            },
            {
                'model': Review.file_attachment_comments.through,
                'order_by': ('fileattachmentcomment__timestamp',),
                'select_related': True,
                'where': Q(review__in=[1]),
            },
            {
                'model': Review.comments.through,
                'order_by': (
                    'comment__filediff',
                    'comment__first_line',
                    'comment__timestamp',
                ),
                'select_related': True,
                'where': Q(review__in=[1]),
            },
            {
                'model': Review,
                'order_by': ('timestamp',),
                'where': (
                    Q(base_reply_to__isnull=True) &
                    Q(public=False) &
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'join_types': {
                    'attachments_fileattachment': 'INNER JOIN',
                },
                'model': FileAttachmentHistory,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'attachments_fileattachmenthistory',
                },
                'values_select': ('id', 'latest_revision'),
                'where': Q(file_attachments__in=[
                    file_attachment1,
                    file_attachment3,
                ]),
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
                'join_types': {
                    'reviews_reviewrequest_inactive_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequest_inactive_file_attachments',
                },
                'where': Q(inactive_review_request__id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
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
                    'reviews_reviewrequestdraft_inactive_file_attachments':
                        'INNER JOIN',
                },
                'model': FileAttachment,
                'num_joins': 1,
                'tables': {
                    'attachments_fileattachment',
                    'reviews_reviewrequestdraft_inactive_file_attachments',
                },
                'where': Q(inactive_drafts__id=1),
            },
            {
                'model': HostingServiceAccount,
                'where': Q(id=1),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'limit': 1,
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'model': Trophy,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=user1.pk) &
                    Q(pk=1)
                ),
            },
            {
                'join_types': {
                    'auth_user_user_permissions': 'INNER JOIN',
                    'django_content_type': 'INNER JOIN',
                },
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': (
                    'content_type__app_label',
                    'codename',
                ),
                'where': Q(user__id=user1.pk),
            },
            {
                'join_types': {
                    'auth_group': 'INNER JOIN',
                    'auth_group_permissions': 'INNER JOIN',
                    'auth_user_groups': 'INNER JOIN',
                    'django_content_type': 'INNER JOIN',
                },
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': (
                    'content_type__app_label',
                    'codename',
                ),
                'where': Q(group__user=user1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': Profile,
                'where': Q(user=user1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequestdraft_depends_on',
                },
                'where': Q(draft_blocks__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequestdraft_target_groups',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequestdraft_target_people',
                },
                'where': Q(directed_drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequestdraft_target_groups',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequestdraft_target_people',
                },
                'where': Q(directed_drafts__id=1),
            },
            {
                'model': ChangeDescription,
                'where': Q(id=1),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/r/%d/' % review_request.pk)

        self.assertEqual(response.status_code, 200)

        file_attachments = response.context['file_attachments']
        self.assertEqual(len(file_attachments), 2)
        self.assertEqual(file_attachments[0].caption, caption_1)
        self.assertEqual(file_attachments[1].caption, caption_3)

        # Make sure that other users won't see the draft one.
        self.client.logout()
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        file_attachments = response.context['file_attachments']
        self.assertEqual(len(file_attachments), 1)
        self.assertEqual(file_attachments[0].caption, caption_1)

        # Make sure we loaded the reviews and all data correctly.
        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)

        comments = entry.comments['file_attachment_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_screenshots_visibility(self):
        """Testing ReviewRequestDetailView default visibility of screenshots"""
        caption_1 = 'Screenshot 1'
        caption_2 = 'Screenshot 2'
        caption_3 = 'Screenshot 3'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'

        user1 = User.objects.get(username='doc')

        review_request = self.create_review_request()

        # Add two screenshots. One active, one inactive.
        screenshot1 = self.create_screenshot(review_request, caption=caption_1)
        screenshot2 = self.create_screenshot(review_request, caption=caption_2,
                                             active=False)
        review_request.publish(user1)

        # Add a third screenshot on a draft.
        self.create_screenshot(review_request, caption=caption_3, draft=True)

        # Create the review with comments for each screenshot.
        user1 = User.objects.get(username='doc')
        review = Review.objects.create(review_request=review_request,
                                       user=user1)
        review.screenshot_comments.create(screenshot=screenshot1,
                                          text=comment_text_1,
                                          x=10,
                                          y=10,
                                          w=20,
                                          h=20)
        review.screenshot_comments.create(screenshot=screenshot2,
                                          text=comment_text_2,
                                          x=0,
                                          y=0,
                                          w=10,
                                          h=10)
        review.publish()

        self.client.login(username='doc', password='doc')

        # Prime the caches.
        user1.get_profile()

        # Check that we can find all the objects we expect on the page.
        queries: ExpectedQueries = [
            {
                'model': SiteConfiguration,
                'where': Q(site_id=1)
            },
            {
                'model': User,
                'where': Q(pk=user1.pk),
            },
            {
                'model': Profile,
                'where': Q(user=user1),
            },
            {
                'model': ReviewRequest,
                'select_related': {
                    'repository',
                    'submitter',
                },
                'where': Q(pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'model': ReviewRequestVisit,
                'type': 'INSERT',
            },
            {
                'model': ReviewRequestVisit,
                'type': 'UPDATE',
                'where': Q(pk=1),
            },
            {
                'model': Review,
                'order_by': ('-timestamp',),
                'select_related': {'user'},
                'where': (
                    Q(review_request=review_request) &
                    (Q(public=True) |
                     Q(user_id=user1.pk))
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': (
                    Q(review_request__id=1) &
                    Q(public=True)
                ),
            },
            {
                'model': ReviewRequestDraft,
                'where': Q(review_request=review_request),
            },
            {
                'model': StatusUpdate,
                'order_by': ('summary',),
                'where': Q(review_request=review_request),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_depends_on',
                },
                'where': Q(depends_on__id=1),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=user1.pk) &
                    Q(pk=1)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_screenshots': 'INNER JOIN',
                },
                'model': Screenshot,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequestdraft_screenshots',
                    'reviews_screenshot',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_inactive_screenshots':
                        'INNER JOIN',
                },
                'model': Screenshot,
                'num_joins': 1,
                'tables': {
                    'reviews_screenshot',
                    'reviews_reviewrequestdraft_inactive_screenshots',
                },
                'where': Q(inactive_drafts__id=1),
            },
            {
                'model': Review.general_comments.through,
                'order_by': ('generalcomment__timestamp',),
                'select_related': True,
                'where': Q(review__in=[1]),
            },
            {
                'model': Review.screenshot_comments.through,
                'order_by': ('screenshotcomment__timestamp',),
                'select_related': True,
                'where': Q(review__in=[1]),
            },
            {
                'model': Review,
                'order_by': ('timestamp',),
                'where': (
                    Q(base_reply_to__isnull=True) &
                    Q(public=False) &
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'join_types': {
                    'reviews_reviewrequest_changedescs': 'INNER JOIN',
                },
                'model': ChangeDescription,
                'num_joins': 1,
                'tables': {
                    'changedescs_changedescription',
                    'reviews_reviewrequest_changedescs',
                },
                'where': Q(review_request__id=1),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'limit': 1,
                'model': DiffSet,
                'where': Q(history__pk=1),
            },
            {
                'model': ReviewRequestVisit,
                'where': (
                    Q(review_request=review_request) &
                    Q(user=user1)
                ),
            },
            {
                'model': Trophy,
                'where': Q(review_request=review_request),
            },
            {
                'annotations': {
                    'a': Value(1),
                },
                'join_types': {
                    'accounts_profile_starred_review_requests': 'INNER JOIN',
                },
                'limit': 1,
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'accounts_profile_starred_review_requests',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(starred_by__id=user1.pk) &
                    Q(pk=1)
                ),
            },
            {
                'join_types': {
                    'auth_user_user_permissions': 'INNER JOIN',
                    'django_content_type': 'INNER JOIN',
                },
                'model': Permission,
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'values_select': (
                    'content_type__app_label',
                    'codename',
                ),
                'where': Q(user__id=user1.pk),
            },
            {
                'join_types': {
                    'auth_group': 'INNER JOIN',
                    'auth_group_permissions': 'INNER JOIN',
                    'auth_user_groups': 'INNER JOIN',
                    'django_content_type': 'INNER JOIN',
                },
                'model': Permission,
                'num_joins': 4,
                'tables': {
                    'auth_group',
                    'auth_group_permissions',
                    'auth_permission',
                    'auth_user_groups',
                    'django_content_type',
                },
                'values_select': (
                    'content_type__app_label',
                    'codename',
                ),
                'where': Q(group__user=user1),
            },
            {
                'model': Profile,
                'where': Q(user=user1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_depends_on': 'INNER JOIN',
                },
                'model': ReviewRequest,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_reviewrequestdraft_depends_on',
                },
                'where': Q(draft_blocks__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequestdraft_target_groups',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequestdraft_target_people',
                },
                'where': Q(directed_drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_groups': 'INNER JOIN',
                },
                'model': Group,
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequestdraft_target_groups',
                },
                'where': Q(drafts__id=1),
            },
            {
                'join_types': {
                    'reviews_reviewrequestdraft_target_people': 'INNER JOIN',
                },
                'model': User,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'reviews_reviewrequestdraft_target_people',
                },
                'where': Q(directed_drafts__id=1),
            },
            {
                'model': ChangeDescription,
                'where': Q(id=1),
            },
        ]

        with self.assertQueries(queries):
            response = self.client.get('/r/%d/' % review_request.pk)

        self.assertEqual(response.status_code, 200)

        screenshots = response.context['screenshots']
        self.assertEqual(len(screenshots), 2)
        self.assertEqual(screenshots[0].caption, caption_1)
        self.assertEqual(screenshots[1].caption, caption_3)

        # Make sure that other users won't see the draft one.
        self.client.logout()
        response = self.client.get('/r/%d/' % review_request.pk)
        self.assertEqual(response.status_code, 200)

        screenshots = response.context['screenshots']
        self.assertEqual(len(screenshots), 1)
        self.assertEqual(screenshots[0].caption, caption_1)

        entries = response.context['entries']
        initial_entries = entries['initial']
        self.assertEqual(len(initial_entries), 1)
        self.assertIsInstance(initial_entries[0], InitialStatusUpdatesEntry)

        main_entries = entries['main']
        self.assertEqual(len(main_entries), 1)
        entry = main_entries[0]
        self.assertIsInstance(entry, ReviewEntry)

        # Make sure we loaded the reviews and all data correctly.
        comments = entry.comments['screenshot_comments']
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)

    def test_with_anonymous_and_requires_site_wide_login(self) -> None:
        """Testing ReviewRequestDetailView with anonymous user and site-wide
        login required
        """
        with self.siteconfig_settings({'auth_require_sitewide_login': True},
                                      reload_settings=False):
            self.create_review_request(publish=True)

            with self.assertNumQueries(0):
                response = self.client.get('/r/1/')

            self.assertEqual(response.status_code, 302)

    def test_etag_with_issues(self) -> None:
        """Testing ReviewRequestDetailView ETags with issue status toggling"""
        self.client.login(username='doc', password='doc')

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create a review.
        review = self.create_review(review_request, user=user)
        comment = self.create_diff_comment(review, filediff,
                                           issue_opened=True)
        review.publish()

        # Get the etag
        response = self.client.get(review_request.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        etag1 = response['ETag']
        self.assertNotEqual(etag1, '')

        # Change the issue status
        comment.issue_status = Comment.RESOLVED
        comment.save()

        # Check the etag again
        response = self.client.get(review_request.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        etag2 = response['ETag']
        self.assertNotEqual(etag2, '')

        # Make sure they're not equal
        self.assertNotEqual(etag1, etag2)

    def test_review_request_box_template_hooks(self) -> None:
        """Testing ReviewRequestDetailView template hooks for the review
        request box
        """
        class ContentTemplateHook(TemplateHook):
            def initialize(self, name, content):
                super(ContentTemplateHook, self).initialize(name)
                self.content = content

            def render_to_string(self, request,  context):
                return self.content

        class TestExtension(Extension):
            registration = RegisteredExtension.objects.create(
                class_name='test-extension',
                name='test-extension',
                enabled=True,
                installed=True)

        extension = TestExtension(get_extension_manager())
        review_request = self.create_review_request(publish=True)
        hooks = []

        for name in ('before-review-request-summary',
                     'review-request-summary-pre',
                     'review-request-summary-post',
                     'after-review-request-summary-post',
                     'before-review-request-fields',
                     'after-review-request-fields',
                     'before-review-request-extra-panes',
                     'review-request-extra-panes-pre',
                     'review-request-extra-panes-post',
                     'after-review-request-extra-panes'):
            hooks.append(ContentTemplateHook(extension, name,
                                             '[%s here]' % name))

        # Turn off some parts of the page, to simplify the resulting HTML
        # and shorten render/parse times.
        self.spy_on(get_review_request_fieldsets,
                    call_fake=lambda *args, **kwargs: [])

        response = self.client.get(
            local_site_reverse('review-request-detail',
                               args=[review_request.display_id]))
        self.assertEqual(response.status_code, 200)

        parsed_html = str(parse_html(response.content.decode('utf-8')))
        self.assertIn(
            '<div class="rb-c-review-request__fields">\n'
            '[before-review-request-summary here]',
            parsed_html)
        self.assertIn(
            '<div aria-label="Review request summary"'
            ' class="-has-inline-fields rb-c-review-request-fieldset"'
            ' role="group">\n'
            '[review-request-summary-pre here]',
            parsed_html)
        self.assertIn(
            '</time>\n</p>[review-request-summary-post here]\n</div>',
            parsed_html)
        self.assertIn(
            '[before-review-request-fields here]'
            '<div class="rb-c-review-request__details"'
            ' id="review-request-details">',
            parsed_html)
        self.assertIn(
            '</div>'
            '[after-review-request-fields here] '
            '[before-review-request-extra-panes here]'
            '<div class="rb-c-review-request__extra"'
            ' id="review-request-extra">\n'
            '<div aria-label="Extra fields"'
            ' class="rb-c-review-request-fieldset" role="group">\n'
            '[review-request-extra-panes-pre here]',
            parsed_html)
        self.assertIn(
            '</div>[review-request-extra-panes-post here]\n'
            '</div>\n'
            '</div>[after-review-request-extra-panes here]\n'
            '</div>',
            parsed_html)
