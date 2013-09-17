from django.contrib.auth.models import User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (default_reviewer_item_mimetype,
                                                default_reviewer_list_mimetype)
from reviewboard.webapi.tests.urls import (get_default_reviewer_item_url,
                                           get_default_reviewer_list_url)


class DefaultReviewerResourceTests(BaseWebAPITestCase):
    """Testing the DefaultReviewerResource APIs."""

    #
    # List tests
    #

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewers(self):
        """Testing the GET default-reviewers/ API"""
        user = User.objects.get(username='doc')
        group = Group.objects.create(name='group1')
        repository = self.create_repository()

        DefaultReviewer.objects.create(name='default1', file_regex='.*')

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.people.add(user)
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(repository)

        rsp = self.apiGet(get_default_reviewer_list_url(),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[0]['file_regex'], '.*')
        self.assertEqual(default_reviewers[1]['name'], 'default2')
        self.assertEqual(default_reviewers[1]['file_regex'], '/foo')

        users = default_reviewers[1]['users']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['title'], user.username)

        groups = default_reviewers[1]['groups']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['title'], group.name)

        repos = default_reviewers[1]['repositories']
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['title'], repository.name)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewers_with_site(self):
        """Testing the GET default-reviewers/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        DefaultReviewer.objects.create(name='default1', file_regex='.*',
                                       local_site=local_site)
        DefaultReviewer.objects.create(name='default2', file_regex='/foo')

        # Test for non-LocalSite ones.
        rsp = self.apiGet(get_default_reviewer_list_url(),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default2')
        self.assertEqual(default_reviewers[0]['file_regex'], '/foo')

        # Now test for the ones in the LocalSite.
        self._login_user(local_site=True)
        rsp = self.apiGet(get_default_reviewer_list_url(self.local_site_name),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[0]['file_regex'], '.*')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewers_with_site_no_access(self):
        """Testing the GET default-reviewers/ API
        with a local site and Permission Denied error
        """
        self.apiGet(get_default_reviewer_list_url(self.local_site_name),
                    expected_status=403)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewers_with_repositories(self):
        """Testing the GET default-reviewers/?repositories= API"""
        repository1 = self.create_repository(name='repo 1')
        repository2 = self.create_repository(name='repo 2')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.repository.add(repository1)
        default_reviewer.repository.add(repository2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.repository.add(repository2)

        # Test singling out one repository.
        rsp = self.apiGet('%s?repositories=%s'
                          % (get_default_reviewer_list_url(), repository2.pk),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet('%s?repositories=%s,%s'
                          % (get_default_reviewer_list_url(), repository1.pk,
                             repository2.pk),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    @add_fixtures(['test_users'])
    def test_get_default_reviewers_with_users(self):
        """Testing the GET default-reviewers/?users= API"""
        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.people.add(user1)
        default_reviewer.people.add(user2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.people.add(user2)

        # Test singling out one user.
        rsp = self.apiGet('%s?users=dopey' % get_default_reviewer_list_url(),
                          expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet(
            '%s?users=doc,dopey' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    def test_get_default_reviewers_with_groups(self):
        """Testing the GET default-reviewers/?groups= API"""
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.groups.add(group1)
        default_reviewer.groups.add(group2)

        default_reviewer = DefaultReviewer.objects.create(
            name='default2', file_regex='/foo')
        default_reviewer.groups.add(group2)

        # Test singling out one group.
        rsp = self.apiGet(
            '%s?groups=group2' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.apiGet(
            '%s?groups=group1,group2' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')


    @add_fixtures(['test_users', 'test_scmtools'])
    def test_post_default_reviewer(self, local_site=None):
        """Testing the POST default-reviewers/ API"""
        self._login_user(admin=True)

        name = 'default1'
        file_regex = '.*'
        git_tool = Tool.objects.get(name='Git')

        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')
        group1 = Group.objects.create(name='group1', local_site=local_site)
        group2 = Group.objects.create(name='group2', local_site=local_site)
        repo1 = Repository.objects.create(name='Test Repo 1',
                                          local_site=local_site,
                                          path='test-repo-1',
                                          tool=git_tool)
        repo2 = Repository.objects.create(name='Test Repo 2',
                                          local_site=local_site,
                                          path='test-repo-2',
                                          tool=git_tool)

        # For the tests, make sure these are what we expect.
        if local_site:
            local_site.users.add(user1)
            local_site.users.add(user2)

        rsp = self.apiPost(
            get_default_reviewer_list_url(local_site),
            {
                'name': name,
                'file_regex': file_regex,
                'users': ','.join([user1.username, user2.username]),
                'groups': ','.join([group1.name, group2.name]),
                'repositories': ','.join([str(repo1.pk), str(repo2.pk)]),
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(
            pk=rsp['default_reviewer']['id'])
        self.assertEqual(default_reviewer.local_site, local_site)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], user1)
        self.assertEqual(people[1], user2)

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], group1)
        self.assertEqual(groups[1], group2)

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0], repo1)
        self.assertEqual(repos[1], repo2)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_defaults(self):
        """Testing the POST default-reviewers/ API with field defaults"""
        self._login_user(admin=True)

        name = 'default1'
        file_regex = '.*'

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': name,
                'file_regex': file_regex,
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(
            pk=rsp['default_reviewer']['id'])
        self.assertEqual(default_reviewer.local_site, None)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_permission_denied(self):
        """Testing the POST default-reviewers/ API
        with Permission Denied error
        """
        self._login_user()

        self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
            },
            expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_permission_denied_and_local_site(self):
        """Testing the POST default-reviewers/ API
        with a local site and Permission Denied error
        """
        self._login_user()

        self.apiPost(
            get_default_reviewer_list_url(self.local_site_name),
            {
                'name': 'default1',
                'file_regex': '.*',
            },
            expected_status=403)

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_username(self):
        """Testing the POST default-reviewers/ API with invalid username"""
        self._login_user(admin=True)

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'users': 'foo'
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_user_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with user and invalid site
        """
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)

        rsp = self.apiPost(
            get_default_reviewer_list_url(local_site),
            {
                'name': 'default1',
                'file_regex': '.*',
                'users': 'grumpy'
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_group(self):
        """Testing the POST default-reviewers/ API with invalid group"""
        self._login_user(admin=True)

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'groups': 'foo'
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_default_reviewer_with_group_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with group and invalid site
        """
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'groups': 'group1'
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_default_reviewer_with_invalid_repository(self):
        """Testing the POST default-reviewers/ API with invalid repository"""
        self._login_user(admin=True)

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'repositories': '12345'
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_post_default_reviewer_with_repository_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with repository and invalid site
        """
        repository = self.create_repository(with_local_site=True)

        self._login_user(admin=True)

        rsp = self.apiPost(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'repositories': str(repository.pk),
            },
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_post_default_reviewer_with_site(self, local_site=None):
        """Testing the POST default-reviewers/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post_default_reviewer(local_site)

    #
    # Item tests
    #

    @add_fixtures(['test_users'])
    def test_delete_default_reviewer(self):
        """Testing the DELETE default-reviewers/<id>/ API"""
        self._login_user(admin=True)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiDelete(get_default_reviewer_item_url(default_reviewer.pk),
                       expected_status=204)
        self.assertFalse(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users'])
    def test_delete_default_reviewer_with_permission_denied_error(self):
        """Testing the DELETE default-reviewers/<id>/ API
        with Permission Denied error
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiDelete(get_default_reviewer_item_url(default_reviewer.pk),
                       expected_status=403)
        self.assertTrue(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users', 'test_site'])
    def test_delete_default_reviewer_with_site(self):
        """Testing the DELETE default-reviewers/<id>/ API with a local site"""
        self._login_user(local_site=True, admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiDelete(get_default_reviewer_item_url(default_reviewer.pk,
                                                     self.local_site_name),
                       expected_status=204)
        self.assertFalse(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users', 'test_site'])
    def test_delete_default_reviewer_with_site_and_permission_denied_error(self):
        """Testing the DELETE default-reviewers/<id>/ API
        with a local site and Permission Denied error
        """
        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiDelete(get_default_reviewer_item_url(default_reviewer.pk,
                                                     self.local_site_name),
                       expected_status=403)
        self.assertTrue(
            DefaultReviewer.objects.filter(name='default1').exists())

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_get_default_reviewer(self):
        """Testing the GET default-reviewers/<id>/ API"""
        user = User.objects.get(username='doc')
        group = Group.objects.create(name='group1')
        repository = self.create_repository()

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        default_reviewer.people.add(user)
        default_reviewer.groups.add(group)
        default_reviewer.repository.add(repository)

        rsp = self.apiGet(get_default_reviewer_item_url(default_reviewer.pk),
                          expected_mimetype=default_reviewer_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['default_reviewer']['name'], 'default1')
        self.assertEqual(rsp['default_reviewer']['file_regex'], '.*')

        users = rsp['default_reviewer']['users']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['title'], user.username)

        groups = rsp['default_reviewer']['groups']
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['title'], group.name)

        repos = rsp['default_reviewer']['repositories']
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['title'], repository.name)

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewer_with_site(self):
        """Testing the GET default-reviewers/<id>/ API with a local site"""
        self._login_user(local_site=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        rsp = self.apiGet(get_default_reviewer_item_url(default_reviewer.pk,
                                                        self.local_site_name),
                          expected_mimetype=default_reviewer_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['default_reviewer']['name'], 'default1')
        self.assertEqual(rsp['default_reviewer']['file_regex'], '.*')

    @add_fixtures(['test_users', 'test_site'])
    def test_get_default_reviewer_with_site_no_access(self):
        """Testing the GET default-reviewers/<id>/ API
        with a local site and Permission Denied error
        """
        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiGet(get_default_reviewer_item_url(default_reviewer.pk,
                                                  self.local_site_name),
                    expected_status=403)

    def test_get_default_reviewer_not_modified(self):
        """Testing the GET default-reviewers/<id>/ API
        with Not Modified response
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._testHttpCaching(
            get_default_reviewer_item_url(default_reviewer.pk),
            check_etags=True)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_put_default_reviewer(self, local_site=None):
        """Testing the PUT default-reviewers/<id>/ API"""
        name = 'my-default-reviewer'
        file_regex = '/foo/'
        git_tool = Tool.objects.get(name='Git')

        old_user = User.objects.get(username='admin')
        old_group = Group.objects.create(name='group3', local_site=local_site)
        old_repo = Repository.objects.create(name='Old Repo',
                                             local_site=local_site,
                                             path='old-repo',
                                             tool=git_tool)

        user1 = User.objects.get(username='doc')
        user2 = User.objects.get(username='dopey')
        group1 = Group.objects.create(name='group1', local_site=local_site)
        group2 = Group.objects.create(name='group2', local_site=local_site)
        repo1 = Repository.objects.create(name='Test Repo 1',
                                          local_site=local_site,
                                          path='test-repo-1',
                                          tool=git_tool)
        repo2 = Repository.objects.create(name='Test Repo 2',
                                          local_site=local_site,
                                          path='test-repo-2',
                                          tool=git_tool)

        # For the tests, make sure these are what we expect.
        if local_site:
            local_site.users.add(user1)
            local_site.users.add(user2)
            local_site.users.add(old_user)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)
        default_reviewer.groups.add(old_group)
        default_reviewer.repository.add(old_repo)
        default_reviewer.people.add(old_user)

        self._login_user(admin=True)
        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk, local_site),
            {
                'name': name,
                'file_regex': file_regex,
                'users': ','.join([user1.username, user2.username]),
                'groups': ','.join([group1.name, group2.name]),
                'repositories': ','.join([str(repo1.pk), str(repo2.pk)]),
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(default_reviewer.local_site, local_site)
        self.assertEqual(default_reviewer.name, name)
        self.assertEqual(default_reviewer.file_regex, file_regex)

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0], user1)
        self.assertEqual(people[1], user2)

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], group1)
        self.assertEqual(groups[1], group2)

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0], repo1)
        self.assertEqual(repos[1], repo2)

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_put_default_reviewer_with_site(self):
        """Testing the PUT default-reviewers/<id>/ API with a local site"""
        self.test_put_default_reviewer(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_permission_denied(self):
        """Testing the POST default-reviewers/ API with Permission Denied
        error
        """
        self._login_user()

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'name': 'default2'},
            expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_permission_denied_and_local_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with a local site and Permission Denied error
        """
        self._login_user()

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk,
                                          self.local_site_name),
            {'name': 'default2'},
            expected_status=403)

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_username(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid username"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'users': 'foo'},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_user_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with user and invalid site
        """
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk,
                                          self.local_site_name),
            {'users': 'grumpy'},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('users' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_group(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid group"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'groups': 'foo'},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_default_reviewer_with_group_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with group and invalid site
        """
        self._login_user(admin=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'groups': 'group1'},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('groups' in rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_default_reviewer_with_invalid_repository(self):
        """Testing the PUT default-reviewers/<id>/ API
        with invalid repository
        """
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'repositories': '12345'},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_put_default_reviewer_with_repository_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with repository and invalid site
        """
        repository = self.create_repository(with_local_site=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._login_user(admin=True)

        rsp = self.apiPut(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'repositories': str(repository.pk)},
            expected_status=400)

        self.assertTrue('fields' in rsp)
        self.assertTrue('repositories' in rsp['fields'])
