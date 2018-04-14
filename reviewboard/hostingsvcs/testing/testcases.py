"""Test cases for testing hosting services."""

from __future__ import unicode_literals

import io
import json
from contextlib import contextmanager

from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.parse import urlparse
from kgb import SpyAgency

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.testing import TestCase


class HttpTestContext(object):
    """State and functions for an HTTP test.

    This is provided when calling
    :py:meth:`HostingServiceTestCase.setup_http_test`. It serves up state
    that can be tested with, along with useful functions for creating necessary
    objects and asserting results.

    Version Added:
        3.0.4

    Attributes:
        client (reviewboard.hostingsvcs.service.HostingServiceClient):
            The hosting service client used to perform HTTP requests for
            this test.

        hosting_account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The hosting account used for the test.

        service (reviewboard.hostingsvcs.service.HostingService):
            The hosting service instance used for the test.
    """

    def __init__(self, test_case, hosting_account, http_request_func):
        """Initialize the test context.

        Args:
            test_case (HostingServiceTestCase):
                The parent test case.

            hosting_account (reviewboard.hostingsvcs.models.
                             HostingServiceAccount):
                The hosting service account set up for the test.

            http_request_func (callable):
                The function used to handle HTTP requests.
        """
        self.hosting_account = hosting_account
        self.service = hosting_account.service
        self.client = self.service.client

        self._test_case = test_case
        self._http_request_func = http_request_func

    @property
    def http_calls(self):
        """The HTTP calls made by the service.

        This is a list of spy calls from KGB.
        """
        return self._http_request_func.calls

    def create_repository(self, **kwargs):
        """Create a repository using the current hosting account.

        This wraps :py:meth:`HostingServiceTestCase.create_repository`,
        specifying the hosting account that was set up in this test context.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`HostingServiceTestCase.create_repository`.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        return self._test_case.create_repository(
            hosting_account=self.hosting_account,
            **kwargs)

    def assertHTTPCall(self, index=0, method='GET', body=None, headers=None,
                       **kwargs):
        """Assert that an HTTP call was made.

        This sets some defaults based on the test case, helping both to
        eliminate the amount of data that needs to be checked and helping
        avoid missed data.

        Any keyword argument accepted by
        :py:meth:`HostingServiceClient.http_request()
        <reviewboard.hostingsvcs.service.HostingServiceClient.http_request>`
        can be provided.

        If ``username`` or ``password`` are not explicitly provided, the
        values from :py:attr:`HostingServiceTestCase.default_username` or
        :py:attr:`HostingServiceTestCase.default_password` will be used.

        Args:
            index (int, optional):
                The index of the HTTP call.

            method (unicode, optional);
                The HTTP method expected for the call.

            body (unicode, optional):
                The expected body for the call (used for POST/PUT requests).

            headers (dict, optional):
                The expected headers for the call.

            **kwargs (dict):
                Additional parameters to check in the call.
        """
        kwargs.setdefault('username', self._test_case.default_username)
        kwargs.setdefault('password', self._test_case.default_password)

        self._test_case.assertTrue(self.http_calls[index].called_with(
            method=method,
            body=body,
            headers=headers,
            **kwargs))


class HostingServiceTestCase(SpyAgency, TestCase):
    """Base class for unit tests for hosting services."""

    #: The registered name of the service.
    service_name = None

    #: The default username to use for accounts.
    default_username = 'myuser'

    #: The default password to use for accounts.
    default_password = 'mypass'

    #: The default hosting URL to use for accounts.
    #:
    #: This is only used for accounts set with ``use_url=True`` (or when
    #: ``default_use_hosting_url`` is ``True``).
    default_hosting_url = 'https://example.com'

    #: Whether to create accounts attached to a hosting URL by default.
    default_use_hosting_url = False

    #: Default data to set for created hosting service accounts.
    default_account_data = {}

    #: Default data to set for created repositories.
    default_repository_extra_data = {}

    #: Default SCMTool to set for created repositories.
    default_repository_tool_name = None

    fixtures = ['test_scmtools']

    @classmethod
    def setUpClass(cls):
        super(HostingServiceTestCase, cls).setUpClass()

        if cls.service_name:
            cls.service_class = get_hosting_service(cls.service_name)
        else:
            cls.service_class = None

    def setUp(self):
        super(HostingServiceTestCase, self).setUp()

        self.assertIsNotNone(self.service_class)

    @contextmanager
    def setup_http_test(self, http_request_func=None, payload=None,
                        headers=None, status_code=None, hosting_account=None,
                        expected_http_calls=None):
        """Set up state for HTTP-related tests.

        This takes the hard work out of testing hosting service functionality
        that needs to communicate over HTTP. It's a context manager that takes
        in information on what to return to the client and yields a context
        containing state and functions for performing and checking calls.

        By default, this will cause any HTTP requests to return an empty
        byte string as a payload. Explicit payloads can also be provided,
        as can an HTTP error code. For more advanced needs, a function can
        be provided that will handle the HTTP request (which is useful when
        your test may invoke several HTTP endpoints).

        This may be called repeatedly in the same test function.

        Args:
            http_request_func (callable, optional):
                An explicit HTTP request function to call when performing an
                HTTP request. This will override
                :py:meth:`reviewboard.hostingsvcs.service.HostingServiceClient
                .http_request`.

            payload (bytes, optional):
                An explicit payload to return to the client.

            headers (dict, optional):
                Headers to send along with the result.

            status_code (int, optional):
                An explicit HTTP status code. Only values >= 400 are used.
                Providing an error code will raise an HTTP error to the
                client, using the ``payload`` value if provided.

            hosting_account (reviewboard.hostingsvcs.models.
                             HostingServiceAccount, optional):
                An explicit hosting account to use. If not provided, one will
                be created using :py:meth:`create_hosting_account`.

            expected_http_calls (int, optional):
                The number of HTTP calls expected. If provided, this will
                assert that there were this many HTTP calls.

        Context:
            HttpTestContext:
            The context for the test, containing state, helper functions,
            and results.
        """
        if hosting_account is None:
            hosting_account = self.create_hosting_account()

        if http_request_func:
            # Sanity-check that the caller isn't mixing incompatible arguments.
            if payload is not None:
                raise ValueError(
                    'http_request_func and payload cannot both be provided')
            elif payload is not None:
                raise ValueError(
                    'http_request_func and status_code cannot both be '
                    'provided')
        else:
            http_request_func = self.make_handler_for_paths({
                None: {
                    'status_code': status_code,
                    'payload': payload,
                    'headers': headers,
                },
            })

        client = hosting_account.service.client

        if hasattr(client.http_request, 'unspy'):
            # Reset for this next test. This allows the test case to use
            # this context function multiple times.
            client.http_request.unspy()

        self.spy_on(client.http_request, call_fake=http_request_func)

        ctx = HttpTestContext(self, hosting_account, client.http_request)
        yield ctx

        if expected_http_calls is not None:
            self.assertEqual(len(ctx.http_calls), expected_http_calls)

    def make_handler_for_paths(self, paths):
        """Return an HTTP handler function for serving the supplied paths.

        This is meant to be passed to :py:meth:`setup_http_test`.

        This takes a dictionary matching paths to information to return. Each
        key is a path relative to the domain, which may optionally contain a
        full query string to match. It may also be ``None``, which is the
        fallback.

        Each value is a dictionary containing optional ``payload``,
        ``status_code``, or ``headers`` values.

        Args:
            paths (dict):
                The dictionary of paths.

        Returns:
            callable:
            The resulting HTTP handler function.

        Example:
            .. code-block:: python

               handler = make_handler_for_paths({
                   '/api/1/diffs/': {
                       'payload': b'...',
                       'headers': {
                           b'My-Header': b'value',
                        },
                   },
                   '/api/1/bad/': {
                       'status_code': 404,
                       'payload': b'Not found.',
                   },
                   None: {
                       'payload': b'fallback data...',
                   },
               })
        """
        # Validate the paths to make sure payloads are in the right format.
        for path, path_info in six.iteritems(paths):
            payload = path_info.get('payload')

            if payload is not None and not isinstance(payload, bytes):
                raise TypeError('payload must be a byte string or None')

        def _handler(client, url, *args, **kwargs):
            parts = urlparse(url)

            path_info = paths.get('%s?%s' % (parts.path, parts.query))

            if path_info is None:
                path_info = paths.get(parts.path)

                if path_info is None:
                    path_info = paths.get(None)

                    if path_info is None:
                        self.fail('Unexpected path "%s"' % parts.path)

            status_code = path_info.get('status_code')
            payload = path_info.get('payload') or b''
            headers = path_info.get('headers') or {}

            if status_code is not None and status_code >= 400:
                raise HTTPError(url, status_code, '', headers,
                                io.BytesIO(payload))
            else:
                return payload, headers

        return _handler

    def dump_json(self, data):
        """Dump JSON-compatible data to a byte string.

        Args:
            data (object):
                The data to dump.

        Returns:
            bytes:
            The serialized byte string.
        """
        result = json.dumps(data)

        if isinstance(result, six.text_type):
            result = result.encode('utf-8')

        return result

    def get_form(self, plan=None, fields={}):
        """Return the configuration form for the hosting service.

        Args:
            plan (unicode, optional):
                The hosting plan that the configuration form is for.

            fields (dict, optional):
                The initial field data to populate the form with.

        Returns:
            reviewboard.hostingsvcs.forms.HostingServiceForm:
        """
        form_cls = self.service_class.get_field(name='form', plan=plan)
        self.assertIsNotNone(form_cls)

        form = form_cls(fields)
        self.assertTrue(form.is_valid())

        return form

    def create_hosting_account(self, use_url=None, local_site=None,
                               data=None):
        """Create a hosting account to test with.

        Args:
            use_url (unicode, optional):
                Whether the account should be attached to a given hosting URL,
                for self-hosted services. If set, this will use
                ``https://example.com``.

            local_site (reviewboard.site.models.LocalSite, optional):
                A Local Site to attach the account to.

            data (dict, optional):
                Optional data to set for the account. If this is ``None``,
                :py:attr:`default_account_data` will be used.

        Returns:
            reviewboard.hostingsvcs.models.HostingServiceAccount:
            The new hosting service account.
        """
        if use_url is None:
            use_url = self.default_use_hosting_url

        if use_url:
            hosting_url = self.default_hosting_url
        else:
            hosting_url = None

        account = HostingServiceAccount(service_name=self.service_name,
                                        username=self.default_username,
                                        hosting_url=hosting_url,
                                        local_site=local_site)

        if data is not None:
            account.data = data
        else:
            account.data = self.default_account_data

        account.save()

        return account

    def create_repository(self, **kwargs):
        """Create a repository for a test.

        This wraps :py:meth:`TestCase.create_repository()
        <reviewboard.testing.testcase.TestCase.create_repository>`,
        specifying a default SCM Tool name (if
        :py:attr:`default_repository_tool_name`) is set) and
        extra data (if :py:attr:`default_repository_extra_data` is set).

        Args:
            **kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`TestCase.create_repository()
                <reviewboard.testing.testcase.TestCase.create_repository>`.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        if 'extra_data' not in kwargs:
            kwargs['extra_data'] = self.default_repository_extra_data.copy()

        return super(HostingServiceTestCase, self).create_repository(**kwargs)

    def get_repository_fields(self, tool_name, fields, plan=None,
                              with_url=None, hosting_account=None):
        """Return populated fields for a repository.

        Args:
            tool_name (unicode):
                The name of the SCM Tool used for the repository.

            fields (dict):
                A dictionary of fields for the hosting service form.

            plan (unicode, optional):
                The optional hosting plan to use for the configuration.

            with_url (unicode, optional):
                Whether the account should be attached to a given hosting URL,
                for self-hosted services. If set, this will use
                ``https://example.com``. This is ignored if ``hosting_account``
                is provided.

                This value defaults to :py:attr:`default_use_hosting_url`

            hosting_account (reviewboard.hostingsvcs.models.
                             HostingServiceAccount, optional):
                An explicit hosting service account to use.

        Returns:
            dict:
            The populated field data for the repository.
        """
        form = self.get_form(plan, fields)

        if not hosting_account:
            hosting_account = self.create_hosting_account(with_url)

        service = hosting_account.service
        self.assertIsNotNone(service)

        field_vars = form.clean().copy()
        field_vars.update(hosting_account.data)

        return service.get_repository_fields(
            username=hosting_account.username,
            hosting_url=self.default_hosting_url,
            plan=plan,
            tool_name=tool_name,
            field_vars=field_vars)
