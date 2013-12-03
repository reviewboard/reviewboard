from __future__ import unicode_literals

from django.contrib.auth.models import User, Permission
from django.db.models import Q
from djblets.db.query import get_object_or_none
from djblets.testing.decorators import add_fixtures
from djblets.util.compat import six
from djblets.webapi.errors import DOES_NOT_EXIST, PERMISSION_DENIED

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.reviews.models import ReviewRequest
from reviewboard.site.models import LocalSite
from reviewboard.webapi.errors import INVALID_REPOSITORY
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (review_request_item_mimetype,
                                                review_request_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (get_repository_item_url,
                                           get_review_request_item_url,
                                           get_review_request_list_url,
                                           get_user_item_url)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(BaseWebAPITestCase):
    """Testing the ReviewRequestResource list API tests."""
    fixtures = ['test_users']
    basic_post_fixtures = ['test_scmtools']
    sample_api_url = 'review-requests/'
    resource = resources.review_request

    def compare_item(self, item_rsp, review_request):
        self.assertEqual(item_rsp['id'], review_request.display_id)
        self.assertEqual(item_rsp['summary'], review_request.summary)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        if populate_items:
            if not with_local_site:
                LocalSite.objects.create(name=self.local_site_name)

            items = [
                self.create_review_request(
                    publish=True,
                    submitter=user,
                    with_local_site=with_local_site),
            ]

            self.create_review_request(publish=True,
                                       submitter=user,
                                       with_local_site=not with_local_site)
        else:
            items = []

        return (get_review_request_list_url(local_site_name),
                review_request_list_mimetype,
                items)

    @add_fixtures(['test_site'])
    def test_get_with_status(self):
        """Testing the GET review-requests/?status= API"""
        self.create_review_request(publish=True, status='S')
        self.create_review_request(publish=True, status='S')
        self.create_review_request(publish=True, status='D')
        self.create_review_request(publish=True, status='P')
        self.create_review_request(publish=True, status='P')
        self.create_review_request(publish=True, status='P')

        url = get_review_request_list_url()

        rsp = self.apiGet(url, {'status': 'submitted'},
                          expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

        rsp = self.apiGet(url, {'status': 'discarded'},
                          expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.apiGet(url, {'status': 'all'},
                          expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 6)

    def test_get_with_counts_only(self):
        """Testing the GET review-requests/?counts-only=1 API"""
        self.create_review_request(publish=True)
        self.create_review_request(publish=True)

        rsp = self.apiGet(get_review_request_list_url(), {
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_groups(self):
        """Testing the GET review-requests/?to-groups= API"""
        group = self.create_review_group(name='devgroup')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        rsp = self.apiGet(get_review_request_list_url(), {
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

    def test_get_with_to_groups_and_status(self):
        """Testing the GET review-requests/?to-groups=&status= API"""
        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='S')
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_groups.add(group)

        url = get_review_request_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-groups': 'devgroup',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_groups_and_counts_only(self):
        """Testing the GET review-requests/?to-groups=&counts-only=1 API"""
        group = self.create_review_group(name='devgroup')

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        review_request = self.create_review_request(publish=True)
        review_request.target_groups.add(group)

        rsp = self.apiGet(get_review_request_list_url(), {
            'to-groups': 'devgroup',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_users(self):
        """Testing the GET review-requests/?to-users= API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        rsp = self.apiGet(get_review_request_list_url(), {
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_users_and_status(self):
        """Testing the GET review-requests/?to-users=&status= API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True, status='S')
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True, status='D')
        review_request.target_people.add(grumpy)

        url = get_review_request_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-users': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 2)

    def test_get_with_to_users_and_counts_only(self):
        """Testing the GET review-requests/?to-users=&counts-only=1 API"""
        grumpy = User.objects.get(username='grumpy')

        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        review_request = self.create_review_request(publish=True)
        review_request.target_people.add(grumpy)

        rsp = self.apiGet(get_review_request_list_url(), {
            'to-users': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], 2)

    def test_get_with_to_users_directly(self):
        """Testing the GET review-requests/?to-users-directly= API"""
        rsp = self.apiGet(get_review_request_list_url(), {
            'to-users-directly': 'doc',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_with_to_users_directly_and_status(self):
        """Testing the GET review-requests/?to-users-directly=&status= API"""
        url = get_review_request_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'to-users-directly': 'doc'
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'to-users-directly': 'doc'
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def test_get_with_to_users_directly_and_counts_only(self):
        """Testing the
        GET review-requests/?to-users-directly=&counts-only=1 API
        """
        rsp = self.apiGet(get_review_request_list_url(), {
            'to-users-directly': 'doc',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def test_get_with_from_user(self):
        """Testing the GET review-requests/?from-user= API"""
        rsp = self.apiGet(get_review_request_list_url(), {
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_get_with_from_user_and_status(self):
        """Testing the GET review-requests/?from-user=&status= API"""
        url = get_review_request_list_url()

        rsp = self.apiGet(url, {
            'status': 'submitted',
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.apiGet(url, {
            'status': 'discarded',
            'from-user': 'grumpy',
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def test_get_with_from_user_and_counts_only(self):
        """Testing the GET review-requests/?from-user=&counts-only=1 API"""
        rsp = self.apiGet(get_review_request_list_url(), {
            'from-user': 'grumpy',
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    def test_get_with_ship_it_0(self):
        """Testing the GET review-requests/?ship-it=0 API"""
        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, ship_it=True, publish=True)

        rsp = self.apiGet(get_review_request_list_url(), {
            'ship-it': 0,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    def test_get_with_ship_it_1(self):
        """Testing the GET review-requests/?ship-it=1 API"""
        self.create_review_request(publish=True)

        review_request = self.create_review_request(publish=True)
        self.create_review(review_request, ship_it=True, publish=True)

        rsp = self.apiGet(get_review_request_list_url(), {
            'ship-it': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)

        q = ReviewRequest.objects.public(user=self.user,
                                         status='P',
                                         extra_query=Q(shipit_count__gt=0))
        self.assertEqual(len(rsp['review_requests']), q.count())

    def test_get_with_time_added_from(self):
        """Testing the GET review-requests/?time-added-from= API"""
        start_index = 3

        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.apiGet(get_review_request_list_url(), {
            'time-added-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                time_added__gte=r.time_added).count())

    def test_get_with_time_added_to(self):
        """Testing the GET review-requests/?time-added-to= API"""
        start_index = 3

        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.time_added.isoformat()

        rsp = self.apiGet(get_review_request_list_url(), {
            'time-added-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index + 1)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                time_added__lt=r.time_added).count())

    def test_get_with_last_updated_from(self):
        """Testing the GET review-requests/?last-updated-from= API"""
        start_index = 3
        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.apiGet(get_review_request_list_url(), {
            'last-updated-from': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                last_updated__gte=r.last_updated).count())

    def test_get_with_last_updated_to(self):
        """Testing the GET review-requests/?last-updated-to= API"""
        start_index = 3
        public_review_requests = [
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
            self.create_review_request(publish=True),
        ]

        r = public_review_requests[start_index]
        timestamp = r.last_updated.isoformat()

        rsp = self.apiGet(get_review_request_list_url(), {
            'last-updated-to': timestamp,
            'counts-only': 1,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         len(public_review_requests) - start_index + 1)
        self.assertEqual(
            rsp['count'],
            ReviewRequest.objects.filter(
                public=True, status='P',
                last_updated__lt=r.last_updated).count())

    @add_fixtures(['test_scmtools'])
    def test_get_with_repository_and_changenum(self):
        """Testing the GET review-requests/?repository=&changenum= API"""
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.changenum = 1234
        review_request.save()

        rsp = self.apiGet(get_review_request_list_url(), {
            'repository': review_request.repository.id,
            'changenum': review_request.changenum,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_requests'][0]['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_requests'][0]['changenum'],
                         review_request.changenum)
        self.assertEqual(rsp['review_requests'][0]['commit_id'],
                         review_request.commit)

    @add_fixtures(['test_scmtools'])
    def test_get_with_repository_and_commit_id(self):
        """Testing the GET review-requests/?repository=&commit_id= API
        with changenum backwards-compatibility
        """
        review_request = self.create_review_request(create_repository=True,
                                                    publish=True)
        review_request.changenum = 1234
        review_request.save()

        self.assertEqual(review_request.commit_id, None)

        commit_id = six.text_type(review_request.changenum)

        rsp = self.apiGet(get_review_request_list_url(), {
            'repository': review_request.repository.id,
            'commit_id': review_request.commit,
        }, expected_mimetype=review_request_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']), 1)
        self.assertEqual(rsp['review_requests'][0]['id'],
                         review_request.display_id)
        self.assertEqual(rsp['review_requests'][0]['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_requests'][0]['changenum'],
                         review_request.changenum)
        self.assertEqual(rsp['review_requests'][0]['commit_id'],
                         commit_id)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(self, user, with_local_site, local_site_name,
                              post_valid_data):
        if post_valid_data:
            repository = \
                self.create_repository(with_local_site=with_local_site)

            post_data = {
                'repository': repository.path,
            }
        else:
            post_data = {}

        return (get_review_request_list_url(local_site_name),
                review_request_item_mimetype,
                post_data,
                [])

    def check_post_result(self, user, rsp):
        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    @add_fixtures(['test_scmtools'])
    def test_post_with_repository_name(self):
        """Testing the POST review-requests/ API with a repository name"""
        repository = self.create_repository()

        rsp = self.apiPost(
            get_review_request_list_url(),
            {'repository': repository.name},
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['repository']['href'],
            self.base_url + get_repository_item_url(repository))

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    @add_fixtures(['test_scmtools'])
    def test_post_with_no_repository(self):
        """Testing the POST review-requests/ API with no repository"""
        rsp = self.apiPost(
            get_review_request_list_url(),
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        self.assertFalse('repository' in rsp['review_request']['links'])

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        review_request = ReviewRequest.objects.get(
            pk=rsp['review_request']['id'])
        self.assertEqual(review_request.repository, None)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_post_with_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API
        with a local site and Invalid Repository error
        """
        repository = self.create_repository()

        self._login_user(local_site=True)
        rsp = self.apiPost(
            get_review_request_list_url(self.local_site_name),
            {'repository': repository.path},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_with_invalid_repository_error(self):
        """Testing the POST review-requests/ API
        with Invalid Repository error
        """
        rsp = self.apiPost(
            get_review_request_list_url(),
            {'repository': 'gobbledygook'},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    @add_fixtures(['test_site', 'test_scmtools'])
    def test_post_with_no_site_invalid_repository_error(self):
        """Testing the POST review-requests/ API with
        Invalid Repository error from a site-local repository
        """
        repository = self.create_repository(with_local_site=True)

        rsp = self.apiPost(
            get_review_request_list_url(),
            {'repository': repository.path},
            expected_status=400)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], INVALID_REPOSITORY.code)

    def test_post_with_submit_as_and_permission(self):
        """Testing the POST review-requests/?submit_as= API
        with permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_submit_as_another_user'))

        self._test_post_with_submit_as()

    def test_post_with_submit_as_and_admin(self):
        """Testing the POST review-requests/?submit_as= API
        with administrator
        """
        self.user.is_superuser = True
        self.user.save()

        self._test_post_with_submit_as()

    @add_fixtures(['test_site'])
    def test_post_with_submit_as_and_site_permission(self):
        """Testing the POST review-requests/?submit_as= API
        with a local site and local permission
        """
        self.user = self._login_user(local_site=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            local_site=local_site,
            user=self.user,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.can_submit_as_another_user'] = True
        site_profile.save()

        self._test_post_with_submit_as(local_site)

    @add_fixtures(['test_site'])
    def test_post_with_submit_as_and_site_admin(self):
        """Testing the POST review-requests/?submit_as= API
        with a local site and site admin
        """
        self._login_user(local_site=True, admin=True)

        self._test_post_with_submit_as(
            LocalSite.objects.get(name=self.local_site_name))

    @add_fixtures(['test_scmtools'])
    def test_post_with_submit_as_and_permission_denied_error(self):
        """Testing the POST review-requests/?submit_as= API
        with Permission Denied error
        """
        repository = self.create_repository()

        rsp = self.apiPost(
            get_review_request_list_url(),
            {
                'repository': repository.path,
                'submit_as': 'doc',
            },
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def _test_post_with_submit_as(self, local_site=None):
        submit_as_username = 'dopey'

        self.assertNotEqual(self.user.username, submit_as_username)

        if local_site:
            local_site_name = local_site.name
            local_site.users.add(User.objects.get(username=submit_as_username))
        else:
            local_site_name = None

        rsp = self.apiPost(
            get_review_request_list_url(local_site_name),
            {
                'submit_as': submit_as_username,
            },
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(
            rsp['review_request']['links']['submitter']['href'],
            self.base_url +
            get_user_item_url(submit_as_username, local_site_name))

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase):
    """Testing the ReviewRequestResource item API tests."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/'
    resource = resources.review_request
    test_http_methods = ('DELETE', 'GET')

    def compare_item(self, item_rsp, review_request):
        self.assertEqual(item_rsp['id'], review_request.display_id)
        self.assertEqual(item_rsp['summary'], review_request.summary)
        self.assertEqual(item_rsp['absolute_url'],
                         self.base_url + review_request.get_absolute_url())

    #
    # HTTP DELETE tests
    #

    def setup_basic_delete_test(self, user, with_local_site, local_site_name):
        user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.assertTrue(user.has_perm('reviews.delete_reviewrequest'))

        review_request = self.create_review_request(
            submitter=user,
            with_local_site=with_local_site,
            publish=True)

        return (get_review_request_item_url(review_request.display_id,
                                            local_site_name),
                [review_request.pk])

    def check_delete_result(self, user, review_request_id):
        self.assertIsNone(get_object_or_none(ReviewRequest,
                                             pk=review_request_id))

    def test_delete_with_permission_denied_error(self):
        """Testing the DELETE review-requests/<id>/ API
        without permission and with Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.apiDelete(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_delete_with_does_not_exist_error(self):
        """Testing the DELETE review-requests/<id>/ API
        with Does Not Exist error
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assertTrue(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.apiDelete(get_review_request_item_url(999),
                             expected_status=404)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], DOES_NOT_EXIST.code)

    @add_fixtures(['test_site'])
    def test_delete_with_site_and_local_permission(self):
        """Testing the DELETE review-requests/<id>/ API
        with a local site and a local permission is not allowed
        """
        self.user = self._login_user(local_site=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            user=self.user,
            local_site=local_site,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.delete_reviewrequest'] = True
        site_profile.save()

        review_request = self.create_review_request(with_local_site=True)

        rsp = self.apiDelete(
            get_review_request_item_url(review_request.display_id,
                                        self.local_site_name),
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_delete_with_site_and_site_admin(self):
        """Testing the DELETE review-requests/<id>/ API
        with a local site and a site admin is not allowed
        """
        user = User.objects.get(username='doc')

        self.user = self._login_user(local_site=True, admin=True)
        local_site = LocalSite.objects.get(name=self.local_site_name)

        review_request = self.create_review_request(with_local_site=True)

        rsp = self.apiDelete(
            get_review_request_item_url(review_request.display_id,
                                        self.local_site_name),
            expected_status=403)


    #
    # HTTP GET tests
    #

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        review_request = self.create_review_request(
            with_local_site=with_local_site,
            publish=True)

        return (get_review_request_item_url(review_request.display_id,
                                            local_site_name),
                review_request_item_mimetype,
                review_request)

    def test_get_with_non_public_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API
        with non-public and Permission Denied error
        """
        review_request = self.create_review_request(public=False)
        self.assertNotEqual(review_request.submitter, self.user)

        rsp = self.apiGet(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_with_invite_only_group_and_permission_denied_error(self):
        """Testing the GET review-requests/<id>/ API
        with invite-only group and Permission Denied error
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.save()

        rsp = self.apiGet(
            get_review_request_item_url(review_request.display_id),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    def test_get_with_invite_only_group_and_target_user(self):
        """Testing the GET review-requests/<id>/ API
        with invite-only group and target user
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter, self.user)

        group = self.create_review_group(invite_only=True)

        review_request.target_groups.add(group)
        review_request.target_people.add(self.user)
        review_request.save()

        rsp = self.apiGet(
            get_review_request_item_url(review_request.display_id),
            expected_mimetype=review_request_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.display_id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    @add_fixtures(['test_site'])
    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)

        self._testHttpCaching(get_review_request_item_url(review_request.id),
                              check_last_modified=True)

    #
    # HTTP PUT tests
    #

    def test_put_status_discarded(self):
        """Testing the PUT review-requests/<id>/?status=discarded API"""
        r = self.create_review_request(submitter=self.user, publish=True)

        rsp = self.apiPut(
            get_review_request_item_url(r.display_id),
            {
                'status': 'discarded',
                'description': 'comment',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'D')

    def test_put_status_discarded_with_permission_denied(self):
        """Testing the PUT review-requests/<id>/?status=discarded API
        with Permission Denied
        """
        r = self.create_review_request()
        self.assertNotEqual(r.submitter, self.user)

        rsp = self.apiPut(
            get_review_request_item_url(r.display_id),
            {'status': 'discarded'},
            expected_status=403)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_put_status_pending(self):
        """Testing the PUT review-requests/<id>/?status=pending API"""
        r = self.create_review_request(submitter=self.user, publish=True)
        r.close(ReviewRequest.SUBMITTED)
        r.save()

        rsp = self.apiPut(
            get_review_request_item_url(r.display_id),
            {'status': 'pending'},
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'P')

    def test_put_status_submitted(self):
        """Testing the PUT review-requests/<id>/?status=submitted API"""
        r = self.create_review_request(submitter=self.user, publish=True)

        rsp = self.apiPut(
            get_review_request_item_url(r.display_id),
            {
                'status': 'submitted',
                'description': 'comment',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_status_submitted_with_site(self):
        """Testing the PUT review-requests/<id>/?status=submitted API
        with a local site
        """
        self._login_user(local_site=True)
        r = self.create_review_request(submitter='doc', with_local_site=True,
                                       publish=True)

        rsp = self.apiPut(
            get_review_request_item_url(r.display_id, self.local_site_name),
            {
                'status': 'submitted',
                'description': 'comment'
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

        c = r.changedescs.latest('timestamp')
        self.assertEqual(c.text, 'comment')

        fc_status = c.fields_changed['status']
        self.assertEqual(fc_status['old'][0], 'P')
        self.assertEqual(fc_status['new'][0], 'S')

    @add_fixtures(['test_site'])
    def test_put_status_submitted_with_site_no_access(self):
        """Testing the PUT review-requests/<id>/?status=submitted API
        with a local site and Permission Denied error
        """
        r = self.create_review_request(submitter='doc', with_local_site=True,
                                       publish=True)

        self.apiPut(
            get_review_request_item_url(r.display_id, self.local_site_name),
            {'status': 'submitted'},
            expected_status=403)

    def test_put_status_as_other_user_with_permission(self):
        """Testing the PUT review-requests/<id>/?status= API
        as another user with permission
        """
        self.user.user_permissions.add(
            Permission.objects.get(codename='can_change_status'))

        self._test_put_status_as_other_user()

    def test_put_status_as_other_user_with_admin(self):
        """Testing the PUT review-requests/<id>/?status= API
        as another user with admin
        """
        self._login_user(admin=True)

        self._test_put_status_as_other_user()

    def test_put_status_as_other_user_not_allowed(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user not allowed
        """
        review_request = self.create_review_request(publish=True)
        self.assertNotEqual(review_request.submitter.username,
                            self.user.username)

        self.apiPut(
            get_review_request_item_url(review_request.display_id),
            {
                'status': 'submitted',
            },
            expected_status=403)

    @add_fixtures(['test_site'])
    def test_put_status_as_other_user_with_site_and_permission(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user with local site and permission
        """
        self.user = self._login_user(local_site=True)

        local_site = LocalSite.objects.get(name=self.local_site_name)

        site_profile = LocalSiteProfile.objects.create(
            local_site=local_site,
            user=self.user,
            profile=self.user.get_profile())
        site_profile.permissions['reviews.can_change_status'] = True
        site_profile.save()

        self._test_put_status_as_other_user(local_site)

    @add_fixtures(['test_site'])
    def test_put_status_as_other_user_with_site_and_admin(self):
        """Testing the PUT review-requests/<id>/?status=pending API
        as another user with local site and admin
        """
        self.user = self._login_user(local_site=True, admin=True)

        self._test_put_status_as_other_user(
            LocalSite.objects.get(name=self.local_site_name))

    def _test_put_status_as_other_user(self, local_site=None):
        review_request = self.create_review_request(
            submitter='dopey',
            publish=True,
            with_local_site=(local_site is not None))

        if local_site:
            local_site_name = local_site.name
        else:
            local_site_name = None

        rsp = self.apiPut(
            get_review_request_item_url(review_request.display_id,
                                        local_site_name),
            {
                'status': 'submitted',
            },
            expected_mimetype=review_request_item_mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.status, 'S')
