"""Unit tests for reviewboard.admin.form_widgets.RelatedUserWidget."""

from __future__ import unicode_literals

from django import forms
from django.contrib.auth.models import User

from reviewboard.admin.form_widgets import RelatedUserWidget
from reviewboard.testing.testcase import TestCase


class TestForm(forms.Form):
    """A Test Form with a field that contains a RelatedUserWidget."""
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=('Default users'),
        required=False,
        widget=RelatedUserWidget())


class LocalSiteTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedUserWidget.

    The RelatedUserWidget is defined to have a local_site_name.
    """
    my_multiselect_field = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=('Default users'),
        required=False,
        widget=RelatedUserWidget(local_site_name='supertest'))


class SingleValueTestForm(forms.Form):
    """A Test Form with a field that contains a RelatedUserWidget.

    The RelatedUserWidget is defined as setting multivalued to False.
    """
    my_select_field = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=('Default users'),
        required=False,
        widget=RelatedUserWidget(multivalued=False))


class RelatedUserWidgetTests(TestCase):
    """Unit tests for RelatedUserWidget."""

    fixtures = ['test_users']

    def test_render_empty(self):
        """Testing RelatedUserWidget.render with no initial data"""
        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [],
            {'id': 'default-users'})

        self.assertHTMLEqual(
            """<input id="default-users" name="Default users" type="hidden" />

            <script>
            $(function() {
                var view = new RB.RelatedUserSelectorView({
                    $input: $('#default\\u002Dusers'),
                    initialOptions: [],

                    useAvatars: true,
                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_data(self):
        """Testing RelatedUserWidget.render with initial data"""
        my_form = TestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [1, 2, 3],
            {'id': 'default-users'})

        self.assertHTMLEqual(
            """<input id="default-users" name="Default users"
            type="hidden" value="1,2,3" />

            <script>
            $(function() {
                var view = new RB.RelatedUserSelectorView({
                    $input: $('#default\\u002Dusers'),
                    initialOptions: [{"avatarHTML": "\\u003Cimg
                    src=\\"https://secure.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61?s=20\\u0026d=mm\\"
                    alt=\\"admin\\" width=\\"20\\" height=\\"20\\"
                    srcset=\\"https://secure.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61?s=20\\u0026d=mm 1x,
                    https://secure.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61?s=40\\u0026d=mm 2x,
                    https://secure.gravatar.com/avatar/e64c7d89f26bd1972efa854d13d7dd61?s=60\\u0026d=mm 3x\\"
                    class=\\"avatar djblets-o-avatar\\"\\u003E\\n",
                    "fullname": "Admin User",
                    "id": 1,
                    "username": "admin"},
                    {"avatarHTML": "\\u003Cimg
                    src=\\"https://secure.gravatar.com/avatar/b0f1ae4342591db2695fb11313114b3e?s=20\\u0026d=mm\\"
                    alt=\\"doc\\" width=\\"20\\" height=\\"20\\"
                    srcset=\\"https://secure.gravatar.com/avatar/b0f1ae4342591db2695fb11313114b3e?s=20\\u0026d=mm 1x,
                    https://secure.gravatar.com/avatar/b0f1ae4342591db2695fb11313114b3e?s=40\\u0026d=mm 2x,
                    https://secure.gravatar.com/avatar/b0f1ae4342591db2695fb11313114b3e?s=60\\u0026d=mm 3x\\"
                    class=\\"avatar djblets-o-avatar\\"\\u003E\\n",
                    "fullname": "Doc Dwarf",
                    "id": 2,
                    "username": "doc"},
                    {"avatarHTML": "\\u003Cimg
                    src=\\"https://secure.gravatar.com/avatar/1a0098e6600792ea4f714aa205bf3f2b?s=20\\u0026d=mm\\"
                    alt=\\"dopey\\" width=\\"20\\" height=\\"20\\"
                    srcset=\\"https://secure.gravatar.com/avatar/1a0098e6600792ea4f714aa205bf3f2b?s=20\\u0026d=mm 1x,
                    https://secure.gravatar.com/avatar/1a0098e6600792ea4f714aa205bf3f2b?s=40\\u0026d=mm 2x,
                    https://secure.gravatar.com/avatar/1a0098e6600792ea4f714aa205bf3f2b?s=60\\u0026d=mm 3x\\"
                    class=\\"avatar djblets-o-avatar\\"\\u003E\\n",
                    "fullname": "Dopey Dwarf",
                    "id": 3,
                    "username": "dopey"}],

                    useAvatars: true,
                    multivalued: true
                }).render();
            });
            </script>""",
            html)

    def test_render_with_local_site(self):
        """Testing RelatedUserWidget.render with a local site defined"""
        my_form = LocalSiteTestForm()
        html = my_form.fields['my_multiselect_field'].widget.render(
            'Default users',
            [],
            {'id': 'default-users'})

        self.assertIn("localSitePrefix: 's/supertest/',", html)

    def test_value_from_datadict(self):
        """Testing RelatedUserWidget.value_from_datadict"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'people': ['1', '2']},
                {},
                'people'))

        self.assertEqual(value, ['1', '2'])

    def test_value_from_datadict_single_value(self):
        """Testing RelatedUserWidget.value_from_datadict with a single value"""
        my_form = SingleValueTestForm()
        value = (
            my_form.fields['my_select_field']
            .widget
            .value_from_datadict(
                {'people': ['1']},
                {},
                'people'))

        self.assertEqual(value, ['1'])

    def test_value_from_datadict_with_no_data(self):
        """Testing RelatedUserWidget.value_from_datadict with no data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {'people': []},
                {},
                'people'))
        self.assertEqual(value, [])

    def test_value_from_datadict_with_missing_data(self):
        """Testing RelatedUserWidget.value_from_datadict with missing data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_multiselect_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'people'))

        self.assertIsNone(value)
