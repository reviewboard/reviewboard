"""Unit tests for reviewboard.admin.form_widgets.LexersMappingWidget."""

from django import forms
from django.utils.html import escape, format_html
from pygments.lexers import get_all_lexers

from reviewboard.admin.form_widgets import LexersMappingWidget
from reviewboard.testing.testcase import TestCase


class TestForm(forms.Form):
    """A Test Form with a field that contains a LexersMappingWidget."""

    my_mapping_field = forms.CharField(
        label=('Lexer Mapping'),
        required=False,
        widget=LexersMappingWidget())


class LexersMappingWidgetTests(TestCase):
    """Unit tests for LexersMappingWidget."""

    def test_render_empty(self):
        """Testing LexersMappingWidget.render with no initial data"""
        my_form = TestForm()
        html = my_form.fields['my_mapping_field'].widget.render(
            'Lexer Mapping',
            (),
            {'id': 'lexer-mapping'})

        correct_html_parts = [
            '<input type="text" name="Lexer Mapping_0" id="lexer-mapping_0">',
            '<select name="Lexer Mapping_1" id="lexer-mapping_1">'
        ]

        for lex in get_all_lexers():
            lex_name = escape(lex[0])
            correct_html_parts.append(format_html(
                '<option value="{}">{}</option>', lex_name, lex_name))

        correct_html_parts.append('</select>')
        correct_html = ''.join(correct_html_parts)

        self.assertHTMLEqual(correct_html, html)

    def test_render_with_data(self):
        """Testing LexersMappingWidget.render with initial data"""
        my_form = TestForm()
        html = my_form.fields['my_mapping_field'].widget.render(
            'Lexer Mapping',
            ('.py', 'Python'),
            {'id': 'lexer-mapping'})

        correct_html_parts = [
            '<input type="text" name="Lexer Mapping_0"',
            'value=".py" id="lexer-mapping_0">',
            '<select name="Lexer Mapping_1" id="lexer-mapping_1">'
        ]

        for lex in get_all_lexers():
            lex_name = escape(lex[0])

            if lex_name == 'Python':
                correct_html_parts.append(format_html(
                    '<option value="{}" selected>{}</option>', lex_name,
                    lex_name))
            else:
                correct_html_parts.append(format_html(
                    '<option value="{}">{}</option>', lex_name, lex_name))

        correct_html_parts.append('</select>')
        correct_html = ''.join(correct_html_parts)

        self.assertHTMLEqual(correct_html, html)

    def test_value_from_datadict(self):
        """Testing LexersMappingWidget.value_from_datadict"""
        my_form = TestForm()
        value = (
            my_form.fields['my_mapping_field']
            .widget
            .value_from_datadict(
                {'mapping_0': '.py',
                 'mapping_1': 'Python'},
                {},
                'mapping'))
        self.assertEqual(value, ('.py', 'Python'))

    def test_value_from_datadict_with_no_data(self):
        """Testing LexersMappingWidget.value_from_datadict with no data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_mapping_field']
            .widget
            .value_from_datadict(
                {'mapping_0': '',
                 'mapping_1': ''},
                {},
                'mapping'))
        self.assertEqual(value, ('', ''))

    def test_value_from_datadict_with_missing_data(self):
        """Testing LexersMappingWidget.value_from_datadict with missing data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_mapping_field']
            .widget
            .value_from_datadict(
                {},
                {},
                'mapping'))
        self.assertEqual(value, (None, None))

    def test_decompress(self):
        """Testing LexersMappingWidget.decompress"""
        my_form = TestForm()
        value = (
            my_form.fields['my_mapping_field']
            .widget
            .decompress(('.py', 'Python')))
        self.assertEqual(value, ['.py', 'Python'])

    def test_decompress_with_no_data(self):
        """Testing LexersMappingWidget.decompress with no data"""
        my_form = TestForm()
        value = (
            my_form.fields['my_mapping_field']
            .widget
            .decompress(()))
        self.assertEqual(value, [None, None])
