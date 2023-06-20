"""Views for handling authentication and user accounts."""

from __future__ import annotations

import datetime
import logging
from typing import Optional
from urllib.parse import quote, urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView as DjangoLoginView,
    LogoutView,
    logout_then_login as auth_logout_then_login)
from django.forms.forms import ErrorDict
from django.http import (Http404,
                         HttpRequest,
                         HttpResponse,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.base import TemplateView
from djblets.auth.views import register
from djblets.configforms.views import ConfigPagesView
from djblets.features.decorators import feature_required
from djblets.forms.fieldsets import filter_fieldsets
from djblets.registries.errors import ItemLookupError
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import augment_method_from
from djblets.views.generic.etag import ETagViewMixin
from djblets.webapi.errors import WebAPITokenGenerationError

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.forms.registration import RegistrationForm
from reviewboard.accounts.mixins import (CheckLoginRequiredViewMixin,
                                         LoginRequiredViewMixin)
from reviewboard.accounts.pages import AccountPage, OAuth2Page, PrivacyPage
from reviewboard.accounts.privacy import is_consent_missing
from reviewboard.accounts.sso.backends import sso_backends
from reviewboard.admin.decorators import check_read_only
from reviewboard.avatars import avatar_services
from reviewboard.notifications.email.decorators import preview_email
from reviewboard.notifications.email.message import \
    prepare_password_changed_mail
from reviewboard.oauth.features import oauth2_service_feature
from reviewboard.oauth.forms import (UserApplicationChangeForm,
                                     UserApplicationCreationForm)
from reviewboard.oauth.models import Application
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.models import WebAPIToken


logger = logging.getLogger(__name__)


class LoginView(DjangoLoginView):
    """A view for rendering the login page.

    This view may be called when clients are trying to authenticate to
    Review Board through a web-based login flow. In that case, callers must
    include a ``client-name`` query parameter containing the client name,
    and a ``client-url`` parameter containing the URL of where to send
    authentication data upon a successful login. Client callers may include a
    ``next`` parameter containing a URL for redirection, making sure to
    encode any query parameters in that URL.

    Version Changed:
        5.0.5:
        Added the ``client-name`` and ``client-url`` query parameters for
        authenticating clients.

    Version Added:
        5.0

    Version Changed:
        5.0.5:
        Added the ``client-name`` and ``client-url`` query parameters for
        authenticating clients.
    """

    template_name = 'accounts/login.html'

    ######################
    # Instance variables #
    ######################

    #: Whether the request is for authenticating a client.
    #:
    #: Version Added:
    #:     5.0.5
    #:
    #: Type:
    #:     bool
    client_auth_flow: bool

    #: The name of the client who is authenticating.
    #:
    #: Version Added:
    #:     5.0.5
    #:
    #: Type:
    #:     str
    client_name: Optional[str]

    #: The URL to the client login page.
    #:
    #: Version Added:
    #:     5.0.5
    #:
    #: Type:
    #:     str
    client_login_url: str

    #: The URL to the client login confirmation page.
    #:
    #: Version Added:
    #:     5.0.5
    #:
    #: Type:
    #:     str
    client_login_confirm_url: str

    #: The URL of where to send authentication data for the client.
    #:
    #: Version Added:
    #:     5.0.5
    #:
    #: Type:
    #:     str
    client_url: Optional[str]

    def dispatch(self, request, *args, **kwargs):
        """Dispatch the view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.

        Returns:
            django.http.HttpResponse:
            The response to send to the client.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        self.client_name = None
        self.client_url = None

        if siteconfig.get('client_web_login'):
            self.client_name = self.request.GET.get(
                'client-name',
                self.request.POST.get('client-name', ''))
            self.client_url = self.request.GET.get(
                'client-url',
                self.request.POST.get('client-url', ''))
            client_url_port = urlparse(self.client_url).port
            self.success_url_allowed_hosts = \
                _get_client_allowed_hosts(client_url_port)

        client_name = self.client_name
        client_url = self.client_url
        client_auth_flow = bool(client_name and client_url)
        self.client_auth_flow = client_auth_flow
        client_redirect_param_str = ''
        redirect_field_name = self.redirect_field_name
        redirect_to = quote(self.get_redirect_url())

        if redirect_to and client_auth_flow:
            client_redirect_param_str = (
                '&%s=%s' % (redirect_field_name, redirect_to))

        client_login_url = (
            '%s?client-name=%s&client-url=%s%s'
            % (local_site_reverse('client-login'),
               client_name,
               client_url,
               client_redirect_param_str))
        client_login_confirm_url = (
            '%s?client-name=%s&client-url=%s%s'
            % (local_site_reverse('client-login-confirm'),
               client_name,
               client_url,
               client_redirect_param_str))
        self.client_login_url = client_login_url
        self.client_login_confirm_url = client_login_confirm_url

        if (request.method == 'GET' and client_auth_flow and
            request.user.is_authenticated):
            # The request is for client web-based login, with the user already
            # logged in.
            return HttpResponseRedirect(client_login_confirm_url)

        sso_auto_login_backend = siteconfig.get('sso_auto_login_backend', None)

        if sso_auto_login_backend:
            try:
                backend = sso_backends.get('backend_id', sso_auto_login_backend)
                login_url = backend.login_url

                if client_auth_flow:
                    redirect_to = client_login_confirm_url
                else:
                    redirect_to = self.get_success_url()

                if url_has_allowed_host_and_scheme(
                    url=redirect_to, allowed_hosts=request.get_host()):
                    login_url = '%s?%s=%s' % (login_url,
                                              redirect_field_name,
                                              quote(redirect_to))

                return HttpResponseRedirect(login_url)
            except ItemLookupError:
                logging.error('Unable to find sso_auto_login_backend "%s".',
                              sso_auto_login_backend)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Return extra data for rendering the template.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent class.

        Returns:
            dict:
            Context to use when rendering the template.
        """
        context = super().get_context_data(**kwargs)

        context['enabled_sso_backends'] = [
            sso_backend
            for sso_backend in sso_backends
            if sso_backend.is_enabled()
        ]

        if self.client_auth_flow:
            context['client_name'] = self.client_name
            context['client_url'] = self.client_url

            # While in the client web-based login flow, redirect to
            # the client login page upon successful login.
            context[self.redirect_field_name] = self.client_login_url

        return context


def logout(request, *args, **kwargs):
    """Log out the user."""
    siteconfig = SiteConfiguration.objects.get_current()
    sso_auto_login_backend = siteconfig.get('sso_auto_login_backend', None)

    # If we're configured to automatically log in via SSO, we can't use
    # logout_then_login, because it will log out and then immediately log in
    # again.
    if sso_auto_login_backend:
        try:
            backend = sso_backends.get('backend_id', sso_auto_login_backend)
            return LogoutView.as_view()(request, *args, **kwargs)
        except ItemLookupError:
            logging.error('Unable to find sso_auto_login_backend "%s".',
                          sso_auto_login_backend)

    return auth_logout_then_login(request, *args, **kwargs)


class UserInfoboxView(CheckLoginRequiredViewMixin,
                      CheckLocalSiteAccessViewMixin,
                      ETagViewMixin,
                      TemplateView):
    """Displays information on a user, for use in user pop-up infoboxes.

    This is meant to be embedded in other pages, rather than being
    a standalone page.
    """

    template_name = 'accounts/user_infobox.html'

    def __init__(self, **kwargs):
        """Initialize a view for the request.

        Args:
            **kwargs (dict):
                Keyword arguments passed to :py:meth:`as_view`.
        """
        super(UserInfoboxView, self).__init__(**kwargs)

        self._lookup_user = None
        self._show_profile = None
        self._timezone = None

    def get_etag_data(self, request, username, *args, **kwargs):
        """Return an ETag for the view.

        This will look up some state needed for the request and generate a
        suitable ETag.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            username (unicode):
                The username of the user being looked up.

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            unicode:
            The ETag for the page.
        """
        from reviewboard.extensions.hooks import UserInfoboxHook

        user = get_object_or_404(User, username=username)
        self._lookup_user = user

        profile = user.get_profile()
        self._show_profile = user.is_profile_visible(request.user)
        self._timezone = profile.timezone

        etag_data = [
            user.first_name,
            user.last_name,
            user.email,
            str(user.last_login),
            str(settings.TEMPLATE_SERIAL),
            str(self._show_profile),
            self._timezone,
        ]

        if avatar_services.avatars_enabled:
            avatar_service = avatar_services.for_user(user)

            if avatar_service:
                etag_data.extend(avatar_service.get_etag_data(user))

        local_site = self.local_site

        for hook in UserInfoboxHook.hooks:
            try:
                etag_data.append(hook.get_etag_data(
                    user=user,
                    request=request,
                    local_site=local_site))
            except Exception as e:
                logger.exception('Error when running UserInfoboxHook.'
                                 'get_etag_data method in extension "%s": %s',
                                 hook.extension.id, e,
                                 extra={'request': request})

        return ':'.join(etag_data)

    def get_context_data(self, **kwargs):
        """Return data for the template.

        This will return information on the user, along with information from
        any extension hooks used for the page.

        Args:
            **kwargs (tuple):
                Additional keyword arguments from the URL pattern.

        Returns:
            dict:
            Context data for the template.
        """
        from reviewboard.extensions.hooks import UserInfoboxHook

        # These are accessed several times, so bring them in to reduce
        # attribute lookups.
        user = self._lookup_user
        username = user.username
        local_site = self.local_site

        extra_content = []

        for hook in UserInfoboxHook.hooks:
            try:
                extra_content.append(hook.render(
                    user=user,
                    request=self.request,
                    local_site=local_site))
            except Exception as e:
                logger.exception('Error when running UserInfoboxHook.'
                                 'render method in extension "%s": %s',
                                 hook.extension.id, e,
                                 extra={'request': self.request})

        review_requests_url = local_site_reverse('user', local_site=local_site,
                                                 args=[username])
        reviews_url = local_site_reverse('user-grid', local_site=local_site,
                                         args=[username, 'reviews'])

        has_avatar = (
            avatar_services.avatars_enabled and
            avatar_services.for_user(user) is not None
        )

        return {
            'extra_content': mark_safe(''.join(extra_content)),
            'full_name': user.get_full_name(),
            'has_avatar': has_avatar,
            'infobox_user': user,
            'review_requests_url': review_requests_url,
            'reviews_url': reviews_url,
            'show_profile': self._show_profile,
            'timezone': self._timezone,
        }


@csrf_protect
def account_register(request, next_url='dashboard'):
    """Display the appropriate registration page.

    If registration is enabled and the selected authentication backend supports
    creation of users, this will return the appropriate registration page. If
    registration is not supported, this will redirect to the login view.
    """
    siteconfig = SiteConfiguration.objects.get_current()
    auth_backends = get_enabled_auth_backends()

    if (auth_backends[0].supports_registration and
        siteconfig.get('auth_enable_registration') and
        not siteconfig.get('site_read_only')):
        response = register(request, next_page=reverse(next_url),
                            form_class=RegistrationForm)

        return response

    return HttpResponseRedirect(reverse("login"))


class MyAccountView(ConfigPagesView):
    """Displays the My Account page containing user preferences.

    The page will be built based on registered pages and forms. This makes
    it easy to plug in new bits of UI for the page, which is handy for
    extensions that want to offer customization for users.
    """

    title = _('My Account')

    css_bundle_names = [
        'account-page',
    ]

    js_bundle_names = [
        '3rdparty-jsonlint',
        'config-forms',
        'account-page',
    ]

    @method_decorator(login_required)
    @method_decorator(check_read_only)
    @augment_method_from(ConfigPagesView)
    def dispatch(self, *args, **kwargs):
        """Handle the view.

        This just falls back to the djblets ConfigPagesView.dispatch
        implementation.
        """
        pass

    @property
    def nav_title(self):
        """Get the title for the navigation section."""
        return self.request.user.username

    @property
    def page_classes(self):
        """The list of page classes for this view.

        If the user is missing any consent requirements or has not accepted
        the privacy policy/terms of service, only the privacy page will be
        shown.
        """
        if self.is_user_missing_consent:
            return [AccountPage.registry.get('page_id', PrivacyPage.page_id)]

        return list(AccountPage.registry)

    @cached_property
    def ordered_user_local_sites(self):
        """Get the user's local sites, ordered by name."""
        return self.request.user.local_site.order_by('name')

    @property
    def render_sidebar(self):
        """Whether or not to render the sidebar.

        If the user is missing any consent requirements or has not accepted
        the privacy policy/terms of service, the sidebar will not render.
        This is to prevent the user from navigating away from the privacy page
        before making decisions.
        """
        return not self.is_user_missing_consent

    @cached_property
    def is_user_missing_consent(self):
        """Whether or not the user is missing consent."""
        return is_consent_missing(self.request.user)


@login_required
@preview_email(prepare_password_changed_mail)
def preview_password_changed_email(request):
    return {
        'user': request.user,
    }


@login_required
@feature_required(oauth2_service_feature)
def edit_oauth_app(request, app_id=None):
    """Create or edit an OAuth2 application.

    Args:
        request (django.http.HttpRequest):
            The current HTTP request.

        app_id (int, optional):
            The ID of the application to edit.

            If this argument is ``None`` a new application will be edited.

    Returns:
        django.http.HttpResponse:
        The rendered view.
    """
    # If we import this at global scope, it will cause issues with admin sites
    # being automatically registered.
    from reviewboard.oauth.admin import ApplicationAdmin

    if app_id:
        app = get_object_or_404(
            Application,
            pk=app_id,
            user=request.user,
        )
        form_cls = UserApplicationChangeForm
        fieldsets = ApplicationAdmin.fieldsets
    else:
        app = None
        form_cls = UserApplicationCreationForm
        fieldsets = ApplicationAdmin.add_fieldsets

    if request.method == 'POST':
        form_data = request.POST.copy()

        form = form_cls(user=request.user, data=form_data, initial=None,
                        instance=app)

        if form.is_valid():
            app = form.save()

            if app_id is not None:
                next_url = OAuth2Page.get_absolute_url()
            else:
                next_url = reverse('edit-oauth-app', args=(app.pk,))

            return HttpResponseRedirect(next_url)
    else:
        form = form_cls(user=request.user, data=None, initial=None,
                        instance=app)

        # Show a warning at the top of the form when the form is disabled for
        # security.
        #
        # We don't need to worry about full_clean not being called (which would
        # be if we went through form.errors) because this form will never be
        # saved.
        if app and app.is_disabled_for_security:
            form._errors = ErrorDict({
                '__all__': form.error_class(
                    [form.DISABLED_FOR_SECURITY_ERROR],
                ),
            })

    return render(
        request=request,
        template_name='accounts/edit_oauth_app.html',
        context={
            'app': app,
            'form': form,
            'fieldsets': filter_fieldsets(form=form_cls,
                                          fieldsets=fieldsets),
            'oauth2_page_url': OAuth2Page.get_absolute_url(),
            'request': request,
        })


class BaseClientLoginView(LoginRequiredViewMixin,
                          TemplateView):
    """Base view for views dealing with the client web-based login flow.

    Callers must include a ``client-name`` query parameter containing the
    client name, and a ``client-url`` parameter containing the URL of where
    to send authentication data upon a successful login. Callers may include
    a ``next`` parameter containing a URL for redirection, making sure to
    encode any query parameters in that URL.

    Version Added:
        5.0.5
    """

    #: The name of the redirect field.
    #:
    #: Type:
    #:     str
    redirect_field_name: str = LoginView.redirect_field_name

    ######################
    # Instance variables #
    ######################

    #: Whether the client is safe to redirect and POST to.
    #:
    #: Type:
    #:     bool
    client_allowed: bool

    #: The hosts that are allowed to authenticate clients to Review Board.
    #:
    #: This will only allow the local host server at the given client
    #: port and the Review Board server.
    #:
    #: Type:
    #:     set
    client_allowed_hosts: set

    #: The name of the client who is authenticating.
    #:
    #: Type:
    #:     str
    client_name: str

    #: The URL of where to send authentication data for the client.
    #:
    #: Type:
    #:     str
    client_url: str

    #: The URL of where to redirect to upon a successful login.
    #:
    #: This is URL encoded.
    #:
    #: Type:
    #:     str
    redirect_to: str

    #: The name of the template to render.
    #:
    #: This must be set by the subclass.
    #:
    #: Type:
    #:     str
    template_name: str

    def dispatch(
        self,
        request: HttpRequest,
        *args,
        **kwargs,
    ) -> HttpResponse:
        """Dispatch the view.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.

        Returns:
            django.http.HttpResponse:
            The response to send to the client.
        """
        self.siteconfig = SiteConfiguration.objects.get_current()
        request_GET = self.request.GET

        if self.siteconfig.get('client_web_login'):
            self.client_name = request_GET.get('client-name', '')
            self.client_url = request_GET.get('client-url', '')

            client_url_port = urlparse(self.client_url).port
            client_allowed_hosts = _get_client_allowed_hosts(client_url_port)
            client_allowed_hosts.add(request.get_host())
            self.client_allowed_hosts = client_allowed_hosts

            self.client_allowed = self._url_is_safe(self.client_url)
            self.redirect_to = self._get_redirect_url()

            return super().dispatch(request, *args, **kwargs)

        raise Http404

    def get_context_data(self, **kwargs) -> dict:
        """Return extra data for rendering the template.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent class.

        Returns:
            dict:
            Context to use when rendering the template.
        """
        context = super().get_context_data(**kwargs)

        context['client_allowed'] = self.client_allowed
        context['client_name'] = self.client_name
        context['client_url'] = self.client_url
        context['username'] = self.request.user.username

        return context

    def _url_is_safe(
        self,
        url: str,
    ) -> bool:
        """Return whether the given URL is safe to redirect and/or POST to.

        Args:
            url (str):
                The URL.

        Returns:
            bool:
            Whether the url is safe to redirect and/or POST to.
        """
        return url_has_allowed_host_and_scheme(
            url=url,
            allowed_hosts=self.client_allowed_hosts)

    def _get_redirect_url(self) -> str:
        """Return the redirect URL.

        This encodes the URL.

        Returns:
            str:
            The redirect URL or an empty string if the redirect URL is
            not safe.
        """
        redirect_to = self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, ''))
        assert isinstance(redirect_to, str)

        if self._url_is_safe(redirect_to):
            return quote(redirect_to)

        return ''


