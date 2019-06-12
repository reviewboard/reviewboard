"""Unit tests for reviewboard.admin.form_widgets.RelatedGroupWidget."""

from __future__ import unicode_literals

from django import forms

from reviewboard.admin.form_widgets import RelatedGroupWidget
from reviewboard.reviews.models import Group
from reviewboard.testing.testcase import TestCase


class TestForm(forms.Form):
    """A Test Form with a field that contains a RelatedGroupWidget."""
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(visible=True).order_by('name'),
        label=('Default groups'),
        required=False,
        widget=RelatedGroupWidget())


class LocalSiteTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedGroupWidget.

    The RelatedGroupWidget is defined to have a local_site_name.
    """
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(visible=True).order_by('name'),
        label=('Default groups'),
        required=False,
        widget=RelatedGroupWidget(local_site_name='supertest'))


class SingleValueTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedGroupWidget.

    RelatedGroupWidget is defined as setting multivalued to False.
    """
    my_select_field = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(visible=True).order_by('name'),
        label=('Default groups'),
        required=False,
        widget=RelatedGroupWidget(multivalued=False))


class RelatedGroupWidgetTests(TestCase):
    """Unit tests for RelatedGroupWidget."""

    def test_render_empty(self):
        """Testing RelatedGroupWidget.render with no initial data"""
        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [],
            {'id': 'groups'})

        self.assertHTMLEqual(
            """<input id="groups" name="Default groups" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedGroupSelectorView({
                    $input: $('#groups'),
                    initialOptions: [],

                    multivalued: true,
                    inviteOnly: false
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedGroupWidget.render with initial data"""
        test_group_1 = self.create_review_group(name='group1')
        test_group_2 = self.create_review_group(name='group2')
        test_group_3 = self.create_review_group(name='group3')

        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [test_group_1.pk, test_group_2.pk, test_group_3.pk],
            {'id': 'groups'})

        self.assertHTMLEqual(
            """<input id="groups" name="Default groups" type="hidden"
                      value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedGroupSelectorView({
                    $input: $('#groups'),
                    initialOptions:
                    [{"display_name": "", "id": 1, "name": "group1"},
                    {"display_name": "", "id": 2, "name": "group2"},
                    {"display_name": "", "id": 3, "name": "group3"}],

                    multivalued: true,
                    inviteOnly: false
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedGroupWidget.render with a local site defined"""
        my_form = LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default groups',
            [],
            {'id': 'groups'})

        self.assertIn("localSitePrefix: 's/supertest/',", html)

    def test_value_from_datadict(self):
        """Testing RelatedGroupWidget.value_from_datadict"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'groups': ['1', '2']},
                {},
                'groups'))

        self.assertEqual(value, ['1', '2'])

    def test_value_from_datadict_single_value(self):
        """Testing RelatedGroupWidget.value_from_datadict with single value"""
        my_form = SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'groups': ['1']},
                {},
                'groups'))

        self.assertEqual(value, ['1'])

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedGroupWidget.value_from_datadict with no data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'groups': []},
                {},
                'groups'))

        self.assertEqual(value, [])

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedGroupWidget.value_from_datadict with missing data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'groups'))
        self.assertIsNone(value)
