from __future__ import unicode_literals

import logging
from warnings import warn

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from djblets.configforms.mixins import DynamicConfigPageMixin
from djblets.configforms.pages import ConfigPage
from djblets.configforms.registry import ConfigPageRegistry
from djblets.registries.errors import ItemLookupError
from djblets.registries.mixins import ExceptionFreeGetterMixin

from reviewboard.admin.server import build_server_url
from reviewboard.accounts.forms.pages import (AccountSettingsForm,
                                              APITokensForm,
                                              AvatarSettingsForm,
                                              ChangePasswordForm,
                                              PrivacyForm,
                                              GroupsForm,
                                              OAuthApplicationsForm,
                                              OAuthTokensForm,
                                              ProfileForm)
from reviewboard.deprecation import RemovedInReviewBoard40Warning


class AccountPageRegistry(ExceptionFreeGetterMixin, ConfigPageRegistry):
    """A registry for managing account pages."""

    lookup_attrs = ('page_id',)

    def get_defaults(self):
        """Return the default page classes.

        Returns:
            type: The page classes, as subclasses of :py:class:`AccountPage`.
        """
        return (PrivacyPage, ProfilePage, AccountSettingsPage, GroupsPage,
                AuthenticationPage, OAuth2Page)

    def unregister(self, page_class):
        """Unregister the page class.

        Args:
            page_class (type):
                The page class to unregister.

        Raises:
            ItemLookupError:
                This exception is raised if the specified page class cannot
                be found.
        """
        try:
            super(AccountPageRegistry, self).unregister(page_class)
        except ItemLookupError as e:
            logging.error(e)
            raise e


class AccountPage(DynamicConfigPageMixin, ConfigPage):
    """Base class for a page of forms in the My Account page.

    Each AccountPage is represented in the My Account page by an entry
    in the navigation sidebar. When the user has navigated to that page,
    any forms shown on the page will be displayed.

    Extensions can provide custom pages in order to offer per-user
    customization.
    """

    registry = AccountPageRegistry()

    @classmethod
    def get_absolute_url(cls):
        """Return the absolute URL of the page.

        Returns:
            unicode:
            The absolute URL of the page.
        """
        assert cls.page_id
        return (
            '%s#%s'
            % (build_server_url(reverse('user-preferences')),
               cls.page_id)
        )


class AccountSettingsPage(AccountPage):
    """A page containing the primary settings the user can customize."""

    page_id = 'settings'
    page_title = _('Settings')
    form_classes = [AccountSettingsForm]


class AuthenticationPage(AccountPage):
    """A page containing authentication-related forms.

    By default, this just shows the Change Password form, but extensions
    can provide additional forms for display.
    """

    page_id = 'authentication'
    page_title = _('Authentication')
    form_classes = [ChangePasswordForm, APITokensForm, OAuthTokensForm]


class ProfilePage(AccountPage):
    """A page containing settings for the user's profile."""

    page_id = 'profile'
    page_title = _('Profile')
    form_classes = [ProfileForm, AvatarSettingsForm]


class GroupsPage(AccountPage):
    """A page containing a filterable list of groups to join."""

    page_id = 'groups'
    page_title = _('Groups')
    form_classes = [GroupsForm]


class OAuth2Page(AccountPage):
    """A page containing a list of OAuth2 applications to manage."""

    page_id = 'oauth2'
    page_title = 'OAuth2 Applications'
    form_classes = [OAuthApplicationsForm]


class PrivacyPage(AccountPage):
    """A page containing information on a user's privacy rights."""

    page_id = 'privacy'
    page_title = _('My Privacy Rights')
    form_classes = [PrivacyForm]


def register_account_page_class(cls):
    """Register a custom account page class.

    A page ID is considered unique and can only be registered once.

    Args:
        cls (type):
            The page class to register, as a subclass of
            :py:class:`AccountPage`.

    Raises:
        djblets.registries.errors.AlreadyRegisteredError:
            Raised if the page or any of its forms have already been
            registered.

        djblets.registries.errors.RegistrationError:
            Raised if the page shares an attribute with an already
            registered page or if any of its forms share an attribute
            with an already registered form.
    """
    warn('register_account_page_class is deprecated in Review Board 3.0 and '
         'will be removed; use AccountPage.registry.register instead.',
         RemovedInReviewBoard40Warning)
    AccountPage.registry.register(cls)


def unregister_account_page_class(page_cls):
    """Unregister a previously registered account page class.

    Args:
        page_cls (type):
            The page class to unregister, as a subclass of
            :py:class:`AccountPage`.
    """
    warn('unregister_account_page_class is deprecated in Review Board 3.0 and '
         'will be removed; use AccountPage.registry.unregister instead.',
         RemovedInReviewBoard40Warning)
    AccountPage.registry.unregister(page_cls)


def get_page_class(page_id):
    """Return the account page class with the specified ID.

    Args:
        page_id (unicode):
            The page's unique identifier.

    Returns:
        type:
        The :py:class:`AccountPage` subclass, or ``None`` if it could not be
        found.
    """
    warn('get_page_class is deprecated in Review Board 3.0 and will be '
         'removed; use AccountPage.registry.get instead.',
         RemovedInReviewBoard40Warning)
    return AccountPage.registry.get('page_id', page_id)


def get_page_classes():
    """Yield all registered page classes.

    Yields:
        type: Each registered page class, as a subclass of
        :py:class:`AccountPage`.
    """
    warn('get_page_classes is deprecated in Review Board 3.0 and will be '
         'removed; iterate through AccountPage.registry instead.',
         RemovedInReviewBoard40Warning)
    return iter(AccountPage.registry)
