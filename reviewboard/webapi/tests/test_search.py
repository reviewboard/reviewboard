"""Tests for the SearchResource APIs."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils import six
from djblets.testing.decorators import add_fixtures

from reviewboard.site.models import LocalSite
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import search_mimetype
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import get_search_url


@six.add_metaclass(BasicTestsMetaclass)
class ResourceTests(BaseWebAPITestCase):
    """Testing the SearchResource APIs."""

    fixtures = ['test_users']
    sample_api_url = 'search/'
    resource = resources.search

    def setup_http_not_allowed_list_test(self, user):
        return get_search_url()

    def setup_http_not_allowed_item_test(self, user):
        return get_search_url()

    def compare_item(self, item_rsp, local_site_name):
        if local_site_name:
            local_site = LocalSite.objects.get(name=local_site_name)
            self.assertEqual(len(item_rsp['users']), local_site.users.count())
        else:
            self.assertEqual(len(item_rsp['users']), User.objects.count())

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        return (get_search_url(local_site_name),
                search_mimetype,
                local_site_name)

    def test_get_with_max_results(self):
        """Testing the GET search/ API with max_results"""
        for i in range(20):
            self.create_review_request(public=True)

        max_results = 10

        rsp = self.api_get(get_search_url(),
                           query={'max_results': max_results},
                           expected_mimetype=search_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), max_results)

    def test_get_private_review_group(self):
        """Testing the GET search/ API with an invite-only review group"""
        group = self.create_review_group(invite_only=True)

        self.assertFalse(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    def test_get_private_review_group_superuser(self):
        """Testing the GET search/ API with an invite-only review group as a
        superuser
        """
        self.user = self._login_user(admin=True)
        group = self.create_review_group(invite_only=True)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_private_review_group_superuser_local_site(self):
        """Testing the GET search/ API with an invite-only review group on a
        Local Site as a superuser
        """
        self.user = self._login_user(admin=True)
        group = self.create_review_group(invite_only=True,
                                         with_local_site=True)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_private_review_group_local_site(self):
        """Testing the GET search/ API with access to a Local Site and an
        invite-only review group
        """
        self._login_user(local_site=True)
        group = self.create_review_group(invite_only=True,
                                         with_local_site=True)

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    @add_fixtures(['test_site'])
    def test_get_review_group_different_site(self):
        """Testing the GET search/ API with a group on a different site"""
        group = self.create_review_group(with_local_site=True)

        self.assertFalse(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    @add_fixtures(['test_site'])
    def test_get_review_group_global_from_site(self):
        """Testing the GET search/ API with access to a Local Site with a group
        on the global site
        """
        self.user = self._login_user(local_site=True)
        group = self.create_review_group()

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    def test_get_private_review_group_member(self):
        """Testing the GET search/ API with access to an invite-only review
        group
        """
        group = self.create_review_group(invite_only=True)
        group.users.add(self.user)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['groups']), 1)

    @add_fixtures(['test_site'])
    def test_get_private_review_group_member_local_site(self):
        """Testing the GET search/ API with access to an invite-only review
        group on a Local Site
        """
        self.user = self._login_user(local_site=True)
        group = self.create_review_group(invite_only=True,
                                         with_local_site=True)
        group.users.add(self.user)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['groups']), 1)

    def test_get_invisible_review_group(self):
        """Testing the GET search/ API with an invisible review group"""
        group = self.create_review_group(visible=False)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    def test_get_invisible_review_group_superuser(self):
        """Testing the GET search/ API with an invisible review group as a
        superuser
        """
        self.user = self._login_user(admin=True)
        group = self.create_review_group(visible=False)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    @add_fixtures(['test_site'])
    def test_get_invisible_review_group_local_site(self):
        """Testing the GET search/ API with an invisible review group on a
        Local Site
        """
        self.user = self._login_user(local_site=True)
        group = self.create_review_group(visible=False, with_local_site=True)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    @add_fixtures(['test_site'])
    def test_get_invisible_review_group_local_site_superuser(self):
        """Testing the GET search/ API with an invisible review group on a
        Local Site as a superuser
        """
        self.user = self._login_user(admin=True)
        group = self.create_review_group(visible=False, with_local_site=True)

        self.assertTrue(group.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': group.name},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    def test_get_review_request_draft_only(self):
        """Testing the GET search/ API with a draft review request"""
        review_request = self.create_review_request(public=False)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    def test_get_review_request_draft_only_superuser(self):
        """Testing the GET search/ API with a draft review request as a
        superuser
        """
        self.user = self._login_user(admin=True)
        review_request = self.create_review_request(public=False)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['groups'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_draft_local_site(self):
        """Testing the GET search/ API with a draft review request on a Local
        Site
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(with_local_site=True,
                                                    submitter='admin')

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_draft_local_site_superuser(self):
        """Testing the GET search/ API with a draft review request on a Local
        Site as a superuser
        """
        self.user = self._login_user(admin=True)
        review_request = self.create_review_request(with_local_site=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_different_local_site(self):
        """Testing the GET search/ API with a review request on a different
        Local Site
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(with_local_site=True,
                                                    submitter='admin',
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_different_local_site_superuser(self):
        """Testing the GET search/ API with a review request on a different
        Local Site as a superuser
        """
        self.user = self._login_user(admin=True)
        review_request = self.create_review_request(with_local_site=True,
                                                    submitter='admin',
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_global_site(self):
        """Testing the GET search/ API with a review request on a global site
        from a Local Site
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_global_site_superuser(self):
        """Testing the GET search/ API with a review request on a global site
        from a Local Site as superuser
        """
        self.user = self._login_user(admin=True)
        review_request = self.create_review_request(public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_local_site(self):
        """Testing the GET search/ API with a review request on a Local Site
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter='admin',
                                                    with_local_site=True,
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_local_site_no_pk_query_q(self):
        """Testing the GET search/ API with a review request on a Local Site
        cannot be queried by the PK using q=
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter='admin',
                                                    with_local_site=True,
                                                    public=True,
                                                    local_id=9999)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_local_site_no_pk_query_id(self):
        """Testing the GET search/ API with a review request on a Local Site
        cannot be queried by the PK using id=
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter='admin',
                                                    with_local_site=True,
                                                    public=True,
                                                    local_id=9999)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'id': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_local_site_local_id_query_q(self):
        """Testing the GET search/ API with a review request on a Local Site
        can be queried by the local ID using q=
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter='admin',
                                                    with_local_site=True,
                                                    public=True,
                                                    local_id=9999)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_local_site_local_id_query_id(self):
        """Testing the GET search/ API with a review request on a Local Site
        can be queried by the local ID using id=
        """
        self.user = self._login_user(local_site=True)
        review_request = self.create_review_request(submitter='admin',
                                                    with_local_site=True,
                                                    public=True,
                                                    local_id=9999)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'id': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    def test_get_review_request_submitted(self):
        """Testing the GET search/ API with a review request closed as
        submitted
        """
        review_request = self.create_review_request(public=True)
        review_request.close(review_request.SUBMITTED)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

        review_request_rsp = rsp['search']['review_requests'][0]
        self.assertEqual(review_request_rsp['id'], review_request.pk)
        self.assertEqual(review_request_rsp['status'], 'submitted')

    def test_get_review_request_discarded(self):
        """Testing the GET search/ API with a review request closed as
        discarded
        """
        review_request = self.create_review_request(public=True)
        review_request.close(review_request.DISCARDED)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

        review_request_rsp = rsp['search']['review_requests'][0]
        self.assertEqual(review_request_rsp['id'], review_request.pk)
        self.assertEqual(review_request_rsp['status'], 'discarded')

    def test_get_review_request_invite_only_group(self):
        """Testing the GET search/ API with a review request assigned to an
        invite-only group not containing the user
        """
        review_group = self.create_review_group(invite_only=True)
        review_request = self.create_review_request(public=True)
        review_request.target_groups.add(review_group)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_site'])
    def test_get_review_request_invite_only_group_local_site(self):
        """Testing the GET search/ API with a review request assigned to an
        invite-only group on a Local Site
        """
        self.user = self._login_user(local_site=True)
        review_group = self.create_review_group(invite_only=True,
                                                with_local_site=True)
        review_request = self.create_review_request(public=True,
                                                    submitter='admin',
                                                    with_local_site=True)
        review_request.target_groups.add(review_group)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    def test_get_review_request_invite_only_group_superuser(self):
        """Testing the GET search/ API with a review request assigned to an
        invite-only group as a superuser
        """
        self.user = self._login_user(admin=True)
        review_group = self.create_review_group(invite_only=True)
        review_request = self.create_review_request(public=True)
        review_request.target_groups.add(review_group)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_invite_only_group_local_site_superuser(self):
        """Testing the GET search/ API with a review request assigned to an
        invite-only group on a Local Site as a superuser
        """
        self.user = self._login_user(admin=True)
        review_group = self.create_review_group(invite_only=True,
                                                with_local_site=True)
        review_request = self.create_review_request(public=True,
                                                    submitter='doc',
                                                    with_local_site=True)
        review_request.target_groups.add(review_group)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_scmtools'])
    def test_get_review_request_private_repository(self):
        """Testing the GET search/ API with a review request in a private
        repository
        """
        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    public=True)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_scmtools'])
    def test_get_review_request_private_repository_member(self):
        """Testing the GET search/ API with a review request in a private
        repository with access
        """
        repository = self.create_repository(public=False)
        repository.users.add(self.user)
        review_request = self.create_review_request(repository=repository,
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_scmtools'])
    def test_get_review_request_private_repository_superuser(self):
        """Testing the GET search/ API with a review request in a private
        repository as a superuser
        """
        self.user = self._login_user(admin=True)
        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_review_request_private_repository_local_site(self):
        """Testing the GET search/ API with a review request in a private
        repository on a Local Site
        """
        self.user = self._login_user(local_site=True)
        repository = self.create_repository(public=False,
                                            with_local_site=True)
        review_request = self.create_review_request(repository=repository,
                                                    with_local_site=True,
                                                    submitter='admin',
                                                    public=True)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_review_request_private_repository_local_site_member(self):
        """Testing the GET search/ PAI with a review request in a private
        repository on a Local Site with access
        """
        self.user = self._login_user(local_site=True)
        repository = self.create_repository(public=False,
                                            with_local_site=True)
        repository.users.add(self.user)
        review_request = self.create_review_request(repository=repository,
                                                    with_local_site=True,
                                                    submitter='admin',
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_review_request_private_repository_local_site_superuser(self):
        """Testing the GET search/ API with a review request in a private
        repository on a Local Site as a superuser
        """
        self.user = self._login_user(admin=True)
        repository = self.create_repository(public=False,
                                            with_local_site=True)
        review_request = self.create_review_request(repository=repository,
                                                    with_local_site=True,
                                                    submitter='doc',
                                                    public=True)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_scmtools'])
    def test_get_review_request_private_repo_access_invite_only(self):
        """Testing the GET search/ API with a review request in a private
        repository and assigned to an invite-only group that contains the user
        """
        repository = self.create_repository(public=False)
        review_group = self.create_review_group(invite_only=True)
        review_group.users.add(self.user)

        review_request = self.create_review_request(repository=repository,
                                                    public=True)
        review_request.target_groups.add(review_group)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_review_request_private_repo_access_invite_only_site(self):
        """Testing the GET search/ API with a review request on a Local Site in
        a private repository and assigned to an invite-only group that contains
        the user
        """
        self.user = self._login_user(local_site=True)
        repository = self.create_repository(public=False,
                                            with_local_site=True)
        review_group = self.create_review_group(invite_only=True,
                                                with_local_site=True)
        review_group.users.add(self.user)

        review_request = self.create_review_request(repository=repository,
                                                    with_local_site=True,
                                                    submitter='admin',
                                                    public=True)
        review_request.target_groups.add(review_group)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_scmtools'])
    def test_get_review_request_private_repo_access_assigned(self):
        """Testing the GET search/ API with a review request in a private
        repository and assigned to the user
        """
        repository = self.create_repository(public=False)
        review_request = self.create_review_request(repository=repository,
                                                    public=True)
        review_request.target_people.add(self.user)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    @add_fixtures(['test_scmtools', 'test_site'])
    def test_get_review_request_private_repo_access_assigned_site(self):
        """Testing the GET search/ API with a review request on a Local Site in
        a private repository and assigned to the user
        """
        self.user = self._login_user(local_site=True)
        repository = self.create_repository(public=False,
                                            with_local_site=True)
        review_request = self.create_review_request(repository=repository,
                                                    with_local_site=True,
                                                    submitter='admin',
                                                    public=True)
        review_request.target_people.add(self.user)

        self.assertFalse(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['search']['review_requests'], [])

    def test_get_review_request_private_multi_groups(self):
        """Testing the GET search/ API with a review request assigned to
        multiple private groups, one containing the user
        """
        non_member_group = self.create_review_group(invite_only=True,
                                                    name='non-member')
        member_group = self.create_review_group(invite_only=True,
                                                name='member')
        member_group.users.add(self.user)
        review_request = self.create_review_request(public=True)
        review_request.target_groups = [
            member_group,
            non_member_group,
        ]

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_private_multi_groups_site(self):
        """Testing the GET search/ API with a review request on a Local Site
        assigned to multiple private groups, one containing the user
        """
        self.user = self._login_user(local_site=True)
        non_member_group = self.create_review_group(invite_only=True,
                                                    name='non-member',
                                                    with_local_site=True)
        member_group = self.create_review_group(invite_only=True,
                                                name='member',
                                                with_local_site=True)
        member_group.users.add(self.user)
        review_request = self.create_review_request(public=True,
                                                    with_local_site=True,
                                                    submitter='admin')
        review_request.target_groups = [
            member_group,
            non_member_group,
        ]

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    def test_get_review_request_private_public_groups(self):
        """Testing the GET search/ API with a review request assigned to
        public and private groups
        """
        private_group = self.create_review_group(invite_only=True,
                                                 name='private')
        public_group = self.create_review_group(name='public')
        review_request = self.create_review_request(public=True)
        review_request.target_groups = [
            public_group,
            private_group,
        ]

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_private_public_groups_site(self):
        """Testing the GET search/ API with a review request on a Local Site
        assigned to public and private groups
        """
        self.user = self._login_user(local_site=True)
        private_group = self.create_review_group(invite_only=True,
                                                 name='private',
                                                 with_local_site=True)
        public_group = self.create_review_group(name='public',
                                                with_local_site=True)
        review_request = self.create_review_request(public=True,
                                                    with_local_site=True,
                                                    submitter='admin')
        review_request.target_groups = [
            public_group,
            private_group,
        ]

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    def test_get_review_request_private_public_groups_targeted(self):
        """Testing the GET search/ API with a review request assigned to public
        and private groups
        """
        private_group = self.create_review_group(invite_only=True)
        review_request = self.create_review_request(public=True)
        review_request.target_groups.add(private_group)
        review_request.target_people.add(self.user)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(),
                           query={'q': review_request.pk},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)

    @add_fixtures(['test_site'])
    def test_get_review_request_private_public_groups_targeted_site(self):
        """Testing the GET search/ API with a review request on a Local Site
        assigned to public and private groups
        """
        self.user = self._login_user(local_site=True)
        private_group = self.create_review_group(invite_only=True,
                                                 with_local_site=True)
        review_request = self.create_review_request(public=True,
                                                    with_local_site=True,
                                                    submitter='admin')
        review_request.target_groups.add(private_group)
        review_request.target_people.add(self.user)

        self.assertTrue(review_request.is_accessible_by(self.user))

        rsp = self.api_get(get_search_url(self.local_site_name),
                           query={'q': review_request.local_id},
                           expected_mimetype=search_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['search']['review_requests']), 1)
