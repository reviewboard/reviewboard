"""Common mixins for API unit tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from typing import (Any, Dict, Iterator, List, Optional, Sequence,
                    TYPE_CHECKING, Tuple, Union, cast)

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from djblets.features.testing import override_feature_checks
from djblets.secrets.token_generators import token_generator_registry
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED
from djblets.webapi.testing.decorators import webapi_test_template
from oauth2_provider.generators import (generate_client_id,
                                        generate_client_secret)
from oauth2_provider.models import AccessToken
from typing_extensions import NotRequired, TypeAlias, TypedDict

from reviewboard.accounts.models import Profile
from reviewboard.oauth.models import Application
from reviewboard.site.models import LocalSite
from reviewboard.webapi.models import WebAPIToken
from reviewboard.webapi.testing.queries import (
    get_webapi_request_start_equeries,
)

if TYPE_CHECKING:
    from djblets.features.testing import FeatureStates
    from djblets.testing.testcases import ExpectedQueries
    from djblets.util.typing import JSONDict, KwargsDict
    from djblets.webapi.errors import WebAPIError

    from reviewboard.reviews.models import ReviewRequest
    from reviewboard.webapi.tests.base import BaseWebAPITestCase

    _MixinsParentClass = BaseWebAPITestCase
else:
    _MixinsParentClass = object


#: Data provided in an HTTP POST or PUT request body.
#:
#: Version Added:
#:     5.0.7
APIRequestData: TypeAlias = Union[bytes, Dict[str, Any]]


class AuthenticateSetupState(TypedDict):
    """Test setup data for authentication setup for tests.

    Version Added:
        5.0.7
    """

    #: The OAuth2 access token used for the test, if any.
    oauth2_access_token: Optional[AccessToken]

    #: The OAuth2 application used for the test, if any.
    oauth2_application: Optional[Application]

    #: The user to use for the test.
    user: User

    #: The API token used for the test, if any.
    webapi_token: Optional[WebAPIToken]


class BasicTestSetupState(TypedDict):
    """Test setup data for basic HTTP unit tests.

    Version Added:
        5.0.7
    """

    #: The authenticated user for the test.
    auth_user: User

    #: The OAuth2 access token used for the test, if any.
    oauth2_access_token: Optional[AccessToken]

    #: The OAuth2 application used for the test, if any.
    oauth2_application: Optional[Application]

    #: The Local Site tests are being performed on, if any.
    #:
    #: This will be ``None`` if not testing on a Local Site.
    local_site: Optional[LocalSite]

    #: The name of the Local Site tests are being performed on, if any.
    #:
    #: This will be ``None`` if not testing on a Local Site.
    local_site_name: Optional[str]

    #: Whether the test is being performed with Local Sites in the database.
    local_sites_in_db: bool

    #: The user intended to own any state on the resource.
    #:
    #: Objects should be associated with this user. This defaults to
    #: :py:auth:`auth_user` unless explicitly overridden for the test.
    owner: User

    #: Objects used for testing.
    #:
    #: These are local to the unit test, and can be used however the test
    #: suite requires.
    test_objects: Dict[str, Any]

    #: The URL to the API resource.
    url: str

    #: The API token used for the test, if any.
    webapi_token: Optional[WebAPIToken]

    #: Whether the test is being performed on a Local Site.
    with_local_site: bool

    #: Custom positional arguments to pass to response-checking functions.
    check_result_args: NotRequired[Tuple[Any, ...]]

    #: Custom keyword arguments to pass to response-checking functions.
    check_result_kwargs: NotRequired[KwargsDict]

    #: The expected mimetype of the response.
    mimetype: NotRequired[str]


class BasicGetItemTestSetupState(BasicTestSetupState):
    """Test setup data for basic HTTP GET item unit tests.

    Version Added:
        5.0.7
    """

    #: The item to compare result payloads to.
    item: Any


class BasicGetItemListTestSetupState(BasicTestSetupState):
    """Test setup data for basic HTTP GET list unit tests.

    Version Added:
        5.0.7
    """

    #: The list of items to compare result payloads to.
    items: Sequence[Any]


class BasicDeleteTestSetupState(BasicTestSetupState):
    """Test setup data for basic HTTP DELETE unit tests.

    Version Added:
        5.0.7
    """


class BasicPostTestSetupState(BasicTestSetupState):
    """Test setup data for basic HTTP POST unit tests.

    Version Added:
        5.0.7
    """

    #: The body data to send in the POST request.
    request_data: APIRequestData


class BasicPutTestSetupState(BasicTestSetupState):
    """Test setup data for basic HTTP PUT unit tests.

    Version Added:
        5.0.7
    """

    #: The item to compare result payloads to.
    item: Any

    #: The body data to send in the PUT request.
    request_data: APIRequestData


class BasicTestsMetaclass(type):
    """Metaclass to automate common tests for resources.

    An API test class can set this as its metaclass in order to automatically
    add common test methods to ensure basic functionality and access control
    works.

    The class must have a ``resource`` attribute pointing to a WebAPIResource
    instance, and ``sample_api_url`` pointing to a sample URL for the API
    that will be used in the test strings.

    The class can also set ``test_http_methods`` to a tuple of HTTP methods
    that should be tested. By default, this includes DELETE, GET, POST
    and PUT.

    By default, tests will also be repeated on Local Sites. This can be
    disabled by setting ``test_local_sites = False``.
    """

    def __new__(
        cls,
        name: str,
        bases: Tuple[type, ...],
        d: Dict[str, Any],
    ) -> BasicTestsMetaclass:
        """Return a new testcase class with built-in test methods.

        Args:
            name (str):
                The name of the class.

            bases (tuple of str):
                The parent classes and mixins to apply for the class.

            d (dict):
                The dictionary data for the class.

        Returns:
            type:
            The resulting class.
        """
        mixins: Tuple[type, ...]

        test_local_sites = d.get('test_local_sites', True)
        test_api_token_access = d.get('test_api_token_access', True)
        test_oauth_token_access = d.get('test_oauth_token_access', True)
        resource = d['resource']
        is_singleton = False
        is_list = False

        if 'test_http_methods' in d:
            test_http_methods = d['test_http_methods']
        else:
            test_http_methods = ('DELETE', 'GET', 'POST', 'PUT')
            d['test_http_methods'] = test_http_methods

        if (hasattr(resource, 'required_features') and
            resource.required_features):
            d['override_features'] = {
                feature.feature_id: True
                for feature in resource.required_features
            }
        else:
            d['override_features'] = {}

        if name == 'ResourceListTests':
            is_list = True
        elif name == 'ResourceTests':
            is_singleton = True

        if 'DELETE' in test_http_methods and not is_list:
            if 'DELETE' not in resource.allowed_methods:
                mixins = (BasicDeleteNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicDeleteTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicDeleteTestsWithLocalSiteAndAPITokenMixin,)

                if test_oauth_token_access:
                    mixins += (
                        BasicDeleteTestsWithLocalSiteAndOAuthTokenMixin,
                    )
            else:
                mixins = (BasicDeleteTestsMixin,)

            bases = mixins + bases

        if 'GET' in test_http_methods:
            if is_list:
                if test_local_sites:
                    mixins = (BasicGetListTestsWithLocalSiteMixin,)

                    if test_api_token_access:
                        mixins += (
                            BasicGetListTestsWithLocalSiteAndAPITokenMixin,
                        )

                    if test_oauth_token_access:
                        mixins += (
                            BasicGetListTestsWithLocalSiteAndOAuthTokenMixin,
                        )
                else:
                    mixins = (BasicGetListTestsMixin,)
            else:
                if test_local_sites:
                    mixins = (BasicGetItemTestsWithLocalSiteMixin,)

                    if test_api_token_access:
                        mixins += (
                            BasicGetItemTestsWithLocalSiteAndAPITokenMixin,
                        )

                    if test_oauth_token_access:
                        mixins += (
                            BasicGetItemTestsWithLocalsSiteAndOAuthTokenMixin,
                        )
                else:
                    mixins = (BasicGetItemTestsMixin,)

            bases = mixins + bases

        if 'POST' in test_http_methods:
            if (not (is_list or is_singleton) or
                'POST' not in resource.allowed_methods):
                mixins = (BasicPostNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicPostTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicPostTestsWithLocalSiteAndAPITokenMixin,)

                if test_oauth_token_access:
                    mixins += (
                        BasicPostTestsWithLocalSiteAndOAuthTokenMixin,
                    )
            else:
                mixins = (BasicPostTestsMixin,)

            bases = mixins + bases

        if 'PUT' in test_http_methods:
            if is_list or 'PUT' not in resource.allowed_methods:
                mixins = (BasicPutNotAllowedTestsMixin,)
            elif test_local_sites:
                mixins = (BasicPutTestsWithLocalSiteMixin,)

                if test_api_token_access:
                    mixins += (BasicPutTestsWithLocalSiteAndAPITokenMixin,)

                if test_oauth_token_access:
                    mixins += (
                        BasicPutTestsWithLocalSiteAndOAuthTokenMixin,
                    )
            else:
                mixins = (BasicPutTestsMixin,)

            bases = mixins + bases

        return super().__new__(cls, name, bases, d)


class BasicTestsMixin(_MixinsParentClass):
    """Base class for a mixin for basic API tests."""

    #: The HTTP status code returned when the user is not the resource owner.
    #:
    #: Type:
    #:     int
    not_owner_status_code: int = 403

    #: The API error class used when the user is not the resource owner.
    #:
    #: Type:
    #:     djblets.webapi.errors.WebAPIError
    not_owner_error: WebAPIError = PERMISSION_DENIED

    def compare_item(
        self,
        item_rsp: JSONDict,
        obj: Any,
    ) -> None:
        """Compare an item's response payload to an object.

        This must be implemented by subclasses.

        Args:
            item_rsp (dict):
                The item payload from the response.

            obj (object):
                The object to compare to.
        """
        raise NotImplementedError("%s doesn't implement compare_item"
                                  % self.__class__.__name__)

    @contextmanager
    def _run_api_test(
        self,
        *,
        expected_queries: Optional[ExpectedQueries],
    ) -> Iterator[None]:
        """Context manager for running an API unit test.

        This wraps the test in common context managers that govern the
        execution of the tested code.

        Version Added:
            3.4

        Context:
            The test environment is set up to run the test.
        """
        with override_feature_checks(self.override_features):
            if expected_queries is None:
                yield
            else:
                with self.assertQueries(expected_queries,
                                        traceback_size=30):
                    yield

    def _close_file_handles(
        self,
        post_data: APIRequestData,
    ) -> None:
        """Close file handles from uploaded data.

        Any objects with a ``close()`` method in the posted data will be
        closed.

        Args:
            post_data (dict):
                The dictionary of posted data.
        """
        if isinstance(post_data, dict):
            for value in post_data.values():
                if hasattr(value, 'close'):
                    value.close()

    def _build_common_setup_state(
        self,
        *,
        fixtures: Sequence[str],
        owner: Optional[User] = None,
        with_local_site: bool = False,
        **auth_kwargs,
    ) -> Dict[str, Any]:
        """Set up common state for a test.

        This performs some built-in setup for all HTTP method tests. It's
        meant to be used for the method-specific state setup functions.

        Version Added:
            5.0.7

        Args:
            fixtures (list of str):
                The list of fixtures to load.

            owner (django.contrib.auth.models.User, optional):
                The owner of any objects being created.

                This defaults to the ``user`` value provided in
                ``auth_kwargs``.

            with_local_site (bool, optional):
                Whether this is being tested with a Local Site.

            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            dict:
            The common state for testing.
        """
        self.load_fixtures(fixtures)

        auth_setup_state = self._authenticate_basic_tests(
            with_local_site=with_local_site,
            **auth_kwargs)

        local_site_name = self.local_site_name

        if with_local_site:
            setup_local_site_name = local_site_name
            local_site = self.get_local_site(local_site_name)
        else:
            setup_local_site_name = None
            local_site = None

        return {
            'auth_user': auth_setup_state['user'],
            'local_site': local_site,
            'local_site_name': setup_local_site_name,
            'local_sites_in_db': LocalSite.objects.has_local_sites(),
            'oauth2_access_token': auth_setup_state['oauth2_access_token'],
            'oauth2_application': auth_setup_state['oauth2_application'],
            'owner': owner or auth_setup_state['user'],
            'test_objects': {},
            'webapi_token': auth_setup_state['webapi_token'],
            'with_local_site': with_local_site,
        }

    def _authenticate_basic_tests(
        self,
        *,
        with_local_site: bool = False,
        with_admin: bool = False,
        with_webapi_token: bool = False,
        webapi_token_local_site_id: Optional[int] = None,
        with_oauth_token: bool = False,
        oauth_application_enabled: bool = True,
        user: Optional[User] = None,
    ) -> AuthenticateSetupState:
        """Authenticate the user for basic API tests.

        Args:
            with_local_site (bool, optional):
                Whether the user will be authenticated on a Local Site.

            with_admin (bool, optional):
                Whether the user will be authenticated as an administrator.

            with_webapi_token (bool, optional):
                Whether the user will be authenticated using an API token.

                A token will be created for this user if it doesn't already
                exist.

            webapi_token_local_site_id (int, optional):
                The ID of the Local Site to associate with any fetched or
                created API tokens.

                This is only used if ``with_webapi_token`` is ``True``.

            with_oauth_token (bool, optional):
                Whether the user will be authenticated with an OAuth2 token.

            oauth_application_enabled (bool, optional):
                Whether the OAuth2 application to test against should be
                enabled.

                This is only used if ``with_oauth_token`` is ``True``.

            user (django.contrib.auth.models.User, optional):
                An optional user to log in with.

                If not provided, one will be created based on the values in
                ``with_local_site`` and ``with_admin``.

        Returns:
            django.contrib.auth.models.User:
            The authenticated user.
        """
        if user is None:
            user = self._login_user(local_site=with_local_site,
                                    admin=with_admin)
        elif user != self.user:
            self.assertTrue(self.client.login(username=user.username,
                                              password=user.username))

        access_token: Optional[AccessToken] = None
        application: Optional[Application] = None
        webapi_token: Optional[WebAPIToken] = None
        session = self.client.session

        if with_webapi_token:
            token_generator_id = \
                token_generator_registry.get_default().token_generator_id

            webapi_token = WebAPIToken.objects.get_or_create(
                user=user,
                token='abc123',
                token_generator_id=token_generator_id,
                local_site_id=webapi_token_local_site_id)[0]

            assert webapi_token is not None

            session['webapi_token_id'] = webapi_token.pk

        if with_oauth_token:
            application = Application.objects.get_or_create(
                local_site_id=webapi_token_local_site_id,
                user=user,
                defaults={
                    'authorization_grant_type': Application.GRANT_IMPLICIT,
                    'client_id': generate_client_id(),
                    'client_secret': generate_client_secret(),
                    'client_type': Application.CLIENT_PUBLIC,
                    'enabled': oauth_application_enabled,
                    'name': 'Test Application',
                    'redirect_uris': 'http://example.com',
                    'user': user,
                },
            )[0]

            assert application is not None

            if application.enabled != oauth_application_enabled:
                application.enabled = oauth_application_enabled
                application.save(update_fields=('enabled',))

            access_token = AccessToken.objects.create(
                application=application,
                user=user,
                token='abc123',
                scope=' '.join({
                    '%s:%s' % (self.resource.scope_name,
                               self.resource.HTTP_SCOPE_METHOD_MAP[method])
                    for method in self.resource.allowed_methods
                }),
                expires=timezone.now() + timedelta(hours=1),
            )

            session['oauth2_token_id'] = access_token.pk

        if with_webapi_token or with_oauth_token:
            session.save()

        return {
            'oauth2_access_token': access_token,
            'oauth2_application': application,
            'user': user,
            'webapi_token': webapi_token,
        }


class BasicDeleteTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP DELETE unit tests.

    The subclass must implement :py:meth:`populate_delete_test_objects` and
    :py:meth:`check_delete_result`.

    It may also set :py:attr:`basic_delete_fixtures` to a list of additional
    fixture names to import, and :py:attr:`basic_delete_use_admin` to ``True``
    if it wants to run the test as an administrator user.
    """

    #: A list of fixtures to use for basic HTTP DELETE tests.
    #:
    #: Type:
    #:     list of str
    basic_delete_fixtures: List[str] = []

    #: Whether to log in as an administrator for basic HTTP DELETE tests.
    #:
    #: Type:
    #:     bool
    basic_delete_use_admin: bool = False

    def populate_delete_test_objects(
        self,
        *,
        setup_state: BasicDeleteTestSetupState,
        **kwargs,
    ) -> None:
        """Populate objects for a DELETE test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. They're responsible for
        updating ``setup_state`` with the following:

        * ``mimetype``
        * ``url``
        * ``test_objects`` (optional)

        Version Added:
            5.0.7

        Args:
            setup_state (BasicDeleteTestSetupState):
                The setup state for the test.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        raise NotImplementedError(
            "%s doesn't implement populate_delete_test_objects"
            % type(self).__name__)

    def setup_basic_delete_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
    ) -> Tuple[str, Tuple[Any, ...]]:
        """Set up a basic HTTP DELETE unit test.

        Subclasses must override this to create an object that should be
        deleted in this resource.

        Deprecated:
            5.0.7:
            Subclasses should implement :py:meth:`populate_delete_test_objects`
            instead. This is a soft-deprecation as of this release.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

                The subclass must associate any objects that should appear in
                results with the Local Site identified by ``local_site_name``.

            local_site_name (str):
                The name of the Local Site to test againt.

                This will be ``None`` if testing against the global site.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to delete.

                1 (tuple):
                    Positional arguments to pass to
                    :py:meth:`check_delete_result`.
        """
        raise NotImplementedError(
            "%s doesn't implement setup_basic_delete_test"
            % self.__class__.__name__)

    def build_basic_delete_expected_queries(
        self,
        *,
        setup_state: BasicDeleteTestSetupState,
        is_accessible: bool,
        is_mutable: bool,
        is_owner: bool,
        **kwargs,
    ) -> Optional[ExpectedQueries]:
        """Return expected queries for a basic HTTP DELETE test.

        If implemented by a subclass, query assertions will be automatically
        enabled for the built-in tests.

        Version Added:
            5.0.7

        Args:
            setup_state (BasicDeleteTestSetupState):
                The setup state for the test.

            is_accessible (bool):
                Whether the resource is accessible by the current user.

            is_mutable (bool):
                Whether the resource is mutable by the current user.

            is_owner (bool):
                Whether the resource is owned by the current user.

            **kwargs (dict):
                Additional keyword arguments for future expansion or
                test-specific usage.

        Returns:
            djblets.testing.testcases.ExpectedQueries:
            The queries to expect in a test.

            If ``None``, query assertions will not be performed.
        """
        assert 'DELETE' in self.resource.allowed_methods

        return None

    def check_delete_result(
        self,
        user: User,
        *args,
    ) -> None:
        """Check the results of an HTTP DELETE.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the requesdt.

            *args (tuple):
                Positional arguments provided by
                :py:meth:`setup_basic_delete_test`.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        raise NotImplementedError("%s doesn't implement check_delete_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_delete(self) -> None:
        """Testing the DELETE <URL> API"""
        resource = self.resource

        self.assertTrue(getattr(resource.delete, 'login_required', False))
        self.assertTrue(getattr(resource.delete, 'checks_local_site', False))

        setup_state = self.setup_delete_test_state(
            with_admin=self.basic_delete_use_admin)

        expected_queries = self.build_basic_delete_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            self.api_delete(setup_state['url'])

        self.check_delete_result(setup_state['owner'],
                                 *setup_state.get('check_result_args', ()),
                                 **setup_state.get('check_result_kwargs', {}))

    @webapi_test_template
    def test_delete_not_owner(self) -> None:
        """Testing the DELETE <URL> API without owner"""
        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        setup_state = self.setup_delete_test_state(owner=user)

        expected_queries = self.build_basic_delete_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=False,
            is_owner=False)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_delete(setup_state['url'],
                                  expected_status=self.not_owner_status_code)

        assert rsp is not None
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], self.not_owner_error.code)

    def setup_delete_test_state(
        self,
        *,
        with_local_site: bool = False,
        **auth_kwargs,
    ) -> BasicDeleteTestSetupState:
        """Set up a HTTP DELETE item test.

        This performs some built-in setup for all HTTP DELETE tests before
        calling :py:meth:`setup_basic_get_test`.

        Args:
            with_local_site (bool, optional):
                Whether this is being tested with a Local Site.

            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            BasicDeleteTestSetupState:
            The resulting setup state for the test.
        """
        # Note that at this point, setup_state will be missing some keys.
        # This is considered a partial dictionary at this point. As of the
        # time this was implemented, Python does not have any equivalent to
        # TypeScript's Partial<T>, so we work around it and then guarantee a
        # stable result for callers.
        setup_state = cast(
            BasicDeleteTestSetupState,
            self._build_common_setup_state(fixtures=self.basic_delete_fixtures,
                                           with_local_site=with_local_site,
                                           **auth_kwargs))
        local_site_name = setup_state['local_site_name']

        try:
            # The modern form of testing in Review Board 5.0.7+.
            self.populate_delete_test_objects(setup_state=setup_state)

            url = setup_state.get('url')
        except NotImplementedError:
            # The legacy form pre-5.0.7.
            url, cb_args = self.setup_basic_delete_test(
                user=setup_state['owner'],
                with_local_site=with_local_site,
                local_site_name=local_site_name)
            setup_state.update({
                'check_result_args': cb_args,
                'url': url,
            })

        assert 'mimetype' not in setup_state
        assert url is not None

        self.assertEqual(url.startswith(f'/s/{local_site_name}/'),
                         with_local_site)

        return setup_state


