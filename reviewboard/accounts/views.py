from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_protect
from djblets.auth.views import register
from djblets.configforms.views import ConfigPagesView
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import augment_method_from

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.forms.registration import RegistrationForm
from reviewboard.accounts.pages import get_page_classes


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
            siteconfig.get("auth_enable_registration")):
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
        """Get the list of page classes for this view."""
        return get_page_classes()

    @cached_property
    def ordered_user_local_sites(self):
        """Get the user's local sites, ordered by name."""
        return self.request.user.local_site.order_by('name')
