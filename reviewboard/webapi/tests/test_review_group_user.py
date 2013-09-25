from django.contrib.auth.models import User

from reviewboard.webapi.resources import resources
from reviewboard.webapi.errors import INVALID_USER
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (user_item_mimetype,
                                                user_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_review_group_user_item_url,
                                           get_review_group_user_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ReviewGroupUserResource list API tests."""
    __metaclass__ = BasicTestsMetaclass

    fixtures = ['test_users']
    sample_api_url = 'groups/<name>/users/'
    resource = resources.review_group_user
    basic_post_use_admin = True

    def compare_item(self, item_rsp, user):
        self.assertEqual(item_rsp['id'], user.pk)
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        group = self.create_review_group(with_local_site=with_local_site)

        if populate_items:
            items = [
                User.objects.get(username='doc'),
                User.objects.get(username='grumpy'),
            ]
            group.users = items
        else:
            items = []

        return (get_review_group_user_list_url(group.name, local_site_name),
                user_list_mimetype,
                items)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        group = self.create_review_group(with_local_site=with_local_site)

        if post_valid_data:
            post_data = {
                'username': 'doc',
            }
        else:
            post_data = {}

        return (get_review_group_user_list_url(group.name, local_site_name),
                user_item_mimetype,
                post_data,
                [group])

    def check_post_result(self, user, rsp, group):
        users = list(group.users.all())
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, 'doc')
        self.compare_item(rsp['user'], users[0])

    def test_post_with_no_access(self, local_site=None):
        """Testing the POST groups/<name>/users/ API with Permission Denied"""
        group = self.create_review_group()
        user = User.objects.get(pk=1)

        rsp = self.apiPost(
            get_review_group_user_list_url(group.name, local_site),
            {'username': user.username},
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')

    def test_post_with_invalid_user(self):
        """Testing the POST groups/<name>/users/ API with invalid user"""
        self._login_user(admin=True)

        group = self.create_review_group()

        rsp = self.apiPost(
            get_review_group_user_list_url(group.name),
            {'username': 'grabl'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_USER.code)

        self.assertEqual(group.users.count(), 0)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ReviewGroupUserResource item API tests."""
    __metaclass__ = BasicTestsMetaclass

    fixtures = ['test_users']
    sample_api_url = 'groups/<name>/users/<username>/'
    resource = resources.review_group_user
    basic_delete_use_admin = True
    basic_put_use_admin = True

    def setup_http_not_allowed_item_test(self, user):
        return get_review_group_user_list_url('my-group')

    def compare_item(self, item_rsp, user):
        self.assertEqual(item_rsp['id'], user.pk)
        self.assertEqual(item_rsp['username'], user.username)
        self.assertEqual(item_rsp['first_name'], user.first_name)
        self.assertEqual(item_rsp['last_name'], user.last_name)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        group = self.create_review_group(with_local_site=with_local_site)
        doc = User.objects.get(username='doc')
        group.users.add(doc)

        return (get_review_group_user_item_url(group.name, doc.username,
                                               local_site_name),
                [group, doc])

    def check_delete_result(self, user, group, doc):
        self.assertNotIn(doc, group.users.all())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        group = self.create_review_group(with_local_site=with_local_site)
        doc = User.objects.get(username='doc')
        group.users.add(doc)

        return (get_review_group_user_item_url(group.name, doc.username,
                                               local_site_name),
                user_item_mimetype,
                doc)