class ClientLoginView(BaseClientLoginView):
    """View for rendering the client login page.

    The client login page handles authenticating a client to Review Board
    by POSTing authentication data to the client.

    Callers must include a ``client-name`` query parameter containing the
    client name, and a ``client-url`` parameter containing the URL of where
    to send authentication data upon a successful login. Callers may include
    a ``next`` parameter containing a URL for redirection, making sure to
    encode any query parameters in that URL.

    Version Added:
        5.0.5
    """

    template_name = 'accounts/client_login.html'

    def get_context_data(self, **kwargs) -> dict:
        """Return extra data for rendering the template.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent class.

        Returns:
            dict:
            Context to use when rendering the template.
        """
        context = super().get_context_data(**kwargs)

        context['js_view_data'] = self.get_js_view_data()
        error = context['js_view_data'].pop('error', '')

        if error:
            context['error'] = error

        return context

    def get_js_view_data(self) -> dict:
        """Return the data for the ClientLoginView JavaScript view.

        Returns:
            dict:
            Data to be passed to the JavaScript view.
        """
        client_allowed = self.client_allowed
        client_name = self.client_name
        client_url = self.client_url
        payload = {}
        error = ''

        if client_allowed:
            expire_amount = \
                self.siteconfig.get('client_token_expiration')

            if expire_amount:
                assert isinstance(expire_amount, int)
                expires = (timezone.now() +
                           datetime.timedelta(days=expire_amount))
            else:
                expires = None

            try:
                api_token = WebAPIToken.objects.get_or_create_client_token(
                    client_name=client_name,
                    expires=expires,
                    user=self.request.user)[0]

                payload = {
                    'api_token': api_token.token,
                }
            except WebAPITokenGenerationError:
                error = _(
                    'Failed to generate a unique API token for '
                    'authentication. Please reload the page to try again.')
        else:
            logger.warning('Blocking an attempt to send authentication info '
                           'to unsafe URL %s', client_url)
        return {
            'clientName': escape(client_name),
            'clientURL': quote(client_url),
            'error': error,
            'payload': payload,
            'redirectTo': self.redirect_to,
            'username': self.request.user.username,
        }


