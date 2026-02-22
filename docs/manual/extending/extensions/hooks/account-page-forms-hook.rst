.. _account-page-forms-hook:

====================
AccountPageFormsHook
====================

:py:class:`reviewboard.extensions.hooks.AccountPageFormsHook` allows
extensions to register forms on existing "pages" on the My Account page.
These can be used to provide user-level customization for an extension,
information display, or anything else the extension may need.

A caller must subclass
:py:class:`reviewboard.accounts.forms.pages.AccountPageForm` and fill in the
required fields: :py:attr:`form_id` and :py:attr:`form_title`.  It generally
will then need to provide one or more fields for display, plus ``load()`` and
``save()`` methods.

The custom form (or forms) are then registered by instantiating the hook and
passing in the list of form classes.

Form IDs must be unique. It is best to choose a form ID that contains some
sort of extension-specific information, such as the vendor or the extension
ID.


Example
=======

.. code-block:: python

    from django import forms
    from reviewboard.accounts.forms.pages import AccountPageForm
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import AccountPageFormsHook


    class SamplePageForm(AccountPageForm):
        form_id = 'myvendor_form'
        form_title = 'My Form'

        my_field = forms.CharField(label='My Field', max_length=100)


    class SampleExtension(Extension):
        def initialize(self):
            AccountPageFormsHook(self, [SamplePageForm])
