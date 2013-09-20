from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.webapi.errors import GROUP_ALREADY_EXISTS
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_group_item_mimetype,
                                                review_group_list_mimetype)
from reviewboard.webapi.tests.urls import (get_review_group_item_url,
                                           get_review_group_list_url)


class ResourceListTests(BaseWebAPITestCase):
    """Testing the ReviewGroupResource list APIs."""
    fixtures = ['test_users']

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_site'])
    def test_get(self):
        """Testing the GET groups/ API"""
        self.create_review_group(name='group1')
        self.create_review_group(name='group2', with_local_site=True)

        rsp = self.apiGet(get_review_group_list_url(),
                          expected_mimetype=review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']),
                         Group.objects.accessible(self.user).count())
        self.assertEqual(len(rsp['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET groups/ API with a local site"""
        self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.create_review_group(name='group1', with_local_site=True)
        self.create_review_group(name='group2')

        groups = Group.objects.accessible(self.user, local_site=local_site)

        rsp = self.apiGet(get_review_group_list_url(self.local_site_name),
                          expected_mimetype=review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), groups.count())
        self.assertEqual(len(rsp['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET groups/ API
        with a local site and Permission Denied error
        """
        self.apiGet(get_review_group_list_url(self.local_site_name),
                    expected_status=403)

    def test_get_with_q(self):
        """Testing the GET groups/?q= API"""
        self.create_review_group(name='docgroup')
        self.create_review_group(name='devgroup')

        rsp = self.apiGet(get_review_group_list_url(), {'q': 'dev'},
                          expected_mimetype=review_group_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1)  # devgroup

    #
    # HTTP POST tests
    #

    def test_post(self, local_site=None):
        """Testing the POST groups/ API"""
        name = 'my-group'
        display_name = 'My Group'
        mailing_list = 'mygroup@example.com'
        visible = False
        invite_only = True

        self._login_user(admin=True)

        rsp = self.apiPost(
            get_review_group_list_url(local_site),
            {
                'name': name,
                'display_name': display_name,
                'mailing_list': mailing_list,
                'visible': visible,
                'invite_only': invite_only,
            },
            expected_mimetype=review_group_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=rsp['group']['id'])
        self.assertEqual(group.local_site, local_site)
        self.assertEqual(group.name, name)
        self.assertEqual(group.display_name, display_name)
        self.assertEqual(group.mailing_list, mailing_list)
        self.assertEqual(group.visible, visible)
        self.assertEqual(group.invite_only, invite_only)

    @add_fixtures(['test_site'])
    def test_post_with_site(self):
        """Testing the POST groups/ API with a local site"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post(local_site)

    def test_post_with_defaults(self):
        """Testing the POST groups/ API with field defaults"""
        name = 'my-group'
        display_name = 'My Group'

        self._login_user(admin=True)

        rsp = self.apiPost(
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
        local_site = LocalSite.objects.get(name=self.local_site_name)

        rsp = self.apiPost(
            get_review_group_list_url(local_site),
            {
                'name': 'mygroup',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
            },
            expected_mimetype=review_group_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    def test_post_with_no_access(self, local_site=None):
        """Testing the POST groups/ API with no access"""
        rsp = self.apiPost(
            get_review_group_list_url(local_site),
            {
                'name': 'mygroup',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
            },
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_post_with_site_no_access(self):
        """Testing the POST groups/ API with local site and no access"""
        local_site = LocalSite.objects.get(name=self.local_site_name)
        self.test_post_with_no_access(local_site)

    def test_post_with_conflict(self):
        """Testing the POST groups/ API with Group Already Exists error"""
        self._login_user(admin=True)
        group = self.create_review_group()

        rsp = self.apiPost(
            get_review_group_list_url(),
            {
                'name': group.name,
                'display_name': 'My Group',
            },
            expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)


class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ReviewGroupResource item APIs."""
    fixtures = ['test_users']

    #
    # HTTP DELETE tests
    #

    def test_delete(self):
        """Testing the DELETE groups/<id>/ API"""
        self._login_user(admin=True)
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.apiDelete(get_review_group_item_url('test-group'),
                       expected_status=204)
        self.assertFalse(Group.objects.filter(name='test-group').exists())

    def test_delete_with_permission_denied_error(self):
        """Testing the DELETE groups/<id>/ API with Permission Denied error"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.apiDelete(get_review_group_item_url('test-group'),
                       expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site(self):
        """Testing the DELETE groups/<id>/ API with a local site"""
        self.create_review_group(name='sitegroup', with_local_site=True)

        self._login_user(local_site=True, admin=True)
        self.apiDelete(
            get_review_group_item_url('sitegroup', self.local_site_name),
            expected_status=204)

    @add_fixtures(['test_site'])
    def test_delete_with_local_site_and_permission_denied_error(self):
        """Testing the DELETE groups/<id>/ API
        with a local site and Permission Denied error
        """
        self.create_review_group(name='sitegroup', with_local_site=True)

        self._login_user(local_site=True)
        self.apiDelete(
            get_review_group_item_url('sitegroup', self.local_site_name),
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

        self.apiDelete(get_review_group_item_url('test-group'),
                       expected_status=204)

        request = ReviewRequest.objects.get(pk=request.id)
        self.assertEqual(request.target_groups.count(), 0)

    #
    # HTTP GET tests
    #

    def test_get_public(self):
        """Testing the GET groups/<id>/ API"""
        group = Group.objects.create(name='test-group')

        rsp = self.apiGet(get_review_group_item_url(group.name),
                          expected_mimetype=review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['name'], group.name)
        self.assertEqual(rsp['group']['display_name'], group.display_name)
        self.assertEqual(rsp['group']['invite_only'], False)

    def test_get_public_not_modified(self):
        """Testing the GET groups/<id>/ API with Not Modified response"""
        Group.objects.create(name='test-group')

        self._testHttpCaching(get_review_group_item_url('test-group'),
                              check_etags=True)

    def test_get_invite_only(self):
        """Testing the GET groups/<id>/ API with invite-only"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        rsp = self.apiGet(get_review_group_item_url(group.name),
                          expected_mimetype=review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['invite_only'], True)

    def test_get_invite_only_with_permission_denied_error(self):
        """Testing the GET groups/<id>/ API
        with invite-only and Permission Denied error
        """
        group = Group.objects.create(name='test-group', invite_only=True)

        rsp = self.apiGet(get_review_group_item_url(group.name),
                          expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET groups/<id>/ API with a local site"""
        self._login_user(local_site=True)
        group = self.create_review_group(with_local_site=True)

        rsp = self.apiGet(
            get_review_group_item_url(group.name, self.local_site_name),
            expected_mimetype=review_group_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['group']['name'], group.name)
        self.assertEqual(rsp['group']['display_name'], group.display_name)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET groups/<id>/ API
        with a local site and Permission Denied error
        """
        self.apiGet(
            get_review_group_item_url('sitegroup', self.local_site_name),
            expected_status=403)

    #
    # HTTP PUT tests
    #

    @add_fixtures(['test_site'])
    def test_put(self, local_site=None):
        """Testing the PUT groups/<name>/ API"""
        name = 'my-group'
        display_name = 'My Group'
        mailing_list = 'mygroup@example.com'

        group = self.create_review_group(
            with_local_site=(local_site is not None))

        self._login_user(admin=True)
        rsp = self.apiPut(
            get_review_group_item_url(group.name, local_site),
            {
                'name': name,
                'display_name': display_name,
                'mailing_list': mailing_list,
            },
            expected_mimetype=review_group_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        group = Group.objects.get(pk=group.pk)
        self.assertEqual(group.local_site, local_site)
        self.assertEqual(group.name, name)
        self.assertEqual(group.display_name, display_name)
        self.assertEqual(group.mailing_list, mailing_list)

    @add_fixtures(['test_site'])
    def test_put_with_site(self):
        """Testing the PUT groups/<name>/ API with local site"""
        self.test_put(LocalSite.objects.get(name=self.local_site_name))

    def test_put_with_no_access(self, local_site=None):
        """Testing the PUT groups/<name>/ API with no access"""
        group = self.create_review_group(
            with_local_site=(local_site is not None))

        rsp = self.apiPut(
            get_review_group_item_url(group.name, local_site),
            {
                'name': 'mygroup',
                'display_name': 'My Group',
                'mailing_list': 'mygroup@example.com',
            },
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')

    @add_fixtures(['test_site'])
    def test_put_with_site_no_access(self):
        """Testing the PUT groups/<name>/ API with local site and no access"""
        self.test_put_with_no_access(
            LocalSite.objects.get(name=self.local_site_name))

    def test_put_with_conflict(self):
        """Testing the PUT groups/<name>/ API
        with Group Already Exists error
        """
        group = self.create_review_group(name='group1')
        group2 = self.create_review_group(name='group2')

        self._login_user(admin=True)
        rsp = self.apiPut(
            get_review_group_item_url(group.name),
            {'name': group2.name},
            expected_status=409)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], GROUP_ALREADY_EXISTS.code)
