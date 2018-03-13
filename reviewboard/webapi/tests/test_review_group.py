from __future__ import unicode_literals

from django.utils import six
from djblets.db.query import get_object_or_none
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.errors import GROUP_ALREADY_EXISTS
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_group_item_mimetype,
                                                review_group_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)
from reviewboard.webapi.tests.urls import (get_review_group_item_url,
                                           get_review_group_list_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ExtraDataListMixin, BaseWebAPITestCase):
    """Testing the ReviewGroupResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'groups/'
    resource = resources.review_group
    basic_post_use_admin = True

    def compare_item(self, item_rsp, group):
        self.assertEqual(item_rsp['id'], group.pk)
        self.assertEqual(item_rsp['name'], group.name)
        self.assertEqual(item_rsp['display_name'], group.display_name)
        self.assertEqual(item_rsp['mailing_list'], group.mailing_list)
        self.assertEqual(item_rsp['visible'], group.visible)
        self.assertEqual(item_rsp['invite_only'], group.invite_only)
        self.assertEqual(item_rsp['extra_data'], group.extra_data)
        self.assertEqual(item_rsp['absolute_url'],
                         self.base_url + group.get_absolute_url())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            if with_local_site:
                local_site = LocalSite.objects.get(name=local_site_name)

                items = [
                    self.create_review_group(name='group1',
                                             local_site=local_site),
                ]
                self.create_review_group(name='group2')
            else:
                local_site = LocalSite.objects.get_or_create(
                    name=self.local_site_name
                )[0]

                items = [
                    self.create_review_group(name='group1'),
                ]
                self.create_review_group(name='group2',
                                         local_site=local_site)
        else:
            items = []

        return (get_review_group_list_url(local_site_name),
                review_group_list_mimetype,
                items)

    def test_get_with_q(self):
        """Testing the GET groups/?q= API"""
        self.create_review_group(name='docgroup')
        self.create_review_group(name='devgroup')

        rsp = self.api_get(get_review_group_list_url(), {'q': 'dev'},
                           expected_mimetype=review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1)  # devgroup

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            post_data = {
                'name': 'my-group',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
                'visible': False,
                'invite_only': True,
            }
        else:
            post_data = {}

        return (get_review_group_list_url(local_site_name),
                review_group_item_mimetype,
                post_data,
                [])

    def check_post_result(self, user, rsp):
        group = Group.objects.get(pk=rsp['group']['id'])
        self.compare_item(rsp['group'], group)

    def test_post_with_defaults(self):
        """Testing the POST groups/ API with field defaults"""
        name = 'my-group'
        display_name = 'My Group'

        self._login_user(admin=True)

        rsp = self.api_post(
            get_review_group_list_url(),
            {
                'name': name,
                'display_name': display_name,
            },
            expected_mimetype=review_group_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=rsp['group']['id'])
        self.assertEqual(group.mailing_list, '')
        self.assertEqual(group.visible, True)
        self.assertEqual(group.invite_only, False)

    @add_fixtures(['test_site'])
    def test_post_with_site_admin(self):
        """Testing the POST groups/ API with a local site admin"""
        self._login_user(local_site=True, admin=True)
        local_site = self.get_local_site(name=self.local_site_name)

        rsp = self.api_post(
            get_review_group_list_url(local_site),
            {
                'name': 'mygroup',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
            },
            expected_mimetype=review_group_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_with_conflict(self):
        """Testing the POST groups/ API with Group Already Exists error"""
        self._login_user(admin=True)
        group = self.create_review_group()

        rsp = self.api_post(
            get_review_group_list_url(),
            {
                'name': group.name,
                'display_name': 'My Group',
            },
            expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(ExtraDataItemMixin, BaseWebAPITestCase):
    """Testing the ReviewGroupResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'groups/<id>/'
    resource = resources.review_group
    basic_delete_use_admin = True
    basic_put_use_admin = True

    def compare_item(self, item_rsp, group):
        self.assertEqual(item_rsp['id'], group.pk)
        self.assertEqual(item_rsp['name'], group.name)
        self.assertEqual(item_rsp['display_name'], group.display_name)
        self.assertEqual(item_rsp['mailing_list'], group.mailing_list)
        self.assertEqual(item_rsp['visible'], group.visible)
        self.assertEqual(item_rsp['invite_only'], group.invite_only)
        self.assertEqual(item_rsp['extra_data'], group.extra_data)

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        group = self.create_review_group(with_local_site=with_local_site)

        return (get_review_group_item_url(group.name, local_site_name),
                [group.name])

    def check_delete_result(self, user, group_name):
        self.assertIsNone(get_object_or_none(Group, name=group_name))

    def test_delete_with_permission_denied_error(self):
        """Testing the DELETE groups/<id>/ API with Permission Denied error"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.api_delete(get_review_group_item_url('test-group'),
                        expected_status=403)

    @add_fixtures(['test_scmtools'])
    def test_delete_with_review_requests(self):
        """Testing the DELETE groups/<id>/ API with existing review requests"""
        self._login_user(admin=True)

        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        repository = self.create_repository()
        request = ReviewRequest.objects.create(self.user, repository)
        request.target_groups.add(group)

        self.api_delete(get_review_group_item_url('test-group'),
                        expected_status=204)

        request = ReviewRequest.objects.get(pk=request.id)
        self.assertEqual(request.target_groups.count(), 0)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        group = self.create_review_group(with_local_site=with_local_site)

        return (get_review_group_item_url(group.name, local_site_name),
                review_group_item_mimetype,
                group)

    def test_get_not_modified(self):
        """Testing the GET groups/<id>/ API with Not Modified response"""
        Group.objects.create(name='test-group')

        self._testHttpCaching(get_review_group_item_url('test-group'),
                              check_etags=True)

    def test_get_invite_only(self):
        """Testing the GET groups/<id>/ API with invite-only"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        rsp = self.api_get(get_review_group_item_url(group.name),
                           expected_mimetype=review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['invite_only'], True)

    def test_get_invite_only_with_permission_denied_error(self):
        """Testing the GET groups/<id>/ API
        with invite-only and Permission Denied error
        """
        group = Group.objects.create(name='test-group', invite_only=True)

        rsp = self.api_get(get_review_group_item_url(group.name),
                           expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP PUT tests
    #

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        group = self.create_review_group(with_local_site=with_local_site)

        return (get_review_group_item_url(group.name, local_site_name),
                review_group_item_mimetype,
                {
                    'name': 'my-group',
                    'display_name': 'My Group',
                    'mailing_list': 'mygroup@example.com',
                },
                group,
                [])

    def check_put_result(self, user, item_rsp, group):
        group = Group.objects.get(pk=group.pk)
        self.compare_item(item_rsp, group)

    def test_put_with_no_access(self, local_site=None):
        """Testing the PUT groups/<name>/ API with no access"""
        group = self.create_review_group(
            with_local_site=(local_site is not None))

        rsp = self.api_put(
            get_review_group_item_url(group.name, local_site),
            {
                'name': 'mygroup',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
            },
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    def test_put_with_conflict(self):
        """Testing the PUT groups/<name>/ API
        with Group Already Exists error
        """
        group = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')

        self._login_user(admin=True)
        rsp = self.api_put(
            get_review_group_item_url(group.name),
            {'name': group2.name},
            expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)
