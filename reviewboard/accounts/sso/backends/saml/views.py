"""Views for SAML SSO.

Version Added:
    5.0
"""

from enum import Enum
from urllib.parse import urlparse
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import (Http404,
                         HttpResponse,
                         HttpResponseBadRequest,
                         HttpResponseRedirect,
                         HttpResponseServerError)
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import View
from djblets.cache.backend import make_cache_key
from djblets.db.query import get_object_or_none
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import cached_property
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.errors import OneLogin_Saml2_Error
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
except ImportError:
    OneLogin_Saml2_Auth = None
    OneLogin_Saml2_Error = None
    OneLogin_Saml2_Settings = None
    OneLogin_Saml2_Utils = None

from reviewboard.accounts.models import LinkedAccount
from reviewboard.accounts.sso.backends.saml.forms import SAMLLinkUserForm
from reviewboard.accounts.sso.backends.saml.settings import get_saml2_settings
from reviewboard.accounts.sso.users import (find_suggested_username,
                                            find_user_for_sso_user_id)
from reviewboard.accounts.sso.views import BaseSSOView
from reviewboard.admin.server import get_server_url
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__file__)


class SAMLViewMixin(View):
    """Mixin to provide common functionality for SAML views.

    Version Added:
        5.0
    """

    def __init__(self, *args, **kwargs):
        """Initialize the view.

        Args:
            *args (tuple):
                Positional arguments to pass through to the base class.

            **kwargs (dict):
                Keyword arguments to pass through to the base class.
        """
        super().__init__(*args, **kwargs)
        self._saml_auth = None
        self._saml_request = None

    def get_saml_request(self, request):
        """Return the SAML request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            Information about the SAML request.
        """
        if self._saml_request is None:
            server_url = urlparse(get_server_url())

            if server_url.scheme == 'https':
                https = 'on'
            else:
                https = 'off'

            request_url = request.META['HTTP_HOST']
            http_host = server_url.hostname

            # In some cases, there may be multiple correct server URLs (for
            # example, some users may access the site through a reverse proxy
            # which rewrites all URLs). In this case, we want to allow the SAML
            # auth on those URLs. This requires that ALLOWED_HOSTS is set
            # appropriately to specifically include any URLs that the admin
            # wants.
            if (request_url != server_url.hostname and
                request_url in settings.ALLOWED_HOSTS):
                http_host = request_url

            self._saml_request = {
                'https': https,
                'http_host': http_host,
                'get_data': request.GET.copy(),
                'post_data': request.POST.copy(),
                'query_string': request.META['QUERY_STRING'],
                'request_uri': request.path,
                'script_name': request.META['PATH_INFO'],
                'server_port': server_url.port,
            }

        return self._saml_request

    def get_saml_auth(self, request):
        """Return the SAML auth information.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            onelogin.saml2.auth.OneLogin_Saml2_Auth:
            The SAML Auth object.
        """
        if self._saml_auth is None:
            assert OneLogin_Saml2_Auth is not None
            self._saml_auth = OneLogin_Saml2_Auth(
                self.get_saml_request(request),
                get_saml2_settings())

        return self._saml_auth

    def is_replay_attack(self, message_id):
        """Check for potential replay attacks.

        SAML authentication is potentially vulnerable to a replay attack from a
        man in the middle. This is mitigated by keeping track of recent message
        IDs and rejecting the authentication attempt if we've seen them before.

        Args:
            message_id (str):
                The ID to check.

        Returns:
            bool:
            ``True`` if we've seen the response or assertion IDs before.
            ``False`` if this appears to be a valid request.
        """
        if message_id is None:
            return False

        cache_key = make_cache_key('saml_replay_id_%s' % message_id,
                                   use_encryption=True)
        is_replay = cache.get(cache_key) is not None

        if not is_replay:
            cache.set(cache_key, True)

        return is_replay

    def dispatch(self, *args, **kwargs):
        """Handle a dispatch for the view.

        Args:
            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.

        Returns:
            django.http.HttpResponse:
            The response to send back to the client.

        Raises:
            django.http.Http404:
                The SAML backend is not enabled, so treat all SAML views as
                404.
        """
        if not self.sso_backend.is_enabled():
            raise Http404

        return super().dispatch(*args, **kwargs)


