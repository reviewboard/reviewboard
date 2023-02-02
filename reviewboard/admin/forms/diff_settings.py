"""Administration form for diff viewer settings."""

import re

from django import forms
from django.utils.translation import gettext_lazy as _
from djblets.forms.fields import ListEditDictionaryField
from djblets.forms.widgets import ListEditWidget
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.form_widgets import LexersMappingWidget


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

    def load(self):
        """Load settings from the form.

        This will populate initial fields based on the site configuration.
        """
        super(DiffSettingsForm, self).load()

        self.fields['include_space_patterns'].initial = \
            ', '.join(self.siteconfig.get('diffviewer_include_space_patterns'))

    def save(self):
        """Save the form.

        This will write the new configuration to the database.
        """
        self.siteconfig.set(
            'diffviewer_include_space_patterns',
            re.split(r',\s*', self.cleaned_data['include_space_patterns']))

        super(DiffSettingsForm, self).save()

    class Meta:
        title = _('Diff Viewer Settings')
        save_blacklist = ('include_space_patterns',)
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