class BasicDeleteTestsWithLocalSiteMixin(BasicDeleteTestsMixin):
    """Adds basic HTTP DELETE unit tests with Local Sites.

    This extends :py:class:`BasicDeleteTestsMixin` to also perform equivalent
    tests on Local Sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_site(self) -> None:
        """Testing the DELETE <URL> API with access to a local site"""
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin)

        expected_queries = self.build_basic_delete_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            self.api_delete(setup_state['url'])

        self.check_delete_result(setup_state['owner'],
                                 *setup_state.get('check_result_args', ()),
                                 **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_site_no_access(self) -> None:
        """Testing the DELETE <URL> API without access to a local site"""
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin)
        local_site = setup_state['local_site']

        assert local_site is not None

        # Undo our Local Site login, reverting back to a normal user.
        auth_user = self._login_user()

        equeries = get_webapi_request_start_equeries(
            user=auth_user,
            local_site=local_site)

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp is not None
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicDeleteTestsWithLocalSiteAndAPITokenMixin(_MixinsParentClass):
    """Adds basic HTTP DELETE unit tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_restrict_site_and_allowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site
        and session restricted to the site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)

        expected_queries = self.build_basic_delete_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            self.api_delete(setup_state['url'])

        self.check_delete_result(setup_state['owner'],
                                 *setup_state.get('check_result_args', ()),
                                 **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_with_restrict_site_and_not_allowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site
        and session restricted to a different site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            webapi_token=setup_state['webapi_token'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicDeleteTestsWithLocalSiteAndOAuthTokenMixin(_MixinsParentClass):
    """Adds basic HTTP DELETE unit tests with Local Sites and OAuth tokens."""

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_site_with_oauth_token_enabled_allowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site using an
        OAuth token for an enabled application on the current site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)

        expected_queries = self.build_basic_delete_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            self.api_delete(setup_state['url'])

        self.check_delete_result(setup_state['owner'],
                                 *setup_state.get('check_result_args', ()),
                                 **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_site_with_oauth_token_enabled_disallowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site using an
        OAuth token for an enabled application on a different site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_site_with_oauth_token_disabled_disallowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site using an
        OAuth token for a disabled application on the current site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id,
            oauth_application_enabled=False)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_no_site_with_site_oauth_token_disallowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site using an
        OAuth token meant for a local site on the root
        """
        setup_state = self.setup_delete_test_state(
            with_admin=self.basic_delete_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)

        self.assertIsNone(setup_state['local_site'])

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_delete_site_with_global_oauth_token_disallowed(self) -> None:
        """Testing the DELETE <URL> API with access to a local site using an
        OAuth token for the root on a local site
        """
        setup_state = self.setup_delete_test_state(
            with_local_site=True,
            with_admin=self.basic_delete_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=None)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_delete(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicDeleteNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP DELETE.

    The subclass must implement :py:meth:`setup_http_not_allowed_item_test`,
    which will be reused for all HTTP 405 Not Allowed tests on the class.
    """

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up a basic HTTP 405 Not Allowed test for DELETEs.

        Subclasses must override this to create objects that should be
        used when deleting items for this resource. The user must not be
        able to delete the object.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to the API resource to access.
        """
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_item_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_delete_method_not_allowed(self) -> None:
        """Testing the DELETE <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=self.user),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            self.api_delete(url, expected_status=405)


class BasicGetItemTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for item resources.

    The subclass must implement :py:meth:`populate_get_item_test_objects`.

    It may also set :py:attr:`basic_get_fixtures` to a list of additional
    fixture names to import.
    """

    #: A list of fixtures to use for basic HTTP GET item tests.
    #:
    #: Type:
    #:     list of str
    basic_get_fixtures: List[str] = []

    #: Whether the results from the resource are JSON payloads.
    #:
    #: Type:
    #:     bool
    basic_get_returns_json: bool = True

    #: Whether to log in as an administrator for basic HTTP GET item tests.
    #:
    #: Type:
    #:     bool
    basic_get_use_admin: bool = False

    def populate_get_item_test_objects(
        self,
        *,
        setup_state: BasicGetItemTestSetupState,
        **kwargs,
    ) -> None:
        """Populate objects for a GET item test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. They're responsible for
        updating ``setup_state`` with the following:

        * ``item``
        * ``mimetype``
        * ``url``
        * ``check_result_args`` (optional)
        * ``check_result_kwargs`` (optional)
        * ``test_objects`` (optional)

        Version Added:
            5.0.7

        Args:
            setup_state (BasicGetItemTestSetupState):
                The setup state for the test.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        raise NotImplementedError(
            "%s doesn't implement populate_get_item_test_objects"
            % type(self).__name__)

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
    ) -> Tuple[str, str, Any]:
        """Set up a basic HTTP GET unit test.

        Subclasses must override this to create an object that should be
        provided in results for this resource.

        Deprecated:
            5.0.7:
            Subclasses should implement
            :py:meth:`populate_get_item_test_objects` instead. This is a
            soft-deprecation as of this release.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

                The subclass must associate any objects that should appear in
                results with the Local Site identified by ``local_site_name``.

            local_site_name (str):
                The name of the Local Site to test againt.

                This will be ``None`` if testing against the global site.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (object):
                    The item to compare to in :py:meth:`compare_item`.
        """
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    def build_basic_get_item_expected_queries(
        self,
        *,
        setup_state: BasicGetItemTestSetupState,
        is_accessible: bool,
        is_mutable: bool,
        is_owner: bool,
        **kwargs,
    ) -> Optional[ExpectedQueries]:
        """Return expected queries for a basic HTTP GET item test.

        If implemented by a subclass, query assertions will be automatically
        enabled for the built-in tests.

        Version Added:
            5.0.7

        Args:
            setup_state (BasicGetItemTestSetupState):
                The setup state for the test.

            is_accessible (bool):
                Whether the resource is accessible by the current user.

            is_mutable (bool):
                Whether the resource is mutable by the current user.

            is_owner (bool):
                Whether the resource is owned by the current user.

            **kwargs (dict):
                Additional keyword arguments for future expansion or
                test-specific usage.

        Returns:
            djblets.testing.testcases.ExpectedQueries:
            The queries to expect in a test.

            If ``None``, query assertions will not be performed.
        """
        assert 'GET' in self.resource.allowed_methods

        return None

    @webapi_test_template
    def test_get(self) -> None:
        """Testing the GET <URL> API"""
        resource = self.resource

        self.assertTrue(
            getattr(resource.get, 'checks_login_required', False) or
            getattr(resource.get, 'login_required', False))
        self.assertTrue(getattr(resource.get, 'checks_local_site', False))

        setup_state = self.setup_get_item_test_state(
            with_admin=self.basic_get_use_admin)
        item = setup_state['item']

        expected_queries = self.build_basic_get_item_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'],
                               expected_json=self.basic_get_returns_json)

        assert rsp

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(resource.item_result_key, rsp)

            item_rsp = rsp[resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    def setup_get_item_test_state(
        self,
        *,
        with_local_site: bool = False,
        **auth_kwargs,
    ) -> BasicGetItemTestSetupState:
        """Set up a HTTP GET item test.

        This performs some built-in setup for all HTTP GET tests before
        calling :py:meth:`setup_basic_get_test`.

        Args:
            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            BasicGetItemTestSetupState:
            The resulting setup state for the test.
        """
        # Note that at this point, setup_state will be missing some keys.
        # This is considered a partial dictionary at this point. As of the
        # time this was implemented, Python does not have any equivalent to
        # TypeScript's Partial<T>, so we work around it and then guarantee a
        # stable result for callers.
        setup_state = cast(
            BasicGetItemTestSetupState,
            self._build_common_setup_state(fixtures=self.basic_get_fixtures,
                                           with_local_site=with_local_site,
                                           **auth_kwargs))
        local_site_name = setup_state['local_site_name']

        try:
            # The modern form of testing in Review Board 5.0.7+.
            self.populate_get_item_test_objects(setup_state=setup_state)

            mimetype = setup_state.get('mimetype')
            url = setup_state.get('url')
        except NotImplementedError:
            # The legacy form pre-5.0.7.
            url, mimetype, item = \
                self.setup_basic_get_test(user=setup_state['owner'],
                                          with_local_site=with_local_site,
                                          local_site_name=local_site_name)
            setup_state.update({
                'item': item,
                'mimetype': mimetype,
                'url': url,
            })

        assert 'item' in setup_state
        assert mimetype is not None
        assert url is not None

        self.assertEqual(url.startswith(f'/s/{local_site_name}/'),
                         with_local_site)

        return setup_state


class BasicGetItemTestsWithLocalSiteMixin(BasicGetItemTestsMixin):
    """Adds basic HTTP GET unit tests for item resources with Local Sites.

    This extends :py:class:`BasicGetItemTestsMixin` to also perform equivalent
    tests on Local Sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site(self) -> None:
        """Testing the GET <URL> API with access to a local site"""
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin)
        item = setup_state['item']

        expected_queries = self.build_basic_get_item_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'],
                               expected_json=self.basic_get_returns_json)

        assert rsp

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site_no_access(self) -> None:
        """Testing the GET <URL> API without access to a local site"""
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin)
        local_site = setup_state['local_site']

        assert local_site is not None

        # Undo our Local Site login, reverting back to a normal user.
        auth_user = self._login_user()

        equeries = get_webapi_request_start_equeries(
            user=auth_user,
            local_site=local_site)

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetItemTestsWithLocalSiteAndAPITokenMixin(_MixinsParentClass):
    """Adds HTTP GET tests for item resources with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site
        and session restricted to the site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)
        item = setup_state['item']

        expected_queries = self.build_basic_get_item_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'],
                               expected_json=self.basic_get_returns_json)

        assert rsp

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_not_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site
        and session restricted to a different site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            webapi_token=setup_state['webapi_token'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetItemTestsWithLocalsSiteAndOAuthTokenMixin(_MixinsParentClass):
    """Add basic HTTP GET item unit tests with Local Sites and OAuth tokens."""

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_site_with_oauth_token_enabled_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for an enabled application on the current site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        item = setup_state['item']

        expected_queries = self.build_basic_get_item_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'],
                               expected_json=self.basic_get_returns_json)

        assert rsp

        if self.basic_get_returns_json:
            self.assertEqual(rsp['stat'], 'ok')
            self.assertIn(self.resource.item_result_key, rsp)

            item_rsp = rsp[self.resource.item_result_key]
            self.compare_item(item_rsp, item)
        else:
            self.compare_item(rsp, item)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_site_with_oauth_token_enabled_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for an enabled application on a different site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_site_with_oauth_token_disabled_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for a disabled application on the current site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id,
            oauth_application_enabled=False)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_no_site_with_site_oauth_token_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token meant for a local site on the root
        """
        setup_state = self.setup_get_item_test_state(
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        auth_user = setup_state['auth_user']

        self.assertIsNone(setup_state['local_site'])

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=auth_user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=auth_user),
            },
            {
                '__note__': 'Fetch the OAuth2 token for the request',
                'model': AccessToken,
                'where': Q(pk=1),
            },
            {
                '__note__': 'Fetch the OAuth2 application for the token',
                'model': Application,
                'where': Q(id=1),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_site_with_global_oauth_token_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for the root on a local site
        """
        setup_state = self.setup_get_item_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=None)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetListTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP GET unit tests for list resources.

    The subclass must implement :py:class:`populate_get_list_test_objects`.

    It may also set :py:attr:`basic_get_fixtures` to a list of additional
    fixture names to import.
    """

    #: A list of fixtures to use for basic HTTP GET list tests.
    #:
    #: Type:
    #:     list of str
    basic_get_fixtures: List[str] = []

    #: Whether to log in as an administrator for basic HTTP GET list tests.
    #:
    #: Type:
    #:     bool
    basic_get_use_admin = False

    def populate_get_list_test_objects(
        self,
        *,
        setup_state: BasicGetItemListTestSetupState,
        **kwargs,
    ) -> None:
        """Populate objects for a GET list test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. They're responsible for
        updating ``setup_state`` with the following:

        * ``items``
        * ``mimetype``
        * ``url``
        * ``check_result_args`` (optional)
        * ``check_result_kwargs`` (optional)
        * ``test_objects`` (optional)

        Version Added:
            5.0.7

        Args:
            setup_state (BasicGetItemListTestSetupState):
                The setup state for the test.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        raise NotImplementedError(
            "%s doesn't implement populate_get_list_test_objects"
            % type(self).__name__)

    def setup_basic_get_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        populate_items: bool,
    ) -> Tuple[str, str, Sequence[str]]:
        """Set up a basic HTTP GET unit test.

        Subclasses must override this to create objects that should be
        provided in results for this resource (if requested).

        Deprecated:
            5.0.7:
            Subclasses should implement
            :py:meth:`populate_get_list_test_objects` instead. This is a
            soft-deprecation as of this release.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

                The subclass must associate any objects that should appear in
                results with the Local Site identified by ``local_site_name``.

            local_site_name (str):
                The name of the Local Site to test againt.

                This will be ``None`` if testing against the global site.

            populate_items (bool):
                Whether to populate items for the results.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (list of object):
                    The list of items to compare to in :py:meth:`compare_item`.
        """
        raise NotImplementedError("%s doesn't implement setup_basic_get_test"
                                  % self.__class__.__name__)

    def build_basic_get_list_expected_queries(
        self,
        *,
        setup_state: BasicGetItemListTestSetupState,
        is_accessible: bool,
        is_mutable: bool,
        is_owner: bool,
        **kwargs,
    ) -> Optional[ExpectedQueries]:
        """Return expected queries for a basic HTTP GET list test.

        If implemented by a subclass, query assertions will be automatically
        enabled for the built-in tests.

        Version Added:
            5.0.7

        Args:
            setup_state (BasicGetItemListTestSetupState):
                The setup state for the test.

            is_accessible (bool):
                Whether the resource is accessible by the current user.

            is_mutable (bool):
                Whether the resource is mutable by the current user.

            is_owner (bool):
                Whether the resource is owned by the current user.

            **kwargs (dict):
                Additional keyword arguments for future expansion or
                test-specific usage.

        Returns:
            djblets.testing.testcases.ExpectedQueries:
            The queries to expect in a test.

            If ``None``, query assertions will not be performed.
        """
        assert 'GET' in self.resource.allowed_methods

        return None

    @webapi_test_template
    def test_get(self) -> None:
        """Testing the GET <URL> API"""
        resource = self.resource

        self.assertTrue(
            getattr(resource.get, 'checks_login_required', False) or
            getattr(resource.get, 'login_required', False))
        self.assertTrue(getattr(resource.get, 'checks_local_site', False))

        setup_state = self.setup_get_list_test_state(
            with_admin=self.basic_get_use_admin)
        items = setup_state['items']

        expected_queries = self.build_basic_get_list_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    def setup_get_list_test_state(
        self,
        *,
        with_local_site: bool = False,
        populate_items: bool = True,
        **auth_kwargs,
    ) -> BasicGetItemListTestSetupState:
        """Set up a HTTP GET list test.

        This performs some built-in setup for all HTTP GET tests before
        calling :py:meth:`setup_basic_get_test`.

        Args:
            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            BasicGetItemListTestSetupState:
            The resulting setup state for the test.
        """
        # Note that at this point, setup_state will be missing some keys.
        # This is considered a partial dictionary at this point. As of the
        # time this was implemented, Python does not have any equivalent to
        # TypeScript's Partial<T>, so we work around it and then guarantee a
        # stable result for callers.
        setup_state = cast(
            BasicGetItemListTestSetupState,
            self._build_common_setup_state(fixtures=self.basic_get_fixtures,
                                           with_local_site=with_local_site,
                                           **auth_kwargs))
        local_site_name = setup_state['local_site_name']

        try:
            # The modern form of testing in Review Board 5.0.7+.
            self.populate_get_list_test_objects(
                setup_state=setup_state,
                populate_list_items=populate_items)

            items = setup_state.get('items')
            mimetype = setup_state.get('mimetype')
            url = setup_state.get('url')
        except NotImplementedError:
            # The legacy form pre-5.0.7.
            url, mimetype, items = \
                self.setup_basic_get_test(user=setup_state['owner'],
                                          with_local_site=with_local_site,
                                          local_site_name=local_site_name,
                                          populate_items=populate_items)
            setup_state.update({
                'items': items,
                'mimetype': mimetype,
                'url': url,
            })

        assert items is not None
        assert mimetype is not None
        assert url is not None

        self.assertEqual(url.startswith(f'/s/{local_site_name}/'),
                         with_local_site)

        return setup_state


