"""Unit tests for reviewboard.admin.forms.change_form.ChangeFormFieldset."""

from __future__ import unicode_literals

from django.contrib.admin.helpers import AdminForm
from django.contrib.auth.models import User

from reviewboard.admin import admin_site
from reviewboard.admin.forms.change_form import (ChangeFormFieldset,
                                                 ChangeFormRow)
from reviewboard.testing.testcase import TestCase
from reviewboard.admin.templatetags.rbadmintags import change_form_fieldsets


class ChangeFormFieldsetTests(TestCase):
    """Unit tests for ChangeFormFieldset."""

    def setUp(self):
        super(ChangeFormFieldsetTests, self).setUp()

        request = self.create_http_request()
        model_admin = admin_site.get_model_admin(User)

        self.admin_form = AdminForm(
            form=model_admin.get_form(request)(),
            fieldsets=list(model_admin.get_fieldsets(request)),
            prepopulated_fields=model_admin.get_prepopulated_fields(request),
            readonly_fields=model_admin.get_readonly_fields(request),
            model_admin=model_admin)

    def test_init_normalizes_classes(self):
        """Testing ChangeFormFieldset.__init__ normalizes Django fieldset CSS
        classes
        """
        fieldset = ChangeFormFieldset(form=self.admin_form,
                                      classes=('collapse', 'wide', '-is-test'))
        self.assertEqual(
            fieldset.classes,
            'rb-c-form-fieldset -can-collapse -is-collapsed -is-wide -is-test')

    def test_collapsed_with_true(self):
        """Testing ChangeFormFieldset.collapsed with Django collapse CSS class
        """
        fieldset = ChangeFormFieldset(form=self.admin_form,
                                      classes=('collapse',))
        self.assertTrue(fieldset.collapsed)

    def test_collapsed_with_false(self):
        """Testing ChangeFormFieldset.collapsed without Django collapse CSS
        class
        """
        fieldset = ChangeFormFieldset(form=self.admin_form)
        self.assertFalse(fieldset.collapsed)

    def test_iter(self):
        """Testing ChangeFormFieldset.__iter__"""
        fieldset = list(change_form_fieldsets(self.admin_form))[0]

        rows = list(fieldset)
        self.assertGreater(len(rows), 0)

        for row in rows:
            self.assertIsInstance(row, ChangeFormRow)
