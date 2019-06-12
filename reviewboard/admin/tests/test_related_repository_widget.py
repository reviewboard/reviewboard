"""Unit tests for reviewboard.admin.form_widgets.RelatedRepositoryWidget."""

from __future__ import unicode_literals

from django import forms

from reviewboard.admin.form_widgets import RelatedRepositoryWidget
from reviewboard.scmtools.models import Repository
from reviewboard.testing.testcase import TestCase


class TestForm(forms.Form):
    """A Test Form with a field that contains a RelatedRepositoryWidget."""
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        label=('Repositories'),
        required=False,
        widget=RelatedRepositoryWidget())


class LocalSiteTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedRepositoryWidget.

    The RelatedRepositoryWidget is defined to have a local_site_name.
    """
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        label=('Repositories'),
        required=False,
        widget=RelatedRepositoryWidget(local_site_name='supertest'))


class SingleValueTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedRepositoryWidget.

    RelatedRepositoryWidget is defined as setting multivalued to False.
    """
    my_select_field = forms.ModelMultipleChoiceField(
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        label=('Repositories'),
        required=False,
        widget=RelatedRepositoryWidget(multivalued=False))


class RelatedRepositoryWidgetTests(TestCase):
    """Unit tests for RelatedRepositoryWidget."""

    fixtures = ['test_scmtools']

    def test_render_empty(self):
        """Testing RelatedRepositoryWidget.render with no initial data"""
        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [],
            {'id': 'repositories'})

        self.assertHTMLEqual(
            """<input id="repositories" name="Repositories" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedRepoSelectorView({
                    $input: $('#repositories'),
                    initialOptions: [],

                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedRepositoryWidget.render with initial data"""
        test_repo_1 = self.create_repository(name='repo1')
        test_repo_2 = self.create_repository(name='repo2')
        test_repo_3 = self.create_repository(name='repo3')

        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [test_repo_1.pk, test_repo_2.pk, test_repo_3.pk],
            {'id': 'repositories'})

        self.assertHTMLEqual(
            """<input id="repositories" name="Repositories" type="hidden"
                      value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedRepoSelectorView({
                    $input: $('#repositories'),
                    initialOptions: [{"id": 1, "name": "repo1"},
                    {"id": 2, "name": "repo2"},
                    {"id": 3, "name": "repo3"}],

                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedRepositoryWidget.render with a local site defined"""
        my_form = LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Repositories',
            [],
            {'id': 'repositories'})

        self.assertIn("localSitePrefix: 's/supertest/',", html)

    def test_value_from_datadict(self):
        """Testing RelatedRepositoryWidget.value_from_datadict"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'repository': ['1', '2']},
                {},
                'repository'))

        self.assertEqual(['1', '2'], value)

    def test_value_from_datadict_single_value(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with a single
        value
        """
        my_form = SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'repository': ['1']},
                {},
                'repository'))

        self.assertEqual(value, ['1'])

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with no data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'repository': []},
                {},
                'repository'))

        self.assertEqual(value, [])

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedRepositoryWidget.value_from_datadict with missing
        data
        """
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'repository'))

        self.assertIsNone(value)