class SAMLACSView(SAMLViewMixin, BaseSSOView):
    """ACS view for SAML SSO.

    Version Added:
        5.0
    """

    @property
    def success_url(self):
        """The URL to redirect to after a successful login.

        Type:
            str
        """
        url = self.request.POST.get('RelayState')

        assert OneLogin_Saml2_Utils is not None
        self_url = OneLogin_Saml2_Utils.get_self_url(
            self.get_saml_request(self.request))

        if url is not None and self_url != url:
            saml_auth = self.get_saml_auth(self.request)
            return saml_auth.redirect_to(url)
        else:
            return settings.LOGIN_REDIRECT_URL

    @cached_property
    def link_user_url(self):
        """The URL to the link-user flow.

        Type:
            str
        """
        assert self.sso_backend is not None
        return local_site_reverse(
            'sso:%s:link-user' % self.sso_backend.backend_id,
            request=self.request,
            kwargs={'backend_id': self.sso_backend.backend_id})

    def post(self, request, *args, **kwargs):
        """Handle a POST request.

        Args:
            request (django.http.HttpRequest):
                The request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.http.HttpResponse:
            The response to send back to the client.
        """
        auth = self.get_saml_auth(request)
        session = request.session

        try:
            auth.process_response(request_id=session.get('AuthNRequestID'))
        except OneLogin_Saml2_Error as e:
            logger.exception('SAML: Unable to process SSO request: %s', e,
                             exc_info=True)
            return HttpResponseBadRequest('Bad SSO response: %s' % str(e),
                                          content_type='text/plain')

        if (self.is_replay_attack(auth.get_last_message_id()) or
            self.is_replay_attack(auth.get_last_assertion_id())):
            logger.error('SAML: Detected replay attack', request=request)
            return HttpResponseBadRequest(
                'SAML message IDs have already been used')

        error = auth.get_last_error_reason()

        if error:
            logger.error('SAML: Unable to process SSO request: %s', error)
            return HttpResponseBadRequest('Bad SSO response: %s' % error,
                                          content_type='text/plain')

        # Store some state on the session to identify where we are in the SAML
        # workflow.
        session.pop('AuthNRequestID', None)

        linked_account = get_object_or_none(LinkedAccount,
                                            service_id='sso:saml',
                                            service_user_id=auth.get_nameid())

        if linked_account:
            user = linked_account.user
            self.sso_backend.login_user(request, user)
            return HttpResponseRedirect(self.success_url)
        else:
            username = auth.get_nameid()

            try:
                email = self._get_user_attr_value(auth, 'User.email')
                first_name = self._get_user_attr_value(auth, 'User.FirstName')
                last_name = self._get_user_attr_value(auth, 'User.LastName')
            except KeyError as e:
                logger.error('SAML: Assertion is missing %s attribute', e)
                return HttpResponseBadRequest('Bad SSO response: assertion is '
                                              'missing %s attribute'
                                              % e,
                                              content_type='text/plain')

            request.session['sso'] = {
                'user_data': {
                    'id': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                },
                'raw_user_attrs': auth.get_attributes(),
                'session_index': auth.get_session_index(),
            }

            return HttpResponseRedirect(self.link_user_url)

    def _get_user_attr_value(self, auth, key):
        """Return the value of a user attribute.

        Args:
            auth (onelogin.saml2.auth.OneLogin_Saml2_Auth):
                The SAML authentication object.

            key (str):
                The key to look up.

        Returns:
            str:
            The attribute, if it exists.

        Raises:
            KeyError:
                The given key was not present in the SAML assertion.
        """
        value = auth.get_attribute(key)

        if value and isinstance(value, list):
            return value[0]

        # Some identity providers only allow setting the full name, not
        # separate first and last. In this case, we need to fake it by
        # splitting.
        if key in ('User.FirstName', 'User.LastName'):
            try:
                fullname = self._get_user_attr_value(auth, 'User.FullName')
            except KeyError:
                # Reraise with the original key name so that this fallback
                # isn't exposed in the exception message.
                raise KeyError(key)

            # We don't have a good way to split the user's full name to a first
            # and last name, so we split on the first space and then treat the
            # two parts as the first and last names.
            name_parts = fullname.split(' ', 1)

            if key == 'User.FirstName':
                return name_parts[0]
            else:
                return len(name_parts) > 1 and name_parts[1] or ''

        raise KeyError(key)


