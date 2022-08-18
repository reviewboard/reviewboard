"""Unit tests for reviewboard.reviews.manager.ReviewManager.

Version Added:
    5.0
"""

from django.contrib.auth.models import AnonymousUser, Permission, User
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Group, Review
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class ReviewManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.manager.ReviewManager.

    Version Added:
        5.0
    """

    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_duplicate_reviews(self):
        """Testing ReviewManager.get_pending_review consolidation of duplicate
        reviews
        """
        body_top = 'This is the body_top.'
        body_bottom = 'This is the body_bottom.'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the first review.
        master_review = self.create_review(review_request, user=user,
                                           body_top=body_top,
                                           body_bottom='')
        self.create_diff_comment(master_review, filediff, text=comment_text_1,
                                 first_line=1, num_lines=1)

        # Create the second review.
        review = self.create_review(review_request, user=user,
                                    body_top='', body_bottom='')
        self.create_diff_comment(review, filediff, text=comment_text_2,
                                 first_line=1, num_lines=1)

        # Create the third review.
        review = self.create_review(review_request, user=user,
                                    body_top='',
                                    body_bottom=body_bottom)
        self.create_diff_comment(review, filediff, text=comment_text_3,
                                 first_line=1, num_lines=1)

        # Now that we've made a mess, see if we get a single review back.
        review = review_request.get_pending_review(user)
        self.assertIsNotNone(review)
        self.assertEqual(review.id, master_review.id)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)

        comments = list(review.comments.all())
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)
        self.assertEqual(comments[2].text, comment_text_3)

    @add_fixtures(['test_scmtools'])
    def test_duplicate_replies(self):
        """Testing ReviewManager.get_pending_reply consolidation of duplicate
        replies
        """
        body_top = 'This is the body_top'
        body_bottom = 'This is the body_bottom'
        comment_text_1 = 'Comment text 1'
        comment_text_2 = 'Comment text 2'
        comment_text_3 = 'Comment text 3'
        body_top_reply = 'This is the body_top reply'
        body_bottom_reply = 'This is the body_bottom reply'
        reply_text_1 = 'Reply text 1'
        reply_text_2 = 'Reply text 2'
        reply_text_3 = 'Reply text 3'

        # Some objects we need.
        user = User.objects.get(username='doc')

        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        # Create the parent review.
        review = self.create_review(review_request,
                                    user=user,
                                    body_top=body_top,
                                    body_bottom=body_bottom,
                                    publish=True)
        comment1 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_1,
                                            first_line=1,
                                            num_lines=1)
        comment2 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_2,
                                            first_line=2,
                                            num_lines=1)
        comment3 = self.create_diff_comment(review,
                                            filediff,
                                            text=comment_text_3,
                                            first_line=3,
                                            num_lines=1)

        # Create several replies.
        reply1 = self.create_reply(review, user=user, body_top=body_top_reply)
        self.create_diff_comment(reply1, filediff, text=reply_text_1,
                                 reply_to=comment1)

        reply2 = self.create_reply(review,
                                   user=user,
                                   body_top='',
                                   body_bottom=body_bottom_reply)
        self.create_diff_comment(reply2, filediff, text=reply_text_2,
                                 reply_to=comment2)

        reply3 = self.create_reply(review, user=user, body_top='')
        self.create_diff_comment(reply3, filediff, text=reply_text_3,
                                 reply_to=comment3)

        # Now that we've made a mess, see if we get a single reply back.
        reply = review.get_pending_reply(user)
        self.assertIsNotNone(reply)
        self.assertEqual(reply.body_top, body_top_reply)
        self.assertEqual(reply.body_bottom, body_bottom_reply)

        comments = list(reply.comments.all())
        self.assertEqual(len(comments), 3)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_reviews_and_review_requests(self):
        """Testing ReviewManager.accessible returns only public reviews
        from review requests that the user has access to and unpublished
        reviews that the user owns
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Published review on a publicly-accessible review request.
        review1 = self.create_review(review_request, publish=True)

        # Unpublished review on a publicly-accessible review request.
        review2 = self.create_review(review_request, publish=False)

        # Published review owned by the user on a publicly-accessible
        # review request.
        review3 = self.create_review(review_request, user=user, publish=True)

        # Unpublished review owned by the user on a publicly-accessible
        # review request.
        review4 = self.create_review(review_request, user=user, publish=False)

        # Published review request from a private repository the user
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Published review on a private repository the user does not have
        # access to.
        review5 = self.create_review(review_request_inaccessible, publish=True)

        # Unpublished review on a private repository the user does not have
        # access to.
        review6 = self.create_review(review_request_inaccessible,
                                     publish=False)

        # An invite-only review group used to limit access for the following
        # review requests.
        group = self.create_review_group(invite_only=True)

        # Published review from a review request that has an invite-only review
        # group not accessible to the user, but the user has access to through
        # being a targeted reviewer.
        review_request_targetted = self.create_review_request(publish=True)
        review_request_targetted.target_groups.add(group)
        review_request_targetted.target_people.add(user)
        review7 = self.create_review(review_request_targetted, publish=True)

        # Published review from a review request that has an invite-only review
        # group not accessible to the user, and that the user does not have
        # access to because the user is not listed as a target reviewer.
        review_request_untargetted = self.create_review_request(publish=True)
        review_request_untargetted.target_groups.add(group)
        review8 = self.create_review(review_request_untargetted, publish=True)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_anonymous = [
            {
                'model': Review,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review',
                    'scmtools_repository',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(review_request__repository=None) |
                     Q(review_request__repository__public=True)) &
                    (Q(review_request__target_groups=None) |
                     Q(review_request__target_groups__invite_only=False)) &
                    Q(public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access publicly-accessible
            # reviews.
            self.assertQuerysetEqual(
                Review.objects.accessible(anonymous),
                [review1, review3],
                ordered=False)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access publicly-accessible
            # reviews and reviews that they own.
            self.assertQuerysetEqual(
                Review.objects.accessible(user),
                [review1, review3, review4, review7],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_superuser = [
            {
                'model': Review,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can acess any reviews.
            self.assertQuerysetEqual(
                Review.objects.accessible(superuser),
                [
                    review1, review2, review3, review4,
                    review5, review6, review7, review8,
                ],
                ordered=False)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_repositories(self):
        """Testing ReviewManager.accessible returns only reviews from
        repositories that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Review from a public repository.
        repo1 = self.create_repository(name='repo1', public=True)
        review_request1 = self.create_review_request(publish=True,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from a private repository that the user has
        # access to from being listed in the repository's users list.
        repo2 = self.create_repository(name='repo2', public=False)
        repo2.users.add(user)
        review_request2 = self.create_review_request(publish=True,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)

        # An invite-only review group that the user has access to.
        group_accessible = self.create_review_group(invite_only=True)
        group_accessible.users.add(user)

        # Review from a private repository that the user has
        # access to through being a member of a targeted review group.
        repo3 = self.create_repository(name='repo3', public=False)
        repo3.review_groups.add(group_accessible)
        review_request3 = self.create_review_request(publish=True,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)

        # Review from a private repository that the user does
        # not have access to.
        repo4 = self.create_repository(name='repo4', public=False)
        review_request4 = self.create_review_request(publish=True,
                                                     repository=repo4)
        review4 = self.create_review(review_request4, publish=True)

        # Review from a private repository that the user has access
        # to through being a member of a targeted review group and
        # being listed on the repository's users list.
        repo5 = self.create_repository(name='repo5', public=False)
        repo5.review_groups.add(group_accessible)
        repo5.users.add(user)
        review_request5 = self.create_review_request(publish=True,
                                                     repository=repo5)
        review5 = self.create_review(review_request5, publish=True)

        # An invite-only review group that the user does not have access to.
        group_inaccessible = self.create_review_group(invite_only=True)

        # Review from a private repository that targets an invite-only review
        # group, but that the user has access to from being listed in the
        # repository's users list.
        repo6 = self.create_repository(name='repo6', public=False)
        repo6.review_groups.add(group_inaccessible)
        repo6.users.add(user)
        review_request6 = self.create_review_request(publish=True,
                                                     repository=repo6)
        review6 = self.create_review(review_request6, publish=True)

        # Review from a private repository that targets an invite-only review
        # group and that the user does not have access to.
        repo7 = self.create_repository(name='repo7', public=False)
        repo7.review_groups.add(group_inaccessible)
        review_request7 = self.create_review_request(publish=True,
                                                     repository=repo7)
        review7 = self.create_review(review_request7, publish=True)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_anonymous = [
            {
                'model': Review,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review',
                    'scmtools_repository',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(review_request__repository=None) |
                     Q(review_request__repository__public=True)) &
                    (Q(review_request__target_groups=None) |
                     Q(review_request__target_groups__invite_only=False)) &
                    Q(public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access reviews
            # from publicly-accessible repositories.
            self.assertQuerysetEqual(
                Review.objects.accessible(anonymous),
                [review1])

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[
                        repo1.pk, repo2.pk, repo3.pk, repo5.pk, repo6.pk,
                       ])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[
                        group_accessible.pk
                       ]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access reviews
            # from repositories that they have access to.
            self.assertQuerysetEqual(
                Review.objects.accessible(user),
                [review1, review2, review3, review5, review6],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_superuser = [
            {
                'model': Review,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can acess any reviews.
            self.assertQuerysetEqual(
                Review.objects.accessible(superuser),
                [
                    review1, review2, review3, review4,
                    review5, review6, review7,
                ],
                ordered=False)

    @add_fixtures(['test_scmtools'])
    def test_accessible_by_review_group(self):
        """Testing ReviewManager.accessible returns only reviews associated
        with review groups that the user has access to
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Review that the user has access to from being in a public
        # review group that is targeted by the review request.
        group1 = self.create_review_group(name='group1', invite_only=False)
        group1.users.add(user)
        review_request1 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request1.target_groups.add(group1)
        review1 = self.create_review(review_request1, publish=True)

        # Review that the user has access to from being in an invite-only
        # review group that is targeted by the review request.
        group2 = self.create_review_group(name='group2', invite_only=True)
        group2.users.add(user)
        review_request2 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request2.target_groups.add(group2)
        review2 = self.create_review(review_request2, publish=True)

        # Review that the user has access to since there is a public
        # review group that is targeted by the review request.
        group3 = self.create_review_group(name='group3', invite_only=False)
        review_request3 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request3.target_groups.add(group3)
        review3 = self.create_review(review_request3, publish=True)

        # Review that the user does not have access to since there is an
        # invite-only review group that is targeted by the review request.
        group4 = self.create_review_group(name='group4', invite_only=True)
        review_request4 = self.create_review_request(publish=True,
                                                     create_repository=True)
        review_request4.target_groups.add(group4)
        review4 = self.create_review(review_request4, publish=True)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_anonymous = [
            {
                'model': Review,
                'num_joins': 4,
                'tables': {
                    'reviews_group',
                    'reviews_reviewrequest',
                    'reviews_reviewrequest_target_groups',
                    'reviews_review',
                    'scmtools_repository',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(review_request__repository=None) |
                     Q(review_request__repository__public=True)) &
                    (Q(review_request__target_groups=None) |
                     Q(review_request__target_groups__invite_only=False)) &
                    Q(public=True)
                ),
            },
        ]

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access reviews
            # from review requests that target public review groups.
            self.assertQuerysetEqual(
                Review.objects.accessible(anonymous),
                [review1, review3],
                ordered=False)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[
                        group1.pk, group2.pk, group3.pk, group4.pk,
                       ])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[
                        group1.pk, group2.pk, group3.pk,
                       ]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the user can only access reviews
            # from review requests that target them directly or target
            # review groups they have access to.
            self.assertQuerysetEqual(
                Review.objects.accessible(user),
                [review1, review2, review3],
                ordered=False)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_superuser = [
            {
                'model': Review,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can access any reviews associated to
            # any review groups.
            self.assertQuerysetEqual(
                Review.objects.accessible(superuser),
                [review1, review2, review3, review4],
                ordered=False)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_by_local_sites(self):
        """Testing ReviewManager.accessible(local_site=) returns only reviews
        from the given local site
        """
        user = User.objects.get(username='doc')

        # Review from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from a private local site that the user does not have
        # access to.
        local_site2 = self.get_local_site('local-site-2')
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        self.create_review(review_request2, publish=True)

        # Review from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        self.create_review(review_request3, publish=True)

        # Review from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)

        # Load the user profiles and local site profiles into the cache
        # so that these don't influence the query counts.
        user.get_profile()
        user.get_site_profile(local_site=local_site1)

        # 6 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group's auth permissions
        # 4. Fetch user's local site permissions
        # 5. Fetch user's accessible groups
        # 6. Fetch reviews
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group'
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=local_site1)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type'
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': User,
                'extra': {
                    'a': ('1', [])
                },
                'limit': 1,
                'num_joins': 1,
                'tables': {
                    'auth_user',
                    'site_localsite_admins',
                },
                'where': (
                    Q(local_site_admins__id=local_site1.pk) &
                    Q(pk=user.pk)
                ),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=local_site1)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=local_site1) &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[repo1.pk])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that the reviews from other local sites or the global
            # site do not leak into the results from the given local site.
            self.assertQuerysetEqual(
                Review.objects.accessible(user, local_site=local_site1),
                [review1])

        # Testing that the reviews from local sites
        # do not leak into the results from the global site.
        self.assertQuerysetEqual(
            Review.objects.accessible(user),
            [review4])

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_accessible_with_show_all_local_sites(self):
        """Testing Review.objects.accessible(local_site=) with querying for
        all local sites
        """
        user = User.objects.get(username='doc')

        # Review from a private local site that the user has access to.
        local_site1 = self.get_local_site(self.local_site_name)
        local_site1.users.add(user)
        repo1 = self.create_repository(local_site=local_site1)
        review_request1 = self.create_review_request(publish=True,
                                                     local_site=local_site1,
                                                     repository=repo1)
        review1 = self.create_review(review_request1, publish=True)

        # Review from another private local site that the user has access to.
        local_site2 = self.get_local_site('local-site-2')
        local_site2.users.add(user)
        repo2 = self.create_repository(local_site=local_site2)
        review_request2 = self.create_review_request(publish=True,
                                                     local_site=local_site2,
                                                     repository=repo2)
        review2 = self.create_review(review_request2, publish=True)

        # Review from a public local site.
        local_site3 = self.create_local_site('public-local-site', public=True)
        repo3 = self.create_repository(local_site=local_site3)
        review_request3 = self.create_review_request(publish=True,
                                                     local_site=local_site3,
                                                     repository=repo3)
        review3 = self.create_review(review_request3, publish=True)

        # Review from a global site.
        review_request4 = self.create_review_request(publish=True)
        review4 = self.create_review(review_request4, publish=True)

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        queries_user = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    Q(public=True) |
                    Q(users__pk=user.pk) |
                    Q(review_groups__users=user.pk)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    Q(invite_only=False) |
                    Q(users=user.pk)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[
                        repo1.pk, repo2.pk, repo3.pk
                       ])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries_user):
            # Testing that passing LocalSite.ALL returns reviews from all local
            # sites and the global site.
            #
            # Note that this does not test for local site access, since callers
            # of Review.objects.accessible are responsible for ensuring that
            # the user has access to the given local site(s).
            self.assertQuerysetEqual(
                Review.objects.accessible(user, local_site=LocalSite.ALL),
                [review1, review2, review3, review4],
                ordered=False)

    @add_fixtures(['test_scmtools'])
    def test_accessible_with_public_true(self):
        """Testing ReviewManager.accessible(public=True) returns only public
        reviews from review requests that the user has access to and no
        unpublished reviews
        """
        self._test_accessible_with_public(expected_public=True)

    @add_fixtures(['test_scmtools'])
    def test_accessible_with_public_false(self):
        """Testing ReviewManager.accessible(public=False) returns only
        unpublished reviews that the user owns and no public reviews
        """
        self._test_accessible_with_public(expected_public=False)

    def test_accessible_with_extra_query(self):
        """Testing Review.objects.accessible with extra query parameters"""
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(publish=True)

        review = self.create_review(review_request,
                                    body_top='hello',
                                    publish=True)
        self.create_review(review_request, publish=True)
        extra_query = Q(body_top='hello')

        # 5 queries:
        #
        # 1. Fetch user's accessible repositories
        # 2. Fetch user's auth permissions
        # 3. Fetch user's group auth permissions
        # 4. Fetch user's accessible groups
        # 5. Fetch reviews
        queries = [
            {
                'model': Repository,
                'values_select': ('pk',),
                'num_joins': 4,
                'tables': {
                    'scmtools_repository_users',
                    'scmtools_repository',
                    'reviews_group_users',
                    'scmtools_repository_review_groups',
                    'reviews_group',
                },
                'where': (
                    (Q(public=True) |
                     Q(users__pk=user.pk) |
                     Q(review_groups__users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 2,
                'tables': {
                    'auth_permission',
                    'auth_user_user_permissions',
                    'django_content_type',
                },
                'where': Q(user__id=user.pk),
            },
            {
                'model': Permission,
                'values_select': ('content_type__app_label', 'codename',),
                'num_joins': 4,
                'tables': {
                    'auth_permission',
                    'auth_group',
                    'auth_user_groups',
                    'auth_group_permissions',
                    'django_content_type',
                },
                'where': Q(group__user=user),
            },
            {
                'model': Group,
                'values_select': ('pk',),
                'num_joins': 1,
                'tables': {
                    'reviews_group',
                    'reviews_group_users',
                },
                'where': (
                    (Q(invite_only=False) |
                     Q(users=user.pk)) &
                    Q(local_site=None)
                ),
            },
            {
                'model': Review,
                'num_joins': 3,
                'tables': {
                    'reviews_reviewrequest_target_people',
                    'reviews_review',
                    'reviews_reviewrequest_target_groups',
                    'reviews_reviewrequest',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    Q(body_top='hello') &
                    (Q(user=user) |
                     (Q(public=True) &
                      (Q(review_request__repository=None) |
                       Q(review_request__repository__in=[])) &
                      (Q(review_request__target_people=user) |
                       Q(review_request__target_groups=None) |
                       Q(review_request__target_groups__in=[]))))
                ),
            },
        ]

        with self.assertQueries(queries):
            # Testing that only reviews matching the extra query are returned.
            self.assertQuerysetEqual(
                Review.objects.accessible(user, extra_query=extra_query),
                [review])

    @add_fixtures(['test_scmtools'])
    def test_from_user(self):
        """Testing Review.objects.from_user"""
        user = User.objects.get(username='doc')
        user2 = self.create_user()
        repo = self.create_repository(public=True)
        review_request = self.create_review_request(publish=True,
                                                    repository=repo)

        review = self.create_review(review_request, publish=True, user=user)
        self.create_review(review_request, publish=True, user=user2)

        # 1 query:
        #
        # 1. Fetch reviews
        queries = [
            {
                'model': Review,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__status='P') &
                    Q(review_request__local_site=None) &
                    Q(user=user)
                ),
            },
        ]

        with self.assertQueries(queries):
            # Testing that only reviews from the given user are returned.
            self.assertQuerysetEqual(
                Review.objects.from_user(user),
                [review])

    def _test_accessible_with_public(self, expected_public):
        """Helper for testing ReviewManager.accessible(public=).

        This tests that ReviewManager.accessible(public=expected_public) only
        returns reviews whose ``publish`` field that match the expected
        public state.

        Args:
            expected_public (bool):
            The ``public`` value that should be set on the ``publish``
            field of matching reviews.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        anonymous = AnonymousUser()
        user = User.objects.get(username='doc')
        superuser = User.objects.get(username='admin')

        # Publicly-accessible published review request.
        review_request = self.create_review_request(publish=True)

        # Published/unpublished reviews on a publicly-accessible
        # review request.
        review1 = self.create_review(review_request, publish=expected_public)
        self.create_review(review_request, publish=not expected_public)

        # Published/unpublished reviews owned by the user on a
        # publicly-accessible review request.
        review3 = self.create_review(review_request,
                                     user=user,
                                     publish=expected_public)
        self.create_review(review_request,
                           user=user,
                           publish=not expected_public)

        # Published review request from a private repository the user
        # does not have access to.
        repo = self.create_repository(public=False)
        review_request_inaccessible = self.create_review_request(
            repository=repo,
            publish=True)

        # Published/unpublished reviews on a private repository the user does
        # not have access to.
        review5 = self.create_review(review_request_inaccessible,
                                     publish=expected_public)
        self.create_review(review_request_inaccessible,
                           publish=not expected_public)

        if expected_public:
            # 1 query:
            #
            # 1. Fetch reviews
            queries_anonymous = [
                {
                    'model': Review,
                    'num_joins': 4,
                    'tables': {
                        'reviews_group',
                        'reviews_reviewrequest',
                        'reviews_reviewrequest_target_groups',
                        'reviews_review',
                        'scmtools_repository',
                    },
                    'where': (
                        Q(base_reply_to=None) &
                        Q(review_request__local_site=None) &
                        (Q(review_request__repository=None) |
                         Q(review_request__repository__public=True)) &
                        (Q(review_request__target_groups=None) |
                         Q(review_request__target_groups__invite_only=False)) &
                        Q(public=True)
                    ),
                },
            ]

            expected_results_anonymous = [review1, review3]
        else:
            # 0 queries.
            queries_anonymous = []
            expected_results_anonymous = []

        with self.assertQueries(queries_anonymous):
            # Testing that anonymous users can only access publicly-accessible
            # reviews and no drafts.
            self.assertQuerysetEqual(
                Review.objects.accessible(anonymous, public=expected_public),
                expected_results_anonymous,
                ordered=False)

        if expected_public:
            # 5 queries:
            #
            # 1. Fetch user's accessible repositories
            # 2. Fetch user's auth permissions
            # 3. Fetch user's group auth permissions
            # 4. Fetch user's accessible groups
            # 5. Fetch reviews
            queries_user = [
                {
                    'model': Repository,
                    'values_select': ('pk',),
                    'num_joins': 4,
                    'tables': {
                        'scmtools_repository_users',
                        'scmtools_repository',
                        'reviews_group_users',
                        'scmtools_repository_review_groups',
                        'reviews_group',
                    },
                    'where': (
                        (Q(public=True) |
                         Q(users__pk=user.pk) |
                         Q(review_groups__users=user.pk)) &
                        Q(local_site=None)
                    ),
                },
                {
                    'model': Permission,
                    'values_select': ('content_type__app_label', 'codename',),
                    'num_joins': 2,
                    'tables': {
                        'auth_permission',
                        'auth_user_user_permissions',
                        'django_content_type',
                    },
                    'where': Q(user__id=user.pk),
                },
                {
                    'model': Permission,
                    'values_select': ('content_type__app_label', 'codename',),
                    'num_joins': 4,
                    'tables': {
                        'auth_permission',
                        'auth_group',
                        'auth_user_groups',
                        'auth_group_permissions',
                        'django_content_type',
                    },
                    'where': Q(group__user=user),
                },
                {
                    'model': Group,
                    'values_select': ('pk',),
                    'num_joins': 1,
                    'tables': {
                        'reviews_group',
                        'reviews_group_users',
                    },
                    'where': (
                        (Q(invite_only=False) |
                         Q(users=user.pk)) &
                        Q(local_site=None)
                    ),
                },
                {
                    'model': Review,
                    'num_joins': 3,
                    'tables': {
                        'reviews_reviewrequest_target_people',
                        'reviews_review',
                        'reviews_reviewrequest_target_groups',
                        'reviews_reviewrequest',
                    },
                    'where': (
                        Q(base_reply_to=None) &
                        Q(review_request__local_site=None) &
                        Q(public=expected_public) &
                        ((Q(review_request__repository=None) |
                         Q(review_request__repository__in=[])) &
                         (Q(review_request__target_people=user) |
                         Q(review_request__target_groups=None) |
                         Q(review_request__target_groups__in=[])))
                    ),
                },
            ]

            expected_results_user = [review1, review3]
        else:
            # 5 queries:
            #
            # 1. Fetch user's accessible repositories
            # 2. Fetch user's auth permissions
            # 3. Fetch user's group auth permissions
            # 4. Fetch user's accessible groups
            # 5. Fetch reviews
            queries_user = [
                {
                    'model': Repository,
                    'values_select': ('pk',),
                    'num_joins': 4,
                    'tables': {
                        'scmtools_repository_users',
                        'scmtools_repository',
                        'reviews_group_users',
                        'scmtools_repository_review_groups',
                        'reviews_group',
                    },
                    'where': (
                        (Q(public=True) |
                         Q(users__pk=user.pk) |
                         Q(review_groups__users=user.pk)) &
                        Q(local_site=None)
                    ),
                },
                {
                    'model': Permission,
                    'values_select': ('content_type__app_label', 'codename',),
                    'num_joins': 2,
                    'tables': {
                        'auth_permission',
                        'auth_user_user_permissions',
                        'django_content_type',
                    },
                    'where': Q(user__id=user.pk),
                },
                {
                    'model': Permission,
                    'values_select': ('content_type__app_label', 'codename',),
                    'num_joins': 4,
                    'tables': {
                        'auth_permission',
                        'auth_group',
                        'auth_user_groups',
                        'auth_group_permissions',
                        'django_content_type',
                    },
                    'where': Q(group__user=user),
                },
                {
                    'model': Group,
                    'values_select': ('pk',),
                    'num_joins': 1,
                    'tables': {
                        'reviews_group',
                        'reviews_group_users',
                    },
                    'where': (
                        (Q(invite_only=False) |
                         Q(users=user.pk)) &
                        Q(local_site=None)
                    )
                },
                {
                    'model': Review,
                    'num_joins': 1,
                    'tables': {
                        'reviews_review',
                        'reviews_reviewrequest',
                    },
                    'where': (
                        Q(base_reply_to=None) &
                        Q(review_request__local_site=None) &
                        Q(public=expected_public) &
                        Q(user=user)
                    ),
                },
            ]

            expected_results_user = [review3]

        with self.assertQueries(queries_user):
            # Testing that the user can only access publicly-accessible
            # reviews and reviews that they own.
            self.assertQuerysetEqual(
                Review.objects.accessible(user, public=expected_public),
                expected_results_user,
                ordered=False)

        # 1 query:
        #
        # 1. Fetch reviews
        queries_superuser = [
            {
                'model': Review,
                'num_joins': 1,
                'tables': {
                    'reviews_reviewrequest',
                    'reviews_review',
                },
                'where': (
                    Q(base_reply_to=None) &
                    Q(review_request__local_site=None) &
                    Q(public=expected_public)
                ),
            },
        ]

        with self.assertQueries(queries_superuser):
            # Testing that superusers can acess any reviews.
            self.assertQuerysetEqual(
                Review.objects.accessible(superuser, public=expected_public),
                [review1, review3, review5],
                ordered=False)
