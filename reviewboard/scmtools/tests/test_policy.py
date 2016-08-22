from __future__ import unicode_literals

import os

from django.contrib.auth.models import AnonymousUser, User

from reviewboard.reviews.models import Group
from reviewboard.scmtools.forms import RepositoryForm
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class PolicyTests(TestCase):
    """Unit tests for access policies."""

    fixtures = ['test_scmtools']

    def setUp(self):
        self.user = User.objects.create(username='testuser', password='')
        self.anonymous = AnonymousUser()
        self.repo = Repository.objects.create(
            name='test',
            path='example.com:/cvsroot/test',
            username='anonymous',
            tool=Tool.objects.get(name='CVS'))

    def test_repository_public(self):
        """Testing access to a public repository"""
        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertTrue(self.repo.is_accessible_by(self.anonymous))

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
        self.assertTrue(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_denied(self):
        """Testing no access to an inaccessible private repository"""
        self.repo.public = False
        self.repo.save()

        self.assertFalse(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertNotIn(self.repo, Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_allowed_by_user(self):
        """Testing access to a private repository accessible by user"""
        self.repo.users.add(self.user)
        self.repo.public = False
        self.repo.save()

        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_private_access_allowed_by_review_group(self):
        """Testing access to a private repository accessible by review group"""
        group = Group.objects.create(name='test-group')
        group.users.add(self.user)

        self.repo.public = False
        self.repo.review_groups.add(group)
        self.repo.save()

        self.assertTrue(self.repo.is_accessible_by(self.user))
        self.assertFalse(self.repo.is_accessible_by(self.anonymous))

        self.assertIn(self.repo, Repository.objects.accessible(self.user))
        self.assertFalse(
            self.repo in Repository.objects.accessible(self.anonymous))

    def test_repository_form_with_local_site_and_bad_group(self):
        """Testing adding a Group to a RepositoryForm with the wrong LocalSite
        """
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='Subversion')
        group = Group.objects.create(name='test-group')

        svn_repo_path = 'file://' + os.path.join(os.path.dirname(__file__),
                                                 '..', 'testdata', 'svn_repo')

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'review_groups': [group.pk],
            'local_site': test_site.pk,
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())

        group.local_site = test_site
        group.save()

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'review_groups': [group.pk],
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())

    def test_repository_form_with_local_site_and_bad_user(self):
        """Testing adding a User to a RepositoryForm with the wrong LocalSite
        """
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='Subversion')

        svn_repo_path = 'file://' + os.path.join(os.path.dirname(__file__),
                                                 '..', 'testdata', 'svn_repo')

        form = RepositoryForm({
            'name': 'test',
            'path': svn_repo_path,
            'hosting_type': 'custom',
            'bug_tracker_type': 'custom',
            'users': [self.user.pk],
            'local_site': test_site.pk,
            'tool': tool.pk,
        })
        self.assertFalse(form.is_valid())