class ClientLoginConfirmationView(BaseClientLoginView):
    """View for rendering the client login confirmation page.

    This page asks the user if they want to authenticate the client as
    the current user who is logged in to Review Board. If yes, they will be
    redirected to the client login page. If not, they will be logged
    out and redirected to the login page.

    Callers must include a ``client-name`` query parameter containing the
    client name, and a ``client-url`` parameter containing the URL of where
    to send authentication data upon a successful login. Callers may include
    a ``next`` parameter containing a URL for redirection, making sure to
    encode any query parameters in that URL.

    Version Added:
        5.0.5
    """

    template_name = 'accounts/client_login_confirm.html'

    def get_context_data(self, **kwargs) -> dict:
        """Return extra data for rendering the template.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent class.

        Returns:
            dict:
            Context to use when rendering the template.
        """
        context = super().get_context_data(**kwargs)

        client_name = self.client_name
        client_url = self.client_url
        redirect_field_name = self.redirect_field_name
        redirect_to = self.redirect_to
        client_redirect_param_str = ''

        if redirect_to:
            client_redirect_param_str = (
                '&%s=%s' % (redirect_field_name, redirect_to))

        context['client_login_url'] = (
            '%s?client-name=%s&client-url=%s%s'
            % (local_site_reverse('client-login'),
               client_name,
               client_url,
               client_redirect_param_str))

        # The client redirect part of the URL is encoded twice
        # in order to preserve all of its query parameters.
        logout_redirect = quote(
            '%s?client-name=%s&client-url=%s%s'
            % (local_site_reverse('login'),
               client_name,
               client_url,
               client_redirect_param_str))
        context['logout_url'] = (
            '%s?%s=%s'
            % (local_site_reverse('logout'),
               redirect_field_name,
               logout_redirect))

        return context


def _get_client_allowed_hosts(
    port: Optional[int],
) -> set:
    """Return the set of hosts that are allowed to authenticate clients.

    This will return a set of the local host names at the given port,
    or with no port specified if one is not given.

    Version Added:
        5.0.5

    Args:
        port (int):
            The specific port to allow for the hosts. If this is
            ``None`` then no port will be specified.

    Returns:
        set:
        The set of allowed hosts.
    """
    if port:
        suffix = f':{port}'
    else:
        suffix = ''

    return {
        f'127.0.0.1{suffix}',
        f'localhost{suffix}'
    }
