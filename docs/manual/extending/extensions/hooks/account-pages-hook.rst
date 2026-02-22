.. _account-pages-hook:

================
AccountPagesHook
================

:py:class:`reviewboard.extensions.hooks.AccountPagesHook` allows extensions to
add new "pages" to the My Account page. These can be used to provide
user-level customization for an extension, information display, or anything
else the extension may need.

These pages can contain one or more forms, registered either by this extension
or by another. If needed, they can even provide their own custom template,
though it is recommended to use a form-based approach.

A caller must subclass :py:class:`reviewboard.accounts.pages.AccountPage` and
fill in the required fields: :py:attr:`page_id` and :py:attr:`page_title`.
It will also generally need to provide :py:attr:`form_classes`, which is a
list of :py:class:`reviewboard.accounts.forms.pages.AccountPageForm`.

The custom page (or pages) are then registered by instantiating the hook and
passing in the list of page classes.

Page IDs must be unique. It is best to choose a page ID that contains some
sort of extension-specific information, such as the vendor or the extension
ID. Page IDs are used when registered new forms (using
:ref:`account-page-forms-hook`) in order to specify where the form should
appear.


Example
=======

.. code-block:: python

    from django.db import models
    from reviewboard.accounts.forms.pages import AccountPageForm
    from reviewboard.accounts.pages import AccountPage
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import AccountPagesHook


    class SamplePageForm(AccountPageForm):
        form_id = 'myvendor_form'
        form_title = 'My Form'

        my_field = models.CharField(max_length=100)


    class SamplePage(AccountPage):
        page_id = 'myvendor_page'
        page_title = 'My Page'
        form_classes = [SamplePageForm]


    class SampleExtension(Extension):
        def initialize(self):
            AccountPagesHook(self, [SamplePage])