class BasicGetListTestsWithLocalSiteMixin(BasicGetListTestsMixin):
    """Adds basic HTTP GET unit tests for list resources with Local Sites.

    This extends :py:class:`BasicGetListTestsMixin` to also perform
    equivalent tests on Local Sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site(self) -> None:
        """Testing the GET <URL> API with access to a local site"""
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin)
        items = setup_state['items']

        expected_queries = self.build_basic_get_list_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_site_no_access(self) -> None:
        """Testing the GET <URL> API without access to a local site"""
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin)
        local_site = setup_state['local_site']

        assert local_site is not None

        # Undo our Local Site login, reverting back to a normal user.
        auth_user = self._login_user()

        equeries = get_webapi_request_start_equeries(
            user=auth_user,
            local_site=local_site)

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetListTestsWithLocalSiteAndAPITokenMixin(_MixinsParentClass):
    """Adds HTTP GET tests for lists with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site
        and session restricted to the site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)
        items = setup_state['items']

        expected_queries = self.build_basic_get_list_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_with_restrict_site_and_not_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site
        and session restricted to a different site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            webapi_token=setup_state['webapi_token'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicGetListTestsWithLocalSiteAndOAuthTokenMixin(_MixinsParentClass):
    """Add basic HTTP GET list unit tests with Local Sites and OAuth tokens."""

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_list_site_with_oauth_token_enabled_allowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for an enabled application on the current site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        items = setup_state['items']

        expected_queries = self.build_basic_get_list_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_get(setup_state['url'],
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.list_result_key, rsp)

        items_rsp = rsp[self.resource.list_result_key]
        self.assertEqual(len(items), len(items_rsp))

        for i in range(len(items)):
            self.compare_item(items_rsp[i], items[i])

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_list_site_with_oauth_token_enabled_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for an enabled application on a different site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_list_site_with_oauth_token_disabled_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for a disabled application on the current site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id,
            oauth_application_enabled=False)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_list_no_site_with_site_oauth_token_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token meant for a local site on the root
        """
        setup_state = self.setup_get_list_test_state(
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)

        self.assertIsNone(setup_state['local_site'])

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_get_list_site_with_global_oauth_token_disallowed(self) -> None:
        """Testing the GET <URL> API with access to a local site using an
        OAuth token for the root on a local site
        """
        setup_state = self.setup_get_list_test_state(
            with_local_site=True,
            with_admin=self.basic_get_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=None)
        local_site = setup_state['local_site']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_get(setup_state['url'], expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP POST unit tests.

    The subclass must implement :py:meth:`populate_post_test_objects` and
    :py:attr:`check_post_result`.

    It may also set :py:attr:`basic_post_fixtures` to a list of additional
    fixture names to import, and :py:attr:`basic_post_use_admin` to ``True``
    if it wants to run the test as an administrator user.
    """

    #: A list of fixtures to use for basic HTTP POST tests.
    #:
    #: Type:
    #:     list of str
    basic_post_fixtures: List[str] = []

    #: Whether to log in as an administrator for basic HTTP POST tests.
    #:
    #: Type:
    #:     bool
    basic_post_use_admin: bool = False

    #: The HTTP status code for successful POST requests.
    #:
    #: Type:
    #:     int
    basic_post_success_status: int = 201

    def populate_post_test_objects(
        self,
        *,
        setup_state: BasicPostTestSetupState,
        create_valid_request_data: bool,
        **kwargs,
    ) -> None:
        """Populate objects for a POST test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. They're responsible for
        updating ``setup_state`` with the following:

        * ``mimetype``
        * ``request_data``
        * ``url``
        * ``check_result_args`` (optional)
        * ``check_result_kwargs`` (optional)
        * ``test_objects`` (optional)

        Version Added:
            5.0.7

        Args:
            setup_state (BasicPostTestSetupState):
                The setup state for the test.

            create_valid_request_data (bool):
                Whether ``request_data`` in ``setup_state`` should provide
                valid data for a POST test, given the populated objects.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        raise NotImplementedError(
            "%s doesn't implement populate_post_test_objects"
            % type(self).__name__)

    def setup_basic_post_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        post_valid_data: bool,
    ) -> Tuple[str, str, APIRequestData, Tuple[Any, ...]]:
        """Set up a basic HTTP POST unit test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource.

        Deprecated:
            5.0.7:
            Subclasses should implement :py:meth:`populate_post_test_objects`
            instead. This is a soft-deprecation as of this release.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

                The subclass must associate any objects that should appear in
                results with the Local Site identified by ``local_site_name``.

            local_site_name (str):
                The name of the Local Site to test againt.

                This will be ``None`` if testing against the global site.

            post_valid_data (bool):
                Whether to return valid data for successfully creating a
                resource.

                This is used to differentiate a successful POST request versus
                one that's missing data.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (dict or bytes):
                    The data to send in the POST request.

                3 (tuple):
                    Positional arguments to pass to
                    :py:meth:`check_post_result`.
        """
        raise NotImplementedError("%s doesn't implement setup_basic_post_test"
                                  % self.__class__.__name__)

    def build_basic_post_expected_queries(
        self,
        *,
        setup_state: BasicPostTestSetupState,
        is_accessible: bool,
        is_mutable: bool,
        is_owner: bool,
        **kwargs,
    ) -> Optional[ExpectedQueries]:
        """Return expected queries for a basic HTTP POST test.

        If implemented by a subclass, query assertions will be automatically
        enabled for the built-in tests.

        Version Added:
            5.0.7

        Args:
            setup_state (BasicPostTestSetupState):
                The setup state for the test.

            is_accessible (bool):
                Whether the resource is accessible by the current user.

            is_mutable (bool):
                Whether the resource is mutable by the current user.

            is_owner (bool):
                Whether the resource is owned by the current user.

            **kwargs (dict):
                Additional keyword arguments for future expansion or
                test-specific usage.

        Returns:
            djblets.testing.testcases.ExpectedQueries:
            The queries to expect in a test.

            If ``None``, query assertions will not be performed.
        """
        assert 'POST' in self.resource.allowed_methods

        return None

    def check_post_result(
        self,
        user: User,
        rsp: JSONDict,
        *args,
    ) -> None:
        """Check the results of an HTTP POST.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the requesdt.

            rsp (dict):
                The POST response payload.

            *args (tuple):
                Positional arguments provided by
                :py:meth:`setup_basic_post_test`.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        raise NotImplementedError("%s doesn't implement check_post_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_post(self) -> None:
        """Testing the POST <URL> API"""
        resource = self.resource

        self.assertTrue(getattr(resource.create, 'login_required', False))
        self.assertTrue(getattr(resource.create, 'checks_local_site', False))

        setup_state = self.setup_post_test_state(
            with_admin=self.basic_post_use_admin)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_post_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_mimetype=setup_state['mimetype'],
                                expected_status=self.basic_post_success_status)

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(setup_state['owner'],
                               rsp,
                               *setup_state.get('check_result_args', ()),
                               **setup_state.get('check_result_kwargs', {}))

    def setup_post_test_state(
        self,
        *,
        with_local_site: bool = False,
        post_valid_data: bool = True,
        **auth_kwargs,
    ) -> BasicPostTestSetupState:
        """Set up a HTTP POST item test.

        This performs some built-in setup for all HTTP POST tests before
        calling :py:meth:`setup_basic_post_test`.

        Args:
            with_local_site (bool, optional):
                Whether this is being tested with a Local Site.

            post_valid_data (bool, optional):
                Whether valid data should be generated for the HTTP request
                body.

            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            BasicPostTestSetupState:
            The resulting setup state for the test.
        """
        # Note that at this point, setup_state will be missing some keys.
        # This is considered a partial dictionary at this point. As of the
        # time this was implemented, Python does not have any equivalent to
        # TypeScript's Partial<T>, so we work around it and then guarantee a
        # stable result for callers.
        setup_state = cast(
            BasicPostTestSetupState,
            self._build_common_setup_state(fixtures=self.basic_post_fixtures,
                                           with_local_site=with_local_site,
                                           **auth_kwargs))
        local_site_name = setup_state['local_site_name']

        try:
            # The modern form of testing in Review Board 5.0.7+.
            self.populate_post_test_objects(
                setup_state=setup_state,
                create_valid_request_data=post_valid_data)

            mimetype = setup_state.get('mimetype')
            request_data = setup_state.get('request_data')
            url = setup_state.get('url')
        except NotImplementedError:
            # The legacy form pre-5.0.7.
            url, mimetype, request_data, cb_args = \
                self.setup_basic_post_test(
                    user=setup_state['owner'],
                    with_local_site=with_local_site,
                    local_site_name=local_site_name,
                    post_valid_data=post_valid_data)
            setup_state.update({
                'check_result_args': cb_args,
                'mimetype': mimetype,
                'request_data': request_data,
                'url': url,
            })

        assert mimetype is not None
        assert request_data is not None
        assert url is not None

        # Clean up any request data after the test. We'll reference
        # setup_state instead of request_data directly to avoid keeping the
        # latter in scope.
        self.addCleanup(
            lambda: self._close_file_handles(setup_state['request_data']))

        self.assertEqual(url.startswith(f'/s/{local_site_name}/'),
                         with_local_site)

        return setup_state


