"""Unit tests for reviewboard.accounts.pages.AccountPage."""

from __future__ import unicode_literals

from djblets.registries.errors import RegistrationError

from reviewboard.accounts.forms.pages import AccountPageForm
from reviewboard.accounts.pages import (AccountPage,
                                        get_page_classes,
                                        register_account_page_class,
                                        unregister_account_page_class)
from reviewboard.testing import TestCase


class AccountPageTests(TestCase):
    """Unit tests for reviewboard.accounts.pages.AccountPage."""

    @classmethod
    def setUpClass(cls):
        super(AccountPageTests, cls).setUpClass()

        cls.builtin_pages = set(AccountPage.registry.get_defaults())

    def tearDown(self):
        """Uninitialize this test case."""
        super(AccountPageTests, self).tearDown()
        AccountPage.registry.reset()

    def test_default_pages(self):
        """Testing default list of account pages."""
        self.assertEqual(set(get_page_classes()), self.builtin_pages)

    def test_register_account_page_class(self):
        """Testing register_account_page_class."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)

        self.assertEqual(
            set(get_page_classes()),
            self.builtin_pages | {MyPage}
        )

    def test_register_account_page_class_with_duplicate(self):
        """Testing register_account_page_class with duplicate page."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)

        with self.assertRaises(RegistrationError):
            register_account_page_class(MyPage)

    def test_unregister_account_page_class(self):
        """Testing unregister_account_page_class."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)
        unregister_account_page_class(MyPage)

        self.assertEqual(set(get_page_classes()), self.builtin_pages)

    def test_unregister_unknown_account_page_class(self):
        """Testing unregister_account_page_class with unknown page."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        with self.assertRaises(AccountPage.registry.lookup_error_class):
            unregister_account_page_class(MyPage)

    def test_add_form_to_page(self):
        """Testing AccountPage.add_form."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        register_account_page_class(MyPage)
        MyPage.add_form(MyForm)

        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_add_duplicate_form_to_page(self):
        """Testing AccountPage.add_form with duplicate form ID."""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)

        with self.assertRaises(RegistrationError):
            MyPage.add_form(MyForm)

        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_remove_form_from_page(self):
        """Testing AccountPage.remove_form."""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)
        MyPage.remove_form(MyForm)

        self.assertEqual(MyPage.form_classes, [])

    def test_remove_unknown_form_from_page(self):
        """Testing AccountPage.remove_form with unknown form."""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        register_account_page_class(MyPage)

        with self.assertRaises(AccountPage.registry.lookup_error_class):
            MyPage.remove_form(MyForm)

    def test_default_form_classes_for_page(self):
        """Testing AccountPage._default_form_classes persistence"""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'
            form_classes = [MyForm]

        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])
        unregister_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_empty_default_form_classes_for_page(self):
        """Testing AccountPage._default_form_classes with no form_classes"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        MyPage.add_form(MyForm)
        self.assertEqual(MyPage.form_classes, [MyForm])
        unregister_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        register_account_page_class(MyPage)
        self.assertEqual(MyPage.form_classes, [])
