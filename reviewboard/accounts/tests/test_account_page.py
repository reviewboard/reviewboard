"""Unit tests for reviewboard.accounts.pages.AccountPage."""

from __future__ import unicode_literals

from djblets.registries.errors import RegistrationError

from reviewboard.accounts.forms.pages import AccountPageForm
from reviewboard.accounts.pages import AccountPage
from reviewboard.testing import TestCase


class AccountPageTests(TestCase):
    """Unit tests for reviewboard.accounts.pages.AccountPage."""

    def tearDown(self):
        """Uninitialize this test case."""
        super(AccountPageTests, self).tearDown()
        AccountPage.registry.reset()

    def test_add_form_to_page(self):
        """Testing AccountPage.add_form."""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        AccountPage.registry.register(MyPage)
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

        AccountPage.registry.register(MyPage)

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

        AccountPage.registry.register(MyPage)
        MyPage.remove_form(MyForm)

        self.assertEqual(MyPage.form_classes, [])

    def test_remove_unknown_form_from_page(self):
        """Testing AccountPage.remove_form with unknown form."""
        class MyForm(AccountPageForm):
            form_id = 'test-form'

        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        AccountPage.registry.register(MyPage)

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

        AccountPage.registry.register(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])
        AccountPage.registry.unregister(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        AccountPage.registry.register(MyPage)
        self.assertEqual(MyPage.form_classes, [MyForm])

    def test_empty_default_form_classes_for_page(self):
        """Testing AccountPage._default_form_classes with no form_classes"""
        class MyPage(AccountPage):
            page_id = 'test-page'
            page_title = 'Test Page'

        class MyForm(AccountPageForm):
            form_id = 'test-form'

        AccountPage.registry.register(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        MyPage.add_form(MyForm)
        self.assertEqual(MyPage.form_classes, [MyForm])
        AccountPage.registry.unregister(MyPage)
        self.assertEqual(MyPage.form_classes, [])
        AccountPage.registry.register(MyPage)
        self.assertEqual(MyPage.form_classes, [])