class BasicPostTestsWithLocalSiteMixin(BasicPostTestsMixin):
    """Adds basic HTTP POST unit tests with Local Sites.

    This extends :py:class:`BasicPostTestsMixin` to also perform equivalent
    tests on Local Sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site(self) -> None:
        """Testing the POST <URL> API with access to a local site"""
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_post_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_mimetype=setup_state['mimetype'],
                                expected_status=self.basic_post_success_status)

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(setup_state['owner'],
                               rsp,
                               *setup_state.get('check_result_args', ()),
                               **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_site_no_access(self) -> None:
        """Testing the POST <URL> API without access to a local site"""
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        # Undo our Local Site login, reverting back to a normal user.
        auth_user = self._login_user()

        equeries = get_webapi_request_start_equeries(
            user=auth_user,
            local_site=local_site)

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostTestsWithLocalSiteAndAPITokenMixin(_MixinsParentClass):
    """Adds HTTP POST tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_restrict_site_and_allowed(self) -> None:
        """Testing the POST <URL> API with access to a local site
        and session restricted to the site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_post_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_mimetype=setup_state['mimetype'],
                                expected_status=self.basic_post_success_status)

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(setup_state['owner'],
                               rsp,
                               *setup_state.get('check_result_args', ()),
                               **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_with_restrict_site_and_not_allowed(self) -> None:
        """Testing the POST <URL> API with access to a local site
        and session restricted to a different site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            webapi_token=setup_state['webapi_token'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostTestsWithLocalSiteAndOAuthTokenMixin(_MixinsParentClass):
    """Adds basic HTTP POST unit tests with Local Sites and OAuth tokens."""

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_site_with_oauth_token_enabled_allowed(self) -> None:
        """Testing the POST <URL> API with access to a local site using an
        OAuth token for an enabled application on the current site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_post_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_mimetype=setup_state['mimetype'],
                                expected_status=self.basic_post_success_status)

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.check_post_result(setup_state['owner'],
                               rsp,
                               *setup_state.get('check_result_args', ()),
                               **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_site_with_oauth_token_enabled_disallowed(self) -> None:
        """Testing the POST <URL> API with access to a local site using an
        OAuth token for an enabled application on a different site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_site_with_oauth_token_disabled_disallowed(self) -> None:
        """Testing the POST <URL> API with access to a local site using an
        OAuth token for a disabled application on the current site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id,
            oauth_application_enabled=False)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_no_site_with_site_oauth_token_disallowed(self) -> None:
        """Testing the POST <URL> API with access to a local site using an
        OAuth token meant for a local site on the root
        """
        setup_state = self.setup_post_test_state(
            with_admin=self.basic_post_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        auth_user = setup_state['auth_user']
        request_data = setup_state['request_data']

        self.assertIsNone(setup_state['local_site'])

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=auth_user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=auth_user),
            },
            {
                '__note__': 'Fetch the OAuth2 token for the request',
                'model': AccessToken,
                'where': Q(pk=1),
            },
            {
                '__note__': 'Fetch the OAuth2 application for the token',
                'model': Application,
                'where': Q(id=1),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_post_site_with_global_oauth_token_disallowed(self) -> None:
        """Testing the POST <URL> API with access to a local site using an
        OAuth token for the root on a local site
        """
        setup_state = self.setup_post_test_state(
            with_local_site=True,
            with_admin=self.basic_post_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=None)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_post(setup_state['url'],
                                request_data,
                                expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPostNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP POST.

    The subclass must implement :py:meth:`setup_http_not_allowed_list_test`.
    """

    def setup_http_not_allowed_list_test(
        self,
        user: User,
    ) -> str:
        """Set up a basic HTTP 405 Not Allowed test for POSTs.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. The user must not be
        able to create the object.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to the API resource to access.
        """
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_list_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_post_method_not_allowed(self) -> None:
        """Testing the POST <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_list_test(self.user)

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=self.user),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            self.api_post(url, {}, expected_status=405)


class BasicPutTestsMixin(BasicTestsMixin):
    """Mixin to add basic HTTP PUT unit tests.

    The subclass must implement :py:meth:`populate_put_test_objects` and
    :py:meth:`check_put_result`.

    It may also set :py:attr:`basic_put_fixtures` to a list of additional
    fixture names to import, and :py:attr:`basic_put_use_admin` to ``True``
    if it wants to run the test as an administrator user.
    """

    #: A list of fixtures to use for basic HTTP PUT tests.
    #:
    #: Type:
    #:     list of str
    basic_put_fixtures: List[str] = []

    #: Whether to log in as an administrator for basic HTTP PUT tests.
    #:
    #: Type:
    #:     bool
    basic_put_use_admin: bool = False

    def populate_put_test_objects(
        self,
        *,
        setup_state: BasicPutTestSetupState,
        create_valid_request_data: bool,
        **kwargs,
    ) -> None:
        """Populate objects for a PUT test.

        Subclasses must override this to create objects that should be
        used when creating items for this resource. They're responsible for
        updating ``setup_state`` with the following:

        * ``items``
        * ``mimetype``
        * ``request_data``
        * ``url``
        * ``check_result_args`` (optional)
        * ``check_result_kwargs`` (optional)
        * ``test_objects`` (optional)

        Version Added:
            5.0.7

        Args:
            setup_state (BasicPutTestSetupState):
                The setup state for the test.

            create_valid_request_data (bool):
                Whether ``request_data`` in ``setup_state`` should provide
                valid data for a PUT test, given the populated objects.

            **kwargs (dict):
                Additional keyword arguments for future expansion.
        """
        raise NotImplementedError(
            "%s doesn't implement populate_put_test_objects"
            % type(self).__name__)

    def setup_basic_put_test(
        self,
        user: User,
        with_local_site: bool,
        local_site_name: Optional[str],
        put_valid_data: bool,
    ) -> Tuple[str, str, APIRequestData, Any, Tuple[Any, ...]]:
        """Set up a basic HTTP PUT unit test.

        Subclasses must override this to create objects that should be
        used when modifying items for this resource.

        Deprecated:
            5.0.7:
            Subclasses should implement :py:meth:`populate_put_test_objects`
            instead. This is a soft-deprecation as of this release.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

            with_local_site (bool):
                Whether the test is being performed on a Local Site.

                The subclass must associate any objects that should appear in
                results with the Local Site identified by ``local_site_name``.

            local_site_name (str):
                The name of the Local Site to test againt.

                This will be ``None`` if testing against the global site.

            put_valid_data (bool):
                Whether to return valid data for successfully modifying a
                resource.

                This is used to differentiate a successful PUT request versus
                one that's missing data.

        Returns:
            tuple:
            A 5-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.

                2 (dict or bytes):
                    The data to send in the POST request.

                4 (object):
                    The item to compare to in :py:meth:`check_put_result`.

                5 (tuple):
                    Positional arguments to pass to
                    :py:meth:`check_put_result`.
        """
        raise NotImplementedError("%s doesn't implement setup_basic_put_test"
                                  % self.__class__.__name__)

    def build_basic_put_expected_queries(
        self,
        *,
        setup_state: BasicPutTestSetupState,
        is_accessible: bool,
        is_mutable: bool,
        is_owner: bool,
        **kwargs,
    ) -> Optional[ExpectedQueries]:
        """Return expected queries for a basic HTTP PUT test.

        If implemented by a subclass, query assertions will be automatically
        enabled for the built-in tests.

        Version Added:
            5.0.7

        Args:
            setup_state (BasicPutTestSetupState):
                The setup state for the test.

            is_accessible (bool):
                Whether the resource is accessible by the current user.

            is_mutable (bool):
                Whether the resource is mutable by the current user.

            is_owner (bool):
                Whether the resource is owned by the current user.

            **kwargs (dict):
                Additional keyword arguments for future expansion or
                test-specific usage.

        Returns:
            djblets.testing.testcases.ExpectedQueries:
            The queries to expect in a test.

            If ``None``, query assertions will not be performed.
        """
        assert 'PUT' in self.resource.allowed_methods

        return None

    def check_put_result(
        self,
        user: User,
        item_rsp: JSONDict,
        item: Any,
        *args,
    ) -> None:
        """Check the results of an HTTP PUT.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the requesdt.

            item_rsp (dict):
                The item payload from the response.

            item (object):
                The item to compare to.

            *args (tuple):
                Positional arguments provided by
                :py:meth:`setup_basic_put_test`.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        raise NotImplementedError("%s doesn't implement check_put_result"
                                  % self.__class__.__name__)

    @webapi_test_template
    def test_put(self) -> None:
        """Testing the PUT <URL> API"""
        resource = self.resource

        self.assertTrue(getattr(resource.update, 'login_required', False))
        self.assertTrue(getattr(resource.update, 'checks_local_site', False))

        setup_state = self.setup_put_test_state(
            with_admin=self.basic_put_use_admin)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_put_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(resource.item_result_key, rsp)

        self.check_put_result(setup_state['owner'],
                              rsp[resource.item_result_key],
                              setup_state['item'],
                              *setup_state.get('check_result_args', ()),
                              **setup_state.get('check_result_kwargs', {}))

    @webapi_test_template
    def test_put_not_owner(self) -> None:
        """Testing the PUT <URL> API without owner"""
        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        setup_state = self.setup_put_test_state(
            owner=user,
            put_valid_data=False)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_put_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=False,
            is_owner=False)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=self.not_owner_status_code)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], self.not_owner_error.code)

    def setup_put_test_state(
        self,
        *,
        with_local_site: bool = False,
        put_valid_data: bool = True,
        **auth_kwargs,
    ) -> BasicPutTestSetupState:
        """Set up a HTTP PUT item test.

        This performs some built-in setup for all HTTP PUT tests before
        calling :py:meth:`setup_basic_put_test`.

        Args:
            with_local_site (bool, optional):
                Whether this is being tested with a Local Site.

            put_valid_data (bool, optional):
                Whether valid data should be generated for the HTTP request
                body.

            **auth_kwargs (dict):
                Keyword arguments to pass to
                :py:meth:`_authenticate_basic_tests`.

        Returns:
            BasicPutTestSetupState:
            The resulting setup state for the test.
        """
        # Note that at this point, setup_state will be missing some keys.
        # This is considered a partial dictionary at this point. As of the
        # time this was implemented, Python does not have any equivalent to
        # TypeScript's Partial<T>, so we work around it and then guarantee a
        # stable result for callers.
        setup_state = cast(
            BasicPutTestSetupState,
            self._build_common_setup_state(fixtures=self.basic_put_fixtures,
                                           with_local_site=with_local_site,
                                           **auth_kwargs))
        local_site_name = setup_state['local_site_name']

        try:
            # The modern form of testing in Review Board 5.0.7+.
            self.populate_put_test_objects(
                setup_state=setup_state,
                create_valid_request_data=put_valid_data)

            mimetype = setup_state.get('mimetype')
            request_data = setup_state.get('request_data')
            url = setup_state.get('url')
        except NotImplementedError:
            # The legacy form pre-5.0.7.
            url, mimetype, request_data, item, cb_args = \
                self.setup_basic_put_test(user=setup_state['owner'],
                                          with_local_site=with_local_site,
                                          local_site_name=local_site_name,
                                          put_valid_data=put_valid_data)
            setup_state.update({
                'check_result_args': cb_args,
                'item': item,
                'mimetype': mimetype,
                'request_data': request_data,
                'url': url,
            })

        assert 'item' in setup_state
        assert mimetype is not None
        assert request_data is not None
        assert url is not None

        # Clean up any request data after the test. We'll reference
        # setup_state instead of request_data directly to avoid keeping the
        # latter in scope.
        self.addCleanup(
            lambda: self._close_file_handles(setup_state['request_data']))

        self.assertEqual(url.startswith(f'/s/{local_site_name}'),
                         with_local_site)

        return setup_state


