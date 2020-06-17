"""Unit tests for reviewboard.admin.forms.change_form.ChangeFormRow."""

from __future__ import unicode_literals

from django.contrib.auth.models import User

from reviewboard.admin import admin_site
from reviewboard.admin.forms.change_form import (ChangeFormField,
                                                 ChangeFormRow)
from reviewboard.testing.testcase import TestCase


class ChangeFormRowTests(TestCase):
    """Unit tests for ChangeFormRow."""

    def setUp(self):
        super(ChangeFormRowTests, self).setUp()

        request = self.create_http_request()
        model_admin = admin_site.get_model_admin(User)

        self.form = model_admin.get_form(request)()

    def test_classes(self):
        """Testing ChangeFormRow.classes"""
        row = ChangeFormRow(self.form,
                            field='username')

        self.assertEqual(row.classes, 'rb-c-form-row field-username')

    def test_iter(self):
        """Testing ChangeFormRow.__iter__"""
        row = ChangeFormRow(self.form,
                            field='username')

        fields = list(row)
        self.assertEqual(len(fields), 1)

        field = fields[0]
        self.assertIsInstance(field, ChangeFormField)
        self.assertEqual(field.field.name, 'username')