@method_decorator(csrf_protect, name='dispatch')
class SAMLLinkUserView(SAMLViewMixin, BaseSSOView, LoginView):
    """Link user view for SAML SSO.

    This can have several behaviors depending on what combination of state we
    get from the Identity Provider and what we have stored in the database.

    The first major case is where we are given data that matches an existing
    user in the database. Ideally this is via the "username" field, but may
    also be a matching e-mail address, or parsing a username out of the e-mail
    address.

    In this case, there are two paths. The simple path is where the
    administrator trusts both the authority and integrity of their Identity
    Provider and has turned off the "Require login to link" setting. For this,
    we'll just create the LinkedAccount, authenticate the user, and redirect to
    the success URL.

    If the require login setting is turned on, the user will have a choice.
    They can enter the password for the detected user to complete the link. If
    they have an account but the detected one is not correct, they can log in
    with their username and password to link the other account. Finally, they
    can provision a new user if they do not yet have one.

    The second major case is where we cannot find an existing user. In this
    case, we'll offer the user a choice: if they have an existing login that
    wasn't found, they can log in with their (non-SSO) username and password.
    If they don't have an account, they will be able to provision one.

    Version Added:
        5.0
    """

    # TODO: This has a lot of logic which will likely be applicable to other
    # SSO backend implementations. When we add a new backend, this should be
    # refactored to pull out most of the logic into a common base class, and
    # just implement SAML-specific data here.

    form_class = SAMLLinkUserForm

    class Mode(Enum):
        CONNECT_EXISTING_ACCOUNT = 'connect'
        CONNECT_WITH_LOGIN = 'connect-login'
        PROVISION = 'provision'

    def dispatch(self, *args, **kwargs):
        """Dispatch the view.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        self._sso_user_data = \
            self.request.session.get('sso', {}).get('user_data')
        self._sso_data_username = self._sso_user_data.get('id')
        self._sso_data_email = self._sso_user_data.get('email')
        computed_username = find_suggested_username(self._sso_data_email)
        self._provision_username = self._sso_data_username or computed_username
        self._sso_user = find_user_for_sso_user_id(
            self._sso_data_username,
            self._sso_data_email,
            computed_username)

        requested_mode = self.request.GET.get('mode')

        if requested_mode and requested_mode in self.Mode:
            self._mode = requested_mode
        elif self._sso_user:
            self._mode = self.Mode.CONNECT_EXISTING_ACCOUNT
        else:
            self._mode = self.Mode.PROVISION

        return super(SAMLLinkUserView, self).dispatch(*args, **kwargs)

    def get_template_names(self):
        """Return the template to use when rendering.

        Returns:
            list:
            A single-item list with the template name to use when rendering.

        Raises:
            ValueError:
                The current mode is not valid.
        """
        if self._mode == self.Mode.CONNECT_EXISTING_ACCOUNT:
            return ['accounts/sso/link-user-connect-existing.html']
        elif self._mode == self.Mode.CONNECT_WITH_LOGIN:
            return ['accounts/sso/link-user-login.html']
        elif self._mode == self.Mode.PROVISION:
            return ['accounts/sso/link-user-provision.html']
        else:
            raise ValueError('Unknown link-user mode "%s"' % self._mode)

    def get_initial(self):
        """Return the initial data for the form.

        Returns:
            dict:
            Initial data for the form.
        """
        initial = super(SAMLLinkUserView, self).get_initial()

        if self._sso_user is not None:
            initial['username'] = self._sso_user.username
        else:
            initial['username'] = self._provision_username

        initial['provision'] = (self._mode == self.Mode.PROVISION)

        return initial

    def get_context_data(self, **kwargs):
        """Return additional context data for rendering the template.

        Args:
            **kwargs (dict):
                Keyword arguments for the view.

        Returns:
            dict:
            Additional data to inject into the render context.
        """
        context = super(SAMLLinkUserView, self).get_context_data(**kwargs)
        context['user'] = self._sso_user
        context['mode'] = self._mode
        context['username'] = self._provision_username

        return context

    def get(self, request, *args, **kwargs):
        """Handle a GET request for the form.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass through to the base class.

            **kwargs (dict):
                Keyword arguments to pass through to the base class.

        Returns:
            django.http.HttpResponse:
            The response to send back to the client.
        """
        if not self._sso_user_data:
            return HttpResponseRedirect(
                local_site_reverse('login', request=request))

        siteconfig = SiteConfiguration.objects.get_current()

        if self._sso_user and not siteconfig.get('saml_require_login_to_link'):
            return self.link_user(self._sso_user)

        return super(SAMLLinkUserView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        """Handler for when the form has successfully authenticated.

        Args:
            form (reviewboard.accounts.sso.backends.saml.forms.
                  SAMLLinkUserForm):
                The link-user form.

        Returns:
            django.http.HttpResponseRedirect:
            A redirect to the next page.
        """
        if form.cleaned_data['provision']:
            # We can't provision if there's an existing matching user.
            # TODO: show an error?
            assert not self._sso_user
            assert self._provision_username

            first_name = self._sso_user_data.get('first_name')
            last_name = self._sso_user_data.get('last_name')

            logger.info('SAML: Provisioning user "%s" (%s <%s %s>)',
                        self._provision_username, self._sso_data_email,
                        first_name, last_name)

            user = User.objects.create(
                username=self._provision_username,
                email=self._sso_data_email,
                first_name=first_name,
                last_name=last_name)
        else:
            user = form.get_user()

        return self.link_user(user)

    def link_user(self, user):
        """Link the given user.

        Args:
            user (django.contrib.auth.models.User):
                The user to link.

        Returns:
            django.http.HttpResponseRedirect:
            A redirect to the success URL.
        """
        sso_id = self._sso_user_data.get('id')

        logger.info('SAML: Linking SSO user "%s" to Review Board user "%s"',
                    sso_id, user.username)

        user.linked_accounts.create(
            service_id='sso:saml',
            service_user_id=sso_id)
        self.sso_backend.login_user(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


class SAMLLoginView(SAMLViewMixin, BaseSSOView):
    """Login view for SAML SSO.

    Version Added:
        5.0
    """

    def get(self, request, *args, **kwargs):
        """Handle a GET request for the login URL.

        Args:
            request (django.http.HttpRequest):
                The request from the client.

            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            django.http.HttpResponseRedirect:
            A redirect to start the login flow.
        """
        auth = self.get_saml_auth(request)

        return HttpResponseRedirect(
            auth.login(settings.LOGIN_REDIRECT_URL))


class SAMLMetadataView(SAMLViewMixin, BaseSSOView):
    """Metadata view for SAML SSO.

    Version Added:
        5.0
    """

    def get(self, request, *args, **kwargs):
        """Handle a GET request.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments from the URL definition.

            **kwargs (dict):
                Keyword arguments from the URL definition.
        """
        assert OneLogin_Saml2_Settings is not None
        saml_settings = OneLogin_Saml2_Settings(
            get_saml2_settings(),
            sp_validation_only=True)

        metadata = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(metadata)

        if errors:
            logger.error('SAML: Got errors from metadata validation: %s',
                         ', '.join(errors))
            return HttpResponseServerError(', '.join(errors),
                                           content_type='text/plain')

        return HttpResponse(metadata, content_type='text/xml')


class SAMLSLSView(SAMLViewMixin, BaseSSOView):
    """SLS view for SAML SSO.

    Version Added:
        5.0
    """

    def get(self, request, *args, **kwargs):
        """Handle a GET request.

        Args:
            request (django.http.HttpRequest):
                The request from the client.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.http.HttpResponse:
            The response to send back to the client.
        """
        auth = self.get_saml_auth(request)
        request_id = None

        if 'LogoutRequestId' in request.session:
            request_id = request.session['LogoutRequestId']

        redirect_url = auth.process_slo(
            request_id=request_id,
            delete_session_cb=lambda: request.session.flush())

        if (self.is_replay_attack(auth.get_last_message_id()) or
            self.is_replay_attack(auth.get_last_request_id())):
            logger.error('SAML: Detected replay attack', request=request)
            return HttpResponseBadRequest(
                'SAML message IDs have already been used')

        error = auth.get_last_error_reason()

        if error:
            logger.error('SAML: Unable to process SLO request: %s', error)
            return HttpResponseBadRequest('Bad SLO response: %s' % error,
                                          content_type='text/plain')

        if redirect_url:
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect(settings.LOGIN_URL)
