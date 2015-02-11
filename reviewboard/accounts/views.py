from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
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
    """
    Handles redirection to the appropriate registration page, depending
    on the authentication type the user has configured.
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

    js_bundle_names = ['account-page']

    @method_decorator(login_required)
    @augment_method_from(ConfigPagesView)
    def dispatch(self, *args, **kwargs):
        pass

    @property
    def nav_title(self):
        return self.request.user.username

    @property
    def page_classes(self):
        return get_page_classes()
