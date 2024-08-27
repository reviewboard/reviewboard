"""Unit tests for the HostingServiceAccountResource."""

from __future__ import annotations

from typing import Any, Optional, Sequence, TYPE_CHECKING

from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (
    hosting_service_account_item_mimetype,
    hosting_service_account_list_mimetype)
from reviewboard.webapi.tests.mixins import BasicTestsMetaclass
from reviewboard.webapi.tests.urls import (
    get_hosting_service_account_item_url,
    get_hosting_service_account_list_url)

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from djblets.util.typing import JSONDict


class ResourceListTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the HostingServiceAccountResource list APIs."""

    sample_api_url = 'hosting-services-accounts/'
    resource = resources.hosting_service_account
    fixtures = ['test_users']

    basic_post_use_admin = True

    def compare_item(
        self,
        item_rsp: JSONDict,
        account: HostingServiceAccount,
    ) -> None:
        """Compare an API response to an item.

        Args:
            item_rsp (dict):
                The API response.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account object to compare to.
        """
        self.assertEqual(item_rsp['id'], account.pk)
        self.assertEqual(item_rsp['username'], account.username)
        self.assertEqual(item_rsp['service'],
                         account.service.hosting_service_id)

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for item access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        return get_hosting_service_account_list_url()

    def setup_http_not_allowed_list_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for list access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        return get_hosting_service_account_list_url()

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        populate_items: bool,
    ) -> tuple[str, str, list[HostingServiceAccount]]:
        """Set up a basic HTTP GET test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether to run the tests against a Local Site.

            local_site_name (str):
                The name of the Local Site to use.

            populate_items (bool):
                Whether to populate items in the database.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL to use for accessing the resource.

                1 (str):
                    The expected mimetype for responses.

                2 (list):
                    A list of accounts that are expected to be in the response.
        """
        if populate_items:
            if with_local_site:
                assert local_site_name is not None
                local_site = self.get_local_site(name=local_site_name)
            else:
                local_site = None

            accounts = [
                HostingServiceAccount.objects.create(
                    service_name='googlecode',
                    username='bob',
                    local_site=local_site),
            ]
        else:
            accounts = []

        return (get_hosting_service_account_list_url(local_site_name),
                hosting_service_account_list_mimetype,
                accounts)

    @webapi_test_template
    def test_get_with_service(self) -> None:
        """Testing the GET <URL>?service= API"""
        HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='bob')

        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='bob')

        rsp = self.api_get(
            get_hosting_service_account_list_url(),
            data={'service': 'github'},
            expected_mimetype=hosting_service_account_list_mimetype)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['hosting_service_accounts']), 1)
        self.compare_item(rsp['hosting_service_accounts'][0], account)

    @webapi_test_template
    def test_get_with_username(self) -> None:
        """Testing the GET <URL>?username= API"""
        account = HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='bob')

        HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='frank')

        rsp = self.api_get(
            get_hosting_service_account_list_url(),
            data={'username': 'bob'},
            expected_mimetype=hosting_service_account_list_mimetype)
        assert rsp is not None

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['hosting_service_accounts']), 1)
        self.compare_item(rsp['hosting_service_accounts'][0], account)

    #
    # HTTP POST tests
    #

    def setup_basic_post_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        post_valid_data: bool,
    ) -> tuple[str, str, JSONDict, Sequence[Any]]:
        """Set up a basic HTTP POST test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether to run the tests against a Local Site.

            local_site_name (str):
                The name of the Local Site to use.

            post_valid_data (bool):
                Whether to use valid data for the POST body.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (str):
                    The URL to use for accessing the resource.

                1 (str):
                    The expected mimetype of the response.

                2 (dict):
                    The data to send in the POST request.

                3 (list):
                    Additional positional arguments to pass to
                    :py:meth:`check_post_result`.
        """
        if post_valid_data:
            post_data: JSONDict = {
                'username': 'bob',
                'service_id': 'googlecode',
            }
        else:
            post_data = {}

        return (get_hosting_service_account_list_url(local_site_name),
                hosting_service_account_item_mimetype,
                post_data,
                [])

    def check_post_result(
        self,
        user: User,
        rsp: JSONDict,
    ) -> None:
        """Check the result of a POST operation.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            rsp (dict):
                The response content.
        """
        item_rsp = rsp['hosting_service_account']
        account = HostingServiceAccount.objects.get(pk=item_rsp['id'])

        self.compare_item(item_rsp, account)


class ResourceItemTests(BaseWebAPITestCase, metaclass=BasicTestsMetaclass):
    """Unit tests for the HostingServiceAccountResource item APIs."""

    fixtures = ['test_users']
    sample_api_url = 'hosting-service-accounts/<id>/'
    resource = resources.hosting_service_account

    def compare_item(
        self,
        item_rsp: JSONDict,
        account: HostingServiceAccount,
    ) -> None:
        """Compare an API response to an item.

        Args:
            item_rsp (dict):
                The API response.

            account (reviewboard.hostingsvcs.models.HostingServiceAccount):
                The account object to compare to.
        """
        self.assertEqual(item_rsp['id'], account.pk)
        self.assertEqual(item_rsp['username'], account.username)
        self.assertEqual(item_rsp['service'],
                         account.service.hosting_service_id)

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for item access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        account = HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='bob')

        return get_hosting_service_account_item_url(account.pk)

    def setup_http_not_allowed_list_test(
        self,
        user: User,
    ) -> str:
        """Set up the HTTP not allowed test for list access.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to use for accessing the resource.
        """
        account = HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='bob')

        return get_hosting_service_account_item_url(account.pk)

    #
    # HTTP GET tests
    #

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
    ) -> tuple[str, str, HostingServiceAccount]:
        """Set up a basic HTTP GET test.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether to run the tests against a Local Site.

            local_site_name (str):
                The name of the Local Site to use.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL to use for making API requests.

                1 (str):
                    The expected mimetype of the response.

                2 (reviewboard.hostingsvcs.models.HostingServiceAccount):
                    The hosting service account.
        """
        if with_local_site:
            assert local_site_name is not None
            local_site = self.get_local_site(name=local_site_name)
        else:
            local_site = None

        account = HostingServiceAccount.objects.create(
            service_name='googlecode',
            username='bob',
            local_site=local_site)

        return (get_hosting_service_account_item_url(account, local_site_name),
                hosting_service_account_item_mimetype,
                account)
