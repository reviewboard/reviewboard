"""Base helpers for WebAPI unit tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.conf import settings
from djblets.siteconfig.models import SiteConfiguration
from djblets.webapi.testing.testcases import WebAPITestCaseMixin

from reviewboard.notifications.tests.mixins import EmailTestHelper
from reviewboard.testing import TestCase
from reviewboard.webapi.tests.mimetypes import error_mimetype

if TYPE_CHECKING:
    from typelets.funcs import KwargsDict
    from typelets.json import JSONDict

    from django.contrib.auth.models import User


class BaseWebAPITestCase(WebAPITestCaseMixin, EmailTestHelper, TestCase):
    """Base class for WebAPI unit tests.

    This manages initial setup and teardown for unit tests, and provides
    useful utility functions to aid in testing the API.
    """

    #: The base URL to use for absolute URLs.
    #:
    #: Type:
    #:     str:
    base_url = 'http://testserver'

    #: The default error mimetype.
    #:
    #: Type:
    #:     str
    error_mimetype = error_mimetype

    ######################
    # Instance variables #
    ######################

    #: The site configuration used during the API test.
    #:
    #: Type:
    #:     djblets.siteconfig.models.SiteConfiguration
    siteconfig: SiteConfiguration

    #: The currently logged-in user for the test.
    #:
    #: This may be ``None``.
    #:
    #: Type:
    #:     django.contrib.auth.models.User
    user: User | None

    #: Site configuration settings saved prior to the test.
    #:
    #: Type:
    #:     dict
    _saved_siteconfig_settings: JSONDict

    def setUp(self) -> None:
        """Set up the unit test.

        This will temporarily override site configuration settings to block
        all review e-mail code and disable site-wide login requirements. It
        will then set up a user for the test.

        Settings will be restored once the test concludes.
        """
        super().setUp()

        siteconfig = SiteConfiguration.objects.get_current()
        self._saved_siteconfig_settings = siteconfig.settings.copy()

        siteconfig.set('mail_send_review_mail', False)
        siteconfig.set('auth_require_sitewide_login', False)
        siteconfig.save()

        self.siteconfig = siteconfig

        if 'test_users' in (getattr(self, 'fixtures', None) or []):
            self.user = self.login_user()
        else:
            self.user = None

    def tearDown(self) -> None:
        """Tear down the unit test.

        This will restore any previously-changed settings and clear out
        test state.
        """
        super().tearDown()

        siteconfig = self.siteconfig
        siteconfig.settings = self._saved_siteconfig_settings
        siteconfig.save()

        # Clear out state so we don't leak anything.
        #
        # Skip type checking on the siteconfig since we guarantee it's always
        # set when actually used by a test.
        self._saved_siteconfig_settings = None  # type: ignore
        self.siteconfig = None  # type: ignore
        self.user = None

    def _testHttpCaching(
        self,
        url: str,
        *,
        check_etags: bool = False,
        check_last_modified: bool = False,
    ) -> None:
        """Run a test to check for HTTP caching headers.

        Args:
            url (str):
                The URL to request.

            check_etags (bool, optional):
                Whether to check :mailheader:`ETag` headers.

            check_last_modified (bool, optional):
                Whether to check :mailheader:`Last-Modified` headers.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        client = self.client
        response = client.get(url)

        self.assertHttpOK(response, check_etag=check_etags,
                          check_last_modified=check_last_modified)

        headers: KwargsDict = {}

        if check_etags:
            headers['HTTP_IF_NONE_MATCH'] = response['ETag']

        if check_last_modified:
            headers['HTTP_IF_MODIFIED_SINCE'] = response['Last-Modified']

        response = client.get(url, **headers)

        self.assertHttpNotModified(response)

    #
    # Some utility functions shared across test suites.
    #
    def get_sample_image_filename(self) -> str:
        """Return the path to a local image file that can be used for tests.

        This must only be used for reading, and not for writing.

        Returns:
            str:
            The absolute file path.
        """
        return os.path.join(settings.STATIC_ROOT, 'rb', 'images', 'logo.png')
