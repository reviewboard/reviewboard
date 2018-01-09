from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.reviews.forms import DefaultReviewerForm, GroupForm
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class DefaultReviewerFormTests(TestCase):
    """Unit tests for DefaultReviewerForm."""

    fixtures = ['test_scmtools']

    def test_form_with_localsite(self):
        """Testing DefaultReviewerForm with a LocalSite"""
        test_site = LocalSite.objects.create(name='test')

        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool,
                                         local_site=test_site)
        user = User.objects.create_user(username='testuser', password='',
                                        email='user@example.com')
        test_site.users.add(user)

        group = Group.objects.create(name='test', display_name='Test',
                                     local_site=test_site)

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
            'people': [user.pk],
            'groups': [group.pk],
        }, local_site=test_site)
        self.assertTrue(form.is_valid())
        default_reviewer = form.save()

        self.assertEqual(default_reviewer.local_site, test_site)
        self.assertEqual(default_reviewer.repository.get(), repo)
        self.assertEqual(default_reviewer.people.get(), user)
        self.assertEqual(default_reviewer.groups.get(), group)

    def test_form_with_localsite_and_bad_user(self):
        """Testing DefaultReviewerForm with a User not on the same LocalSite
        """
        test_site = LocalSite.objects.create(name='test')
        user = User.objects.create_user(username='testuser', password='',
                                        email='user@example.com')

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'people': [user.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_group(self):
        """Testing DefaultReviewerForm with a Group not on the same LocalSite
        """
        test_site = LocalSite.objects.create(name='test')
        group = Group.objects.create(name='test', display_name='Test')

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

        group.local_site = test_site
        group.save()

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_repository(self):
        """Testing DefaultReviewerForm with a Repository not on the same
        LocalSite
        """
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool)

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())

        repo.local_site = test_site
        repo.save()

        form = DefaultReviewerForm(data={
            'name': 'Test',
            'file_regex': '.*',
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_positional_argument(self):
        """Testing DefaultReviewerForm when passing data as a positional
        argument
        """
        # This was a regression caused by the change to add the new related
        # user selector.
        form = DefaultReviewerForm({
            'name': 'test',
            'file_regex': '.*',
        })

        self.assertTrue(form.is_valid())


class GroupFormTests(TestCase):
    def test_form_with_localsite(self):
        """Testing GroupForm with a LocalSite"""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create_user(username='testuser', password='',
                                        email='user@example.com')
        test_site.users.add(user)

        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        }, local_site_name=test_site.name)
        self.assertTrue(form.is_valid())
        group = form.save()

        self.assertEqual(group.local_site, test_site)
        self.assertEqual(group.users.get(), user)

    def test_form_with_localsite_and_bad_user(self):
        """Testing GroupForm with a User not on the same LocalSite"""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create_user(username='testuser', password='',
                                        email='user@example.com')

        form = GroupForm(data={
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_positional_argument(self):
        """Testing GroupForm when passing data as a positional argument"""
        # This was a regression caused by the change to add the new related
        # user selector.
        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
        })

        self.assertTrue(form.is_valid())
