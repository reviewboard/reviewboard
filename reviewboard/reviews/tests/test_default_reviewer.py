from reviewboard.reviews.models import DefaultReviewer
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DefaultReviewerTests(TestCase):
    """Unit tests for DefaultReviewer."""

    fixtures = ['test_scmtools']

    def test_for_repository(self):
        """Testing DefaultReviewer.objects.for_repository"""
        default_reviewer1 = DefaultReviewer.objects.create(name='Test',
                                                           file_regex='.*')

        default_reviewer2 = DefaultReviewer.objects.create(name='Bar',
                                                           file_regex='.*')

        repo1 = self.create_repository(name='Test1',
                                       path='path1',
                                       tool_name='CVS')
        default_reviewer1.repository.add(repo1)

        repo2 = self.create_repository(name='Test2',
                                       path='path2',
                                       tool_name='CVS')

        default_reviewers = DefaultReviewer.objects.for_repository(repo1, None)
        self.assertEqual(len(default_reviewers), 2)
        self.assertIn(default_reviewer1, default_reviewers)
        self.assertIn(default_reviewer2, default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(repo2, None)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer2, default_reviewers)

    def test_for_repository_with_localsite(self):
        """Testing DefaultReviewer.objects.for_repository with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        default_reviewer1 = DefaultReviewer.objects.create(
            name='Test 1',
            file_regex='.*',
            local_site=test_site)

        default_reviewer2 = DefaultReviewer.objects.create(
            name='Test 2',
            file_regex='.*')

        default_reviewers = DefaultReviewer.objects.for_repository(
            None, test_site)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer1, default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(None, None)
        self.assertEqual(len(default_reviewers), 1)
        self.assertIn(default_reviewer2, default_reviewers)
