"""Hooks for adding to the "My Account" page."""

from __future__ import annotations

from djblets.extensions.hooks import (BaseRegistryMultiItemHook,
                                      ExtensionHook,
                                      ExtensionHookPoint)

from reviewboard.accounts.pages import AccountPage


class AccountPagesHook(BaseRegistryMultiItemHook,
                       metaclass=ExtensionHookPoint):
    """A hook for adding new pages to the My Account page.

    A page can contain one or more forms or even a custom template allowing
    for configuration of an extension.

    This takes a list of AccountPage classes as parameters, which it will
    later instantiate as necessary. Each page can be pre-populated with
    one or more custom AccountPageForm classes.
    """

    registry = AccountPage.registry

    def initialize(self, page_classes):
        """Initialize the hook.

        This will register each of the provided account page classes.

        Args:
            page_classes (list of type):
                The list of page classes to register. Each must be a subclass
                of :py:class:`~reviewboard.accounts.pages.AccountPage`.
        """
        super(AccountPagesHook, self).initialize(page_classes)


class AccountPageFormsHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for adding new forms to a page in the My Account page.

    This is used to add custom forms to a page in the My Account page. The
    form can be used to provide user-level customization of an extension,
    through a traditional form-based approach or even through custom
    JavaScript.

    This hook takes the ID of a registered page where the form should be
    placed. Review Board supplies the following built-in page IDs:

    * ``settings``
    * ``authentication``
    * ``profile``
    * ``groups``

    Any registered page ID can be provided, whether from this extension
    or another.

    Form classes can only be added to a single page.
    """

    def initialize(self, page_id, form_classes):
        """Initialize the hook.

        This will register each of the provided page form classes on the
        account page matching the provided ID.

        Args:
            page_id (unicode):
                The page ID corresponding to a registered
                :py:class:`~reviewboard.accounts.pages.AccountPage`.

            form_classes (list of type):
                The list of form classes to register on the page. Each class
                must be a subclass of
                :py:class:`~reviewboard.accounts.forms.pages.AccountPageForm`.
        """
        self.page_id = page_id
        self.form_classes = form_classes

        page_class = AccountPage.registry.get('page_id', page_id)
        assert page_class is not None

        for form_class in form_classes:
            page_class.add_form(form_class)

    def shutdown(self):
        """Shut down the hook.

        This will unregister each of the page form classes from the associated
        page.
        """
        page_class = AccountPage.registry.get('page_id', self.page_id)
        assert page_class is not None

        for form_class in self.form_classes:
            page_class.remove_form(form_class)
