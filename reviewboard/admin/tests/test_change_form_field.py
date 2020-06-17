"""Unit tests for reviewboard.admin.forms.change_form.ChangeFormField."""

from __future__ import unicode_literals

from django import forms
from django.contrib.admin.helpers import AdminField, AdminReadonlyField
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.utils.safestring import SafeText

from reviewboard.admin import admin_site
from reviewboard.admin.form_widgets import (RelatedGroupWidget,
                                            RelatedRepositoryWidget,
                                            RelatedUserWidget)
from reviewboard.admin.forms.change_form import (ChangeFormField,
                                                 ChangeFormRow)
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.testing.testcase import TestCase


class ChangeFormFieldTests(TestCase):
    """Unit tests for ChangeFormField."""

    def setUp(self):
        super(ChangeFormFieldTests, self).setUp()

        request = self.create_http_request()
        user = self.create_user()

        self.model_admin = admin_site.get_model_admin(User)
        self.form = self.model_admin.get_form(request, user)(instance=user)

    def test_init(self):
        """Testing ChangeFormField.__init__"""
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(form_row=row,
                                admin_field=AdminField(self.form,
                                                       field='username',
                                                       is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field -is-required')
        self.assertTrue(field.is_first)
        self.assertFalse(field.has_field_first)
        self.assertFalse(field.is_checkbox)
        self.assertFalse(field.is_readonly)
        self.assertFalse(field.show_errors)

    def test_init_with_read_only(self):
        """Testing ChangeFormField.__init__ with read-only field"""
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminReadonlyField(self.form,
                                           field='username',
                                           is_first=True,
                                           model_admin=self.model_admin))

        self.assertEqual(field.classes, 'rb-c-form-field -is-read-only')
        self.assertTrue(field.is_first)
        self.assertTrue(field.is_readonly)
        self.assertFalse(field.has_field_first)
        self.assertFalse(field.is_checkbox)
        self.assertFalse(field.show_errors)

    def test_init_with_errors(self):
        """Testing ChangeFormField.__init__ with errors"""
        self.form.errors['username'] = self.form.error_class(['Stuff bad'])
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(self.form,
                                   field='username',
                                   is_first=True))

        self.assertEqual(field.classes,
                         'rb-c-form-field -is-required -has-errors')
        self.assertTrue(field.show_errors)
        self.assertHTMLEqual(field.errors,
                             '<ul class="errorlist"><li>Stuff bad</li></ul>')

    def test_init_with_checkbox(self):
        """Testing ChangeFormField.__init__ with checkbox"""
        row = ChangeFormRow(self.form, field='is_active')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(self.form,
                                   field='is_active',
                                   is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field -has-input-first')
        self.assertTrue(field.has_field_first)
        self.assertTrue(field.is_checkbox)

    def test_init_with_multi_choice(self):
        """Testing ChangeFormField.__init__ with ModelMultipleChoiceField"""
        class MyForm(forms.Form):
            field = forms.ModelMultipleChoiceField(
                queryset=ReviewRequest.objects.all(),
                required=False)

        form = MyForm()
        row = ChangeFormRow(form, field='field')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(form,
                                   field='field',
                                   is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field')
        self.assertIsInstance(form.fields['field'].widget,
                              FilteredSelectMultiple)

    def test_init_with_multi_choice_user(self):
        """Testing ChangeFormField.__init__ with ModelMultipleChoiceField with
        User model
        """
        class MyForm(forms.Form):
            field = forms.ModelMultipleChoiceField(
                queryset=User.objects.all(),
                required=False)

        form = MyForm()
        row = ChangeFormRow(form, field='field')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(form,
                                   field='field',
                                   is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field')
        self.assertIsInstance(form.fields['field'].widget, RelatedUserWidget)

    def test_init_with_multi_choice_repository(self):
        """Testing ChangeFormField.__init__ with ModelMultipleChoiceField with
        Repository model
        """
        class MyForm(forms.Form):
            field = forms.ModelMultipleChoiceField(
                queryset=Repository.objects.all(),
                required=False)

        form = MyForm()
        row = ChangeFormRow(form, field='field')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(form,
                                   field='field',
                                   is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field')
        self.assertIsInstance(form.fields['field'].widget,
                              RelatedRepositoryWidget)

    def test_init_with_multi_choice_group(self):
        """Testing ChangeFormField.__init__ with ModelMultipleChoiceField with
        Group model
        """
        class MyForm(forms.Form):
            field = forms.ModelMultipleChoiceField(
                queryset=Group.objects.all(),
                required=False)

        form = MyForm()
        row = ChangeFormRow(form, field='field')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(form,
                                   field='field',
                                   is_first=True))

        self.assertEqual(field.classes, 'rb-c-form-field')
        self.assertIsInstance(form.fields['field'].widget, RelatedGroupWidget)

    def test_label_tag(self):
        """Testing ChangeFormField.label_tag"""
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(form_row=row,
                                admin_field=AdminField(self.form,
                                                       field='username',
                                                       is_first=True))
        html = field.label_tag()

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<label class="rb-c-form-field__label"'
            ' for="id_username">Username:</label>')

    def test_label_tag_with_read_only_field(self):
        """Testing ChangeFormField.label_tag with read-only field"""
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminReadonlyField(self.form,
                                           field='username',
                                           is_first=True,
                                           model_admin=self.model_admin))
        html = field.label_tag()

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<label class="rb-c-form-field__label">Username:</label>')

    def test_label_tag_with_checkbox_field(self):
        """Testing ChangeFormField.label_tag with checkbox field"""
        row = ChangeFormRow(self.form, field='is_active')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminField(self.form,
                                   field='is_active',
                                   is_first=True))
        html = field.label_tag()

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<label class="rb-c-form-field__label" for="id_is_active">'
            'Active</label>')

    def test_render(self):
        """Testing ChangeFormField.render"""
        row = ChangeFormRow(self.form, field='is_active')
        field = ChangeFormField(form_row=row,
                                admin_field=AdminField(self.form,
                                                       field='is_active',
                                                       is_first=True))
        html = field.render()

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<input id="id_is_active" name="is_active" type="checkbox"'
            ' checked>')

    def test_render_with_read_only_field(self):
        """Testing ChangeFormField.render with read-only field"""
        row = ChangeFormRow(self.form, field='username')
        field = ChangeFormField(
            form_row=row,
            admin_field=AdminReadonlyField(self.form,
                                           field='username',
                                           is_first=True,
                                           model_admin=self.model_admin))
        html = field.render()

        self.assertIsInstance(html, SafeText)
        self.assertHTMLEqual(
            html,
            '<div class="rb-c-form-field__readonly-value">test-user</div>')
