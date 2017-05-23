from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from django.utils.six.moves import zip
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import INVALID_FORM_DATA

from reviewboard.reviews.models import DefaultReviewer, Group
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (default_reviewer_item_mimetype,
                                                default_reviewer_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_default_reviewer_item_url,
                                           get_default_reviewer_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the DefaultReviewerResource list APIs."""
    fixtures = ['test_users']
    basic_post_fixtures = ['test_scmtools']
    basic_post_use_admin = True
    sample_api_url = 'default-reviewers/'
    resource = resources.default_reviewer
    test_http_methods = ('POST',)

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_scmtools'])
    def test_get(self):
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

        rsp = self.api_get(get_default_reviewer_list_url(),
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

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET default-reviewers/ API with a local site"""
        local_site = self.get_local_site(name=self.local_site_name)
        DefaultReviewer.objects.create(name='default1', file_regex='.*',
                                       local_site=local_site)
        DefaultReviewer.objects.create(name='default2', file_regex='/foo')

        # Test for non-LocalSite ones.
        rsp = self.api_get(get_default_reviewer_list_url(),
                           expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default2')
        self.assertEqual(default_reviewers[0]['file_regex'], '/foo')

        # Now test for the ones in the LocalSite.
        self._login_user(local_site=True)
        rsp = self.api_get(get_default_reviewer_list_url(self.local_site_name),
                           expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[0]['file_regex'], '.*')

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET default-reviewers/ API
        with a local site and Permission Denied error
        """
        self.api_get(get_default_reviewer_list_url(self.local_site_name),
                     expected_status=403)

    @add_fixtures(['test_scmtools'])
    def test_get_with_repositories(self):
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
        rsp = self.api_get('%s?repositories=%s'
                           % (get_default_reviewer_list_url(), repository2.pk),
                           expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.api_get('%s?repositories=%s,%s'
                           % (get_default_reviewer_list_url(), repository1.pk,
                              repository2.pk),
                           expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    def test_get_with_users(self):
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
        rsp = self.api_get('%s?users=dopey' % get_default_reviewer_list_url(),
                           expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.api_get(
            '%s?users=doc,dopey' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    def test_get_with_groups(self):
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
        rsp = self.api_get(
            '%s?groups=group2' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 2)
        self.assertEqual(default_reviewers[0]['name'], 'default1')
        self.assertEqual(default_reviewers[1]['name'], 'default2')

        # Test requiring more than one.
        rsp = self.api_get(
            '%s?groups=group1,group2' % get_default_reviewer_list_url(),
            expected_mimetype=default_reviewer_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        default_reviewers = rsp['default_reviewers']
        self.assertEqual(len(default_reviewers), 1)
        self.assertEqual(default_reviewers[0]['name'], 'default1')

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            self.create_review_group(name='group1',
                                     with_local_site=with_local_site)
            self.create_review_group(name='group2',
                                     with_local_site=with_local_site)
            repo1 = self.create_repository(name='Test Repo 1',
                                           with_local_site=with_local_site,
                                           path='test-repo-1')
            repo2 = self.create_repository(name='Test Repo 2',
                                           with_local_site=with_local_site,
                                           path='test-repo-2')

            if with_local_site:
                site = self.get_local_site(name=local_site_name)
                site.users.add(User.objects.get(username='doc'))
                site.users.add(User.objects.get(username='dopey'))

            post_data = {
                'name': 'my-default',
                'file_regex': '.*',
                'users': 'doc,dopey',
                'groups': 'group1,group2',
                'repositories': ','.join([six.text_type(repo1.pk),
                                          six.text_type(repo2.pk)]),
            }
        else:
            post_data = {}

        return (get_default_reviewer_list_url(local_site_name),
                default_reviewer_item_mimetype,
                post_data,
                [local_site_name])

    def check_post_result(self, user, rsp, local_site_name):
        self.assertIn('default_reviewer', rsp)
        item_rsp = rsp['default_reviewer']

        self.assertEqual(item_rsp['name'], 'my-default')
        self.assertEqual(item_rsp['file_regex'], '.*')

        default_reviewer = DefaultReviewer.objects.get(pk=item_rsp['id'])
        self.assertEqual(default_reviewer.name, 'my-default')
        self.assertEqual(default_reviewer.file_regex, '.*')

        if local_site_name:
            self.assertEqual(default_reviewer.local_site.name, local_site_name)

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].username, 'doc')
        self.assertEqual(people[1].username, 'dopey')

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].name, 'group1')
        self.assertEqual(groups[1].name, 'group2')

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0].name, 'Test Repo 1')
        self.assertEqual(repos[1].name, 'Test Repo 2')

    @add_fixtures(['test_users'])
    def test_post_with_defaults(self):
        """Testing the POST default-reviewers/ API with field defaults"""
        self._login_user(admin=True)

        name = 'default1'
        file_regex = '.*'

        rsp = self.api_post(
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
    def test_post_with_permission_denied(self):
        """Testing the POST default-reviewers/ API
        with Permission Denied error
        """
        self._login_user()

        self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
            },
            expected_status=403)

    @add_fixtures(['test_users', 'test_site'])
    def test_post_with_invalid_regex(self):
        """Testing the POST default-reviewers/ API with an invalid regex"""
        self._login_user(admin=True)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '\\',
            },
            expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_FORM_DATA.code)
        self.assertIn('file_regex', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_with_invalid_username(self):
        """Testing the POST default-reviewers/ API with invalid username"""
        self._login_user(admin=True)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'users': 'foo'
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('users', rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_with_user_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with user and invalid site
        """
        self._login_user(admin=True)

        local_site = self.get_local_site(name=self.local_site_name)

        rsp = self.api_post(
            get_default_reviewer_list_url(local_site),
            {
                'name': 'default1',
                'file_regex': '.*',
                'users': 'grumpy'
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('users', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_with_invalid_group(self):
        """Testing the POST default-reviewers/ API with invalid group"""
        self._login_user(admin=True)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'groups': 'foo'
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('groups', rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_post_with_group_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with group and invalid site
        """
        self._login_user(admin=True)

        local_site = self.get_local_site(name=self.local_site_name)
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'groups': 'group1'
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('groups', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_post_with_invalid_repository(self):
        """Testing the POST default-reviewers/ API with invalid repository"""
        self._login_user(admin=True)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'repositories': '12345'
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('repositories', rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_post_with_repository_invalid_site(self):
        """Testing the POST default-reviewers/ API
        with repository and invalid site
        """
        repository = self.create_repository(with_local_site=True)

        self._login_user(admin=True)

        rsp = self.api_post(
            get_default_reviewer_list_url(),
            {
                'name': 'default1',
                'file_regex': '.*',
                'repositories': six.text_type(repository.pk),
            },
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('repositories', rsp['fields'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the DefaultReviewerResource item APIs."""
    fixtures = ['test_users']
    basic_get_fixtures = ['test_scmtools']
    basic_put_fixtures = ['test_scmtools']
    basic_delete_use_admin = True
    basic_put_use_admin = True
    sample_api_url = 'default-reviewers/<id>/'
    resource = resources.default_reviewer

    def compare_item(self, item_rsp, default_reviewer):
        self.assertEqual(default_reviewer.name, item_rsp['name'])
        self.assertEqual(default_reviewer.file_regex, item_rsp['file_regex'])

        users = list(default_reviewer.people.all())

        for user_rsp, user in zip(item_rsp['users'], users):
            self.assertEqual(user_rsp['title'], user.username)

        self.assertEqual(len(item_rsp['users']), len(users))

        groups = list(default_reviewer.groups.all())

        for group_rsp, group in zip(item_rsp['groups'], groups):
            self.assertEqual(group_rsp['title'], group.name)

        self.assertEqual(len(item_rsp['groups']), len(groups))

        repos = list(default_reviewer.repository.all())

        for repo_rsp, repo in zip(item_rsp['repositories'], repos):
            self.assertEqual(repo_rsp['title'], repo.name)

        self.assertEqual(len(item_rsp['repositories']), len(repos))


    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        if with_local_site:
            local_site = self.get_local_site(name=local_site_name)
        else:
            local_site = None

        default_reviewer = DefaultReviewer.objects.create(
            name='default1',
            file_regex='.*',
            local_site=local_site)

        return (get_default_reviewer_item_url(default_reviewer.pk,
                                              local_site_name),
                [])

    def check_delete_result(self, user):
        self.assertEqual(
            DefaultReviewer.objects.filter(name='default1').count(),
            0)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        if with_local_site:
            default_reviewer.local_site = \
                self.get_local_site(name=local_site_name)
            default_reviewer.save()

        default_reviewer.people.add(User.objects.get(username='doc'))
        default_reviewer.groups.add(
            self.create_review_group(name='group1',
                                     with_local_site=with_local_site))
        default_reviewer.repository.add(
            self.create_repository(with_local_site=with_local_site))

        return (get_default_reviewer_item_url(default_reviewer.pk,
                                              local_site_name),
                default_reviewer_item_mimetype,
                default_reviewer)

    def test_get_not_modified(self):
        """Testing the GET default-reviewers/<id>/ API
        with Not Modified response
        """
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._testHttpCaching(
            get_default_reviewer_item_url(default_reviewer.pk),
            check_etags=True)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        if with_local_site:
            local_site = self.get_local_site(name=local_site_name)
            local_site.users.add(User.objects.get(username='doc'))
            local_site.users.add(User.objects.get(username='dopey'))

            default_reviewer.local_site = local_site
            default_reviewer.save()

        default_reviewer.people.add(User.objects.get(username='doc'))
        default_reviewer.groups.add(
            self.create_review_group(name='group1',
                                     with_local_site=with_local_site))

        repo1 = self.create_repository(with_local_site=with_local_site,
                                       name='Test Repo 1',
                                       path='test-repo-1')
        default_reviewer.repository.add(repo1)

        if put_valid_data:
            self.create_review_group(name='group2',
                                     with_local_site=with_local_site)
            repo2 = self.create_repository(with_local_site=with_local_site,
                                           name='Test Repo 2',
                                           path='test-repo-2')

            put_data = {
                'name': 'New name',
                'file_regex': '/foo/',
                'users': 'doc,dopey',
                'groups': 'group1,group2',
                'repositories': ','.join([six.text_type(repo1.pk),
                                          six.text_type(repo2.pk)]),
            }
        else:
            put_data = {}

        return (get_default_reviewer_item_url(default_reviewer.pk,
                                              local_site_name),
                default_reviewer_item_mimetype,
                put_data,
                default_reviewer,
                [])

    def check_put_result(self, user, item_rsp, default_reviewer):
        self.assertEqual(item_rsp['name'], 'New name')
        self.assertEqual(item_rsp['file_regex'], '/foo/')

        default_reviewer = DefaultReviewer.objects.get(pk=item_rsp['id'])
        self.assertEqual(default_reviewer.name, 'New name')
        self.assertEqual(default_reviewer.file_regex, '/foo/')

        people = list(default_reviewer.people.all())
        self.assertEqual(len(people), 2)
        self.assertEqual(people[0].username, 'doc')
        self.assertEqual(people[1].username, 'dopey')

        groups = list(default_reviewer.groups.all())
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].name, 'group1')
        self.assertEqual(groups[1].name, 'group2')

        repos = list(default_reviewer.repository.all())
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0].name, 'Test Repo 1')
        self.assertEqual(repos[1].name, 'Test Repo 2')

    @add_fixtures(['test_users'])
    def test_put_with_invalid_username(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid username"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'users': 'foo'},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('users', rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_with_user_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with user and invalid site
        """
        self._login_user(admin=True)

        local_site = self.get_local_site(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*', local_site=local_site)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk,
                                          self.local_site_name),
            {'users': 'grumpy'},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('users', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_with_invalid_group(self):
        """Testing the PUT default-reviewers/<id>/ API with invalid group"""
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'groups': 'foo'},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('groups', rsp['fields'])

    @add_fixtures(['test_users', 'test_site'])
    def test_put_with_group_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with group and invalid site
        """
        self._login_user(admin=True)

        local_site = self.get_local_site(name=self.local_site_name)
        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')
        Group.objects.create(name='group1', local_site=local_site)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'groups': 'group1'},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('groups', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_with_invalid_repository(self):
        """Testing the PUT default-reviewers/<id>/ API
        with invalid repository
        """
        self._login_user(admin=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'repositories': '12345'},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('repositories', rsp['fields'])

    @add_fixtures(['test_users', 'test_site', 'test_scmtools'])
    def test_put_with_repository_invalid_site(self):
        """Testing the PUT default-reviewers/<id>/ API
        with repository and invalid site
        """
        repository = self.create_repository(with_local_site=True)

        default_reviewer = DefaultReviewer.objects.create(
            name='default1', file_regex='.*')

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {'repositories': six.text_type(repository.pk)},
            expected_status=400)

        self.assertIn('fields', rsp)
        self.assertIn('repositories', rsp['fields'])

    @add_fixtures(['test_users'])
    def test_put_clear_groups(self):
        """Testing PUT <URL> API with empty groups field"""
        group = Group.objects.create(name='group1')
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.groups.add(group)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'groups': ''
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.groups.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)

    @add_fixtures(['test_users'])
    def test_put_groups_only_commas(self):
        """Testing PUT <URL> API with groups field containing only commas"""
        group = Group.objects.create(name='group1')
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.groups.add(group)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'groups': ' , , , '
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.groups.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)

    @add_fixtures(['test_users'])
    def test_put_clear_users(self):
        """Testing PUT <URL> API with empty users field"""
        doc = User.objects.get(username='doc')
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.people.add(doc)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'users': ''
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.people.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)

    @add_fixtures(['test_users'])
    def test_put_users_only_commas(self):
        """Testing PUT <URL> API with users field containing only commas"""
        doc = User.objects.get(username='doc')
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.people.add(doc)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'users': ' , , , '
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.people.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_put_clear_repositories(self):
        """Testing PUT <URL> API with empty repositories field"""
        repository = self.create_repository()
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.repository.add(repository)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'repositories': '',
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.repository.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_put_repositories_only_comma(self):
        """Testing PUT <URL> API with repositories field containing only
        commas
        """
        repository = self.create_repository()
        default_reviewer = DefaultReviewer.objects.create(name='default1',
                                                          file_regex='.*')
        default_reviewer.repository.add(repository)

        self._login_user(admin=True)

        rsp = self.api_put(
            get_default_reviewer_item_url(default_reviewer.pk),
            {
                'file_regex': '.*',
                'name': 'default1',
                'repositories': ' , , , ',
            },
            expected_mimetype=default_reviewer_item_mimetype)

        self.assertIn('stat', rsp)
        self.assertEqual(rsp['stat'], 'ok')

        default_reviewer = DefaultReviewer.objects.get(pk=default_reviewer.pk)
        self.assertEqual(list(default_reviewer.repository.all()), [])

        self.assertIn('default_reviewer', rsp)
        self.compare_item(rsp['default_reviewer'], default_reviewer)
