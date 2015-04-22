from __future__ import unicode_literals

import logging

from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from djblets.configforms.pages import ConfigPage

from reviewboard.accounts.forms.pages import (AccountSettingsForm,
                                              APITokensForm,
                                              ChangePasswordForm,
                                              ProfileForm,
                                              GroupsForm)


_populated = False
_registered_form_classes = {}
_registered_page_classes = SortedDict()


class AccountPage(ConfigPage):
    """Base class for a page of forms in the My Account page.

    Each AccountPage is represented in the My Account page by an entry
    in the navigation sidebar. When the user has navigated to that page,
    any forms shown on the page will be displayed.

    Extensions can provide custom pages in order to offer per-user
    customization.
    """

    _default_form_classes = None

    @classmethod
    def add_form(cls, form_cls):
        """Add a form class to this page."""
        _register_form_class(form_cls)
        cls.form_classes.append(form_cls)

    @classmethod
    def remove_form(cls, form_cls):
        """Remove a form class from this page.

        The form class must have been previously added to this page.
        """
        form_id = form_cls.form_id

        try:
            cls.form_classes.remove(form_cls)
            del _registered_form_classes[form_id]
        except (KeyError, ValueError):
            logging.error('Failed to unregister unknown account form "%s"',
                          form_id)
            raise KeyError('"%s" is not a registered account form' % form_id)


class AccountSettingsPage(AccountPage):
    """A page containing the primary settings the user can customize."""

    page_id = 'settings'
    page_title = _('Settings')
    form_classes = [AccountSettingsForm]


class APITokensPage(AccountPage):
    """A page containing settings for API tokens."""

    page_id = 'api-tokens'
    page_title = _('API Tokens')
    form_classes = [APITokensForm]


class AuthenticationPage(AccountPage):
    """A page containing authentication-related forms.

    By default, this just shows the Change Password form, but extensions
    can provide additional forms for display.
    """

    page_id = 'authentication'
    page_title = _('Authentication')
    form_classes = [ChangePasswordForm]


class ProfilePage(AccountPage):
    """A page containing settings for the user's profile."""

    page_id = 'profile'
    page_title = _('Profile')
    form_classes = [ProfileForm]


class GroupsPage(AccountPage):
    """A page containing a filterable list of groups to join."""

    page_id = 'groups'
    page_title = _('Groups')
    form_classes = [GroupsForm]


def _populate_defaults():
    """Populate the default list of page classes."""
    global _populated

    if not _populated:
        _populated = True

        for page_cls in (GroupsPage, AccountSettingsPage, AuthenticationPage,
                         ProfilePage, APITokensPage):
            register_account_page_class(page_cls)


def _clear_page_defaults():
    """Clear the default list of pages.

    This is really only used by unit tests to put things back into a default
    state.
    """
    global _populated

    _populated = False
    _registered_page_classes.clear()
    _registered_form_classes.clear()


def _register_form_class(form_cls):
    """Register an account form class.

    This will check if the form has already been registered before adding it.
    It's called internally when first adding a page, or when adding a form
    to a page.
    """
    form_id = form_cls.form_id

    if form_id in _registered_form_classes:
        raise KeyError(
            '"%s" is already a registered account form. Form IDs must be '
            'unique across all account pages.'
            % form_id)

    _registered_form_classes[form_id] = form_cls


def register_account_page_class(page_cls):
    """Register a custom account page class.

    A page ID is considered unique and can only be registered once. A
    KeyError will be thrown if attempting to register a second time.
    """
    _populate_defaults()

    page_id = page_cls.page_id

    if page_id in _registered_page_classes:
        raise KeyError('"%s" is already a registered account page'
                       % page_id)

    _registered_page_classes[page_id] = page_cls

    # Set the form_classes to an empty list by default if it doesn't explicitly
    # provide its own, so that entries don't go into AccountPage's global
    # list.
    if page_cls.form_classes is None:
        page_cls.form_classes = []

    # Set _default_form_classes when an account page class first registers.
    if page_cls._default_form_classes is None:
        page_cls._default_form_classes = list(page_cls.form_classes)

    # If form_classes is empty, reload the list from _default_form_classes.
    if not page_cls.form_classes:
        page_cls.form_classes = list(page_cls._default_form_classes)

    for form_cls in page_cls.form_classes:
        _register_form_class(form_cls)


def unregister_account_page_class(page_cls):
    """Unregister a previously registered account page class."""
    _populate_defaults()

    page_id = page_cls.page_id

    if page_id not in _registered_page_classes:
        logging.error('Failed to unregister unknown account page "%s"',
                      page_id)
        raise KeyError('"%s" is not a registered account page' % page_id)

    for form_cls in page_cls.form_classes:
        page_cls.remove_form(form_cls)

    del _registered_page_classes[page_id]


def get_page_class(page_id):
    """Get the My Account page class with the specified ID.

    If the page could not be found, this will return None.
    """
    _populate_defaults()

    try:
        return _registered_page_classes[page_id]
    except KeyError:
        return None


def get_page_classes():
    """Get all registered page classes."""
    _populate_defaults()

    return six.itervalues(_registered_page_classes)
