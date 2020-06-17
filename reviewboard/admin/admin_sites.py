"""Django AdminSite customization for Review Board."""

from __future__ import unicode_literals

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import (AdminSite as DjangoAdminSite,
                                        site as _django_site)
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.forms.auth import ReviewBoardAuthenticationFormMixin


class AuthenticationForm(ReviewBoardAuthenticationFormMixin,
                         AdminAuthenticationForm):
    """Authentication form for the administration UI.

    This builds upon the main admin authentication form (which handles
    permission checks when verifying a username) by incorporating the
    capabilities of the main Review Board administration form, allowing
    e-mail addresses as usernames and rate limiting login attempts.

    Version Added:
        4.0
    """


class AdminSite(DjangoAdminSite):
    """Main administration site for Review Board.

    This provides customization of the administration UI, while maintaining
    Model/Admin registration compatibility with the standard Django
    administration UI.

    Technically, this is focused on the Database section of the administration
    UI, though it's planned to be used to consolidate more of the UI in the
    future.

    All code should reference :py:data:`admin_site` where possible, rather than
    :py:data:`django.contrib.admin.site`.

    Version Added:
        4.0
    """

    site_title = _('Database')
    site_header = _('Database')
    index_title = _('Database')

    login_form = AuthenticationForm

    def __init__(self, *args, **kwargs):
        """Initialize the site.

        Args:
            *args (tuple):
                Positional arguments for the parent class.

            **kwargs (dict):
                Keyword arguments for the parent class.
        """
        super(AdminSite, self).__init__(*args, **kwargs)

        # Mirror these registration tables from the main Django site, since
        # we want to behave exactly like that one.
        self._registry = _django_site._registry
        self._actions = _django_site._actions
        self._global_actions = _django_site._global_actions

    def get_model_admin(self, model_cls):
        """Return the ModelAdmin for a given Model class.

        Args:
            model_cls (type):
                The registered model class.

        Returns:
            django.contrib.admin.ModelAdmin:
            The ModelAdmin for the Model, or ``None`` if one is not registered.
        """
        return self._registry.get(model_cls)


#: The main instance for the Review Board administration site.
#:
#: Version Added:
#:     4.0
admin_site = AdminSite()