class BasicPutTestsWithLocalSiteMixin(BasicPutTestsMixin):
    """Adds basic HTTP PUT unit tests with Local Sites.

    This extends :py:class:`BasicPutTestsMixin` to also perform equivalent
    tests on Local Sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_site(self) -> None:
        """Testing the PUT <URL> API with access to a local site"""
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_put_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(setup_state['owner'],
                              rsp[self.resource.item_result_key],
                              setup_state['item'],
                              *setup_state.get('check_result_args', ()),
                              **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_site_no_access(self) -> None:
        """Testing the PUT <URL> API without access to a local site"""
        setup_state = self.setup_put_test_state(with_local_site=True)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        # Undo our Local Site login, reverting back to a normal user.
        auth_user = self._login_user()

        equeries = get_webapi_request_start_equeries(
            user=auth_user,
            local_site=local_site)

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPutTestsWithLocalSiteAndAPITokenMixin(_MixinsParentClass):
    """Adds HTTP PUT tests with Local Sites and API tokens.

    This adds additional tests for checking API token access for local
    sites.
    """

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_restrict_site_and_allowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site
        and session restricted to the site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_put_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(setup_state['owner'],
                              rsp[self.resource.item_result_key],
                              setup_state['item'],
                              *setup_state.get('check_result_args', ()),
                              **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_with_restrict_site_and_not_allowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site
        and session restricted to a different site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_webapi_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            webapi_token=setup_state['webapi_token'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPutTestsWithLocalSiteAndOAuthTokenMixin(_MixinsParentClass):
    """Adds basic HTTP PUT unit tests with Local Sites and OAuth tokens."""

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_site_with_oauth_token_enabled_allowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site using an
        OAuth token for an enabled application on the current site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        request_data = setup_state['request_data']

        expected_queries = self.build_basic_put_expected_queries(
            setup_state=setup_state,
            is_accessible=True,
            is_mutable=True,
            is_owner=True)

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_mimetype=setup_state['mimetype'])

        assert rsp
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        self.check_put_result(setup_state['owner'],
                              rsp[self.resource.item_result_key],
                              setup_state['item'],
                              *setup_state.get('check_result_args', ()),
                              **setup_state.get('check_result_kwargs', {}))

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_site_with_oauth_token_enabled_disallowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site using an
        OAuth token for an enabled application on a different site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id + 1)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_site_with_oauth_token_disabled_disallowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site using an
        OAuth token for a disabled application on the current site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id,
            oauth_application_enabled=False)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_no_site_with_site_oauth_token_disallowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site using an
        OAuth token meant for a local site on the root
        """
        setup_state = self.setup_put_test_state(
            with_admin=self.basic_put_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=self.local_site_id)
        auth_user = setup_state['auth_user']
        request_data = setup_state['request_data']

        self.assertIsNone(setup_state['local_site'])

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=auth_user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=auth_user),
            },
            {
                '__note__': 'Fetch the OAuth2 token for the request',
                'model': AccessToken,
                'where': Q(pk=1),
            },
            {
                '__note__': 'Fetch the OAuth2 application for the token',
                'model': Application,
                'where': Q(id=1),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_site'])
    @webapi_test_template
    def test_put_site_with_global_oauth_token_disallowed(self) -> None:
        """Testing the PUT <URL> API with access to a local site using an
        OAuth token for the root on a local site
        """
        setup_state = self.setup_put_test_state(
            with_local_site=True,
            with_admin=self.basic_put_use_admin,
            with_oauth_token=True,
            webapi_token_local_site_id=None)
        local_site = setup_state['local_site']
        request_data = setup_state['request_data']

        assert local_site is not None

        equeries = get_webapi_request_start_equeries(
            user=setup_state['auth_user'],
            local_site=local_site,
            oauth2_access_token=setup_state['oauth2_access_token'],
            oauth2_application=setup_state['oauth2_application'])

        with self._run_api_test(expected_queries=equeries):
            rsp = self.api_put(setup_state['url'],
                               request_data,
                               expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class BasicPutNotAllowedTestsMixin(BasicTestsMixin):
    """Mixin to add HTTP 405 Not Allowed tests for HTTP PUT.

    The subclass must implement :py:meth:`setup_http_not_allowed_item_test`,
    which will be reused for all HTTP 405 Not Allowed tests on the
    class.
    """

    def setup_http_not_allowed_item_test(
        self,
        user: User,
    ) -> str:
        """Set up a basic HTTP 405 Not Allowed test for PUTs.

        Subclasses must override this to create objects that should be
        used when modifying items for this resource. The user must not be
        able to modify the object.

        Args:
            user (django.contrib.auth.models.User):
                The user performing the API requests.

        Returns:
            str:
            The URL to the API resource to access.
        """
        raise NotImplementedError(
            "%s doesn't implement setup_http_not_allowed_item_test"
            % self.__class__.__name__)

    @webapi_test_template
    def test_put_method_not_allowed(self) -> None:
        """Testing the PUT <URL> API gives Method Not Allowed"""
        url = self.setup_http_not_allowed_item_test(self.user)

        expected_queries: ExpectedQueries = [
            {
                '__note__': 'Fetch the logged-in user',
                'model': User,
                'where': Q(pk=self.user.pk),
            },
            {
                '__note__': "Fetch the user's profile",
                'model': Profile,
                'where': Q(user=self.user),
            },
        ]

        with self._run_api_test(expected_queries=expected_queries):
            self.api_put(url, {}, expected_status=405)


class BaseReviewRequestChildMixin(_MixinsParentClass):
    """Base class for tests for children of ReviewRequestResource.

    This will test that the resources are only accessible when the user has
    access to the review request itself (such as when the review request
    is private due to being in an invite-only repository or group).

    This applies to immediate children and any further down the tree.
    """

    #: Whether the results from the resource are JSON payloads.
    #:
    #: Type:
    #:     bool
    basic_get_returns_json: bool = True

    #: Features to override for the tests.
    #:
    #: Type:
    #:     dict
    override_features: FeatureStates = {}

    def setup_review_request_child_test(
        self,
        review_request: ReviewRequest,
    ) -> Tuple[str, str]:
        """Set up a basic HTTP GET test for review request resource children.

        Subclasses must override this to create objects nested within a
        review request source.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that the objects must be associated with.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (str):
                    The URL to the API resource to access.

                1 (str):
                    The expected mimetype of the response.
        """
        raise NotImplementedError(
            "%s doesn't implement setup_review_request_child_test"
            % self.__class__.__name__)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_group(self) -> None:
        """Testing the GET <URL> API
        with access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        group.users.add(self.user)
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(publish=True,
                                                    repository=repository)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        with override_feature_checks(self.override_features):
            self.api_get(url,
                         expected_mimetype=mimetype,
                         expected_json=self.basic_get_returns_json)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_group_no_access(self) -> None:
        """Testing the GET <URL> API
        without access to review request on a private group
        """
        group = self.create_review_group(invite_only=True)
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(publish=True,
                                                    repository=repository)
        review_request.target_groups.add(group)

        url, mimetype = self.setup_review_request_child_test(review_request)

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url, expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_repo(self) -> None:
        """Testing the GET <URL> API
        with access to review request on a private repository
        """
        repository = self.create_repository(public=False, tool_name='Test')
        repository.users.add(self.user)
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        with override_feature_checks(self.override_features):
            self.api_get(url,
                         expected_mimetype=mimetype,
                         expected_json=self.basic_get_returns_json)

    @add_fixtures(['test_scmtools'])
    @webapi_test_template
    def test_get_with_private_repo_no_access(self) -> None:
        """Testing the GET <URL> API
        without access to review request on a private repository
        """
        repository = self.create_repository(public=False, tool_name='Test')
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)

        url, mimetype = self.setup_review_request_child_test(review_request)

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url, expected_status=403)

        assert rsp
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)


class ReviewRequestChildListMixin(BaseReviewRequestChildMixin):
    """Tests for list resources that are children of ReviewRequestResource."""


class ReviewRequestChildItemMixin(BaseReviewRequestChildMixin):
    """Tests for item resources that are children of ReviewRequestResource."""
