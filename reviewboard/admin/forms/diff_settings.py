"""Administration form for diff viewer settings."""

from __future__ import annotations

import re
from typing import Any, Dict, List, cast

from django import forms
from django.utils.translation import gettext_lazy as _
from djblets.forms.fields import ListEditDictionaryField
from djblets.forms.widgets import ListEditWidget
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.form_widgets import LexersMappingWidget
from reviewboard.codesafety.checkers.trojan_source import \
    TrojanSourceCodeSafetyChecker


class DiffSettingsForm(SiteSettingsForm):
    """Diff settings for Review Board."""

    css_bundle_names = ['djblets-forms']
    js_bundle_names = ['djblets-forms']

    diffviewer_syntax_highlighting = forms.BooleanField(
        label=_('Show syntax highlighting'),
        help_text=_(
            'Show the content of files with colors and formatting to help '
            'reviewers read and follow the code.'
        ),
        required=False)

    diffviewer_syntax_highlighting_threshold = forms.IntegerField(
        label=_('Max lines for syntax highlighting'),
        help_text=_(
            'Files with lines greater than this number will not have '
            'syntax highlighting. Enter 0 to disable limits.'
        ),
        required=False,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_custom_pygments_lexers = ListEditDictionaryField(
        label=_('Custom file highlighting'),
        help_text=_(
            'Set this to override how particular file extensions (in the '
            'form of <code>.ext</code>) are styled.'
        ),
        required=False,
        widget=ListEditWidget(value_widget=LexersMappingWidget))

    diffviewer_show_trailing_whitespace = forms.BooleanField(
        label=_('Show trailing whitespace'),
        help_text=_('Show excess trailing whitespace as red blocks. This '
                    'helps to visualize when a text editor added unwanted '
                    'whitespace to the end of a line.'),
        required=False)

    include_space_patterns = forms.CharField(
        label=_('Show all whitespace for'),
        required=False,
        help_text=_(
            'A comma-separated list of file patterns for which all '
            'whitespace changes should be shown (e.g., "*.py, *.txt"). '
            'This is <strong>no longer recommended</strong>, as it turns off '
            'smart indentation highlighting and can make some changes '
            'harder to review.'
        ),
        widget=forms.TextInput(attrs={'size': '50'}))

    diffviewer_context_num_lines = forms.IntegerField(
        label=_('Lines of context'),
        help_text=_('The number of unchanged lines shown above and below '
                    'changed lines.'),
        initial=5,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_paginate_by = forms.IntegerField(
        label=_('Paginate by'),
        help_text=_('The number of files to display per page in the diff '
                    'viewer.'),
        initial=20,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_paginate_orphans = forms.IntegerField(
        label=_('Paginate orphans'),
        help_text=_('The number of extra files required before adding another '
                    'page to the diff viewer.'),
        initial=10,
        widget=forms.TextInput(attrs={'size': '5'}))

    diffviewer_max_diff_size = forms.IntegerField(
        label=_('Max diff size in bytes'),
        help_text=_(
            'The maximum size (in bytes) for any given diff. Enter 0 to '
            'disable size restrictions. <strong>2097152 (2MB) '
            'is recommended</strong>, as larger diffs usually cannot be '
            'reviewed by humans and may cause performance problems and '
            'browser timeouts.'
        ),
        widget=forms.TextInput(attrs={'size': '15'}))

    trojan_source_check_confusables = forms.BooleanField(
        label=_(
            'Check for potentially misleading Unicode characters '
            '("confusables")'
        ),
        help_text=_(
            'This will check for Unicode characters in various languages '
            'that look similar to characters commonly used in source code '
            '(such as Latin characters). These are also known as Unicode '
            '"confusables", and can be used to sneak malicious code into '
            'software, either intentionally or accidentally through '
            'copy/paste.'
        ),
        initial=True,
        required=False)

    trojan_source_confusable_aliases_allowed = forms.MultipleChoiceField(
        label=_('Safe character sets'),
        help_text=_(
            'Characters from these sets are considered safe, and will not be '
            'checked for confusables. This is useful if your team is working '
            'in certain languages that often show up as unsafe. '
            '<em>Attacks using these characters will not be caught.</em>'
        ),
        choices=[
            (_lang, _lang)
            for _lang in (
                TrojanSourceCodeSafetyChecker.get_main_confusable_aliases()
            )
        ],
        required=False,
        widget=forms.widgets.CheckboxSelectMultiple())

    def load(self):
        """Load settings from the form.

        This will populate initial fields based on the site configuration.
        """
        super(DiffSettingsForm, self).load()

        siteconfig = self.siteconfig

        # Load the settings from the Trojan Code checker.
        #
        # In the future, we may want to expand this to dynamically support
        # any and all registered code safety checkers, but that will require
        # additional support in the checkers.
        code_safety_config = cast(
            Dict[str, Dict],
            siteconfig.get('code_safety_checkers'))
        trojan_source_config = cast(
            Dict[str, Any],
            code_safety_config.get(TrojanSourceCodeSafetyChecker.checker_id,
                                   {}))

        if trojan_source_config:
            for key in ('check_confusables',
                        'confusable_aliases_allowed'):
                if key in trojan_source_config:
                    self.fields[f'trojan_source_{key}'].initial = \
                        trojan_source_config[key]

        # Load the "Show all whitespace for" setting.
        self.fields['include_space_patterns'].initial = ', '.join(
            cast(List[str],
                 siteconfig.get('diffviewer_include_space_patterns')))

    def save(self):
        """Save the form.

        This will write the new configuration to the database.
        """
        siteconfig = self.siteconfig

        # Store the settings for the Trojan Code checker.
        code_safety_config = cast(
            Dict[str, Any],
            siteconfig.get('code_safety_checkers'))
        code_safety_config[TrojanSourceCodeSafetyChecker.checker_id] = {
            key: self.cleaned_data[f'trojan_source_{key}']
            for key in ('check_confusables',
                        'confusable_aliases_allowed')
        }
        siteconfig.set('code_safety_checkers', code_safety_config)

        # Save the "Show all whitespace for" setting.
        siteconfig.set(
            'diffviewer_include_space_patterns',
            re.split(r',\s*', self.cleaned_data['include_space_patterns']))

        super(DiffSettingsForm, self).save()

    class Meta:
        title = _('Diff Viewer Settings')

        save_blacklist = (
            'trojan_source_check_confusables',
            'trojan_source_confusable_aliases_allowed',
            'include_space_patterns',
        )

        fieldsets = (
            {
                'title': _('Appearance'),
                'classes': ('wide',),
                'fields': (
                    'diffviewer_show_trailing_whitespace',
                    'diffviewer_syntax_highlighting',
                    'diffviewer_custom_pygments_lexers',
                ),
            },
            {
                'title': _('Limits'),
                'classes': ('wide',),
                'description': _(
                    'Limits can be placed to keep large diffs or large files '
                    'from impacting performance.'
                ),
                'fields': (
                    'diffviewer_max_diff_size',
                    'diffviewer_syntax_highlighting_threshold',
                ),
            },
            {
                'title': _('Code Safety'),
                'description': _(
                    'Review Board by default checks code for suspicious '
                    'Unicode characters used in '
                    '<a href="https://trojansource.codes/">Trojan Source</a> '
                    'attacks. These checks can be fine-tunes to avoid '
                    'matching characters in some languages, at the expense '
                    'of decreased code safety.'
                ),
                'classes': ('wide',),
                'fields': (
                    'trojan_source_check_confusables',
                    'trojan_source_confusable_aliases_allowed',
                ),
            },
            {
                'title': _('Advanced'),
                'description': _(
                    'These are advanced settings that control the behavior '
                    'and display of the diff viewer. In general, these '
                    'settings do not need to be changed.'
                ),
                'classes': ('wide',),
                'fields': (
                    'include_space_patterns',
                    'diffviewer_context_num_lines',
                    'diffviewer_paginate_by',
                    'diffviewer_paginate_orphans',
                )
            }
        )
