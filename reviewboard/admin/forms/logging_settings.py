"""Administration form for logging settings."""

from __future__ import unicode_literals

import os

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import (ugettext,
                                      ugettext_lazy as _)
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.siteconfig import load_site_config


class LoggingSettingsForm(SiteSettingsForm):
    """Logging settings for Review Board."""

    LOG_LEVELS = (
        ('DEBUG', _('Debug')),
        ('INFO', _('Info')),
        ('WARNING', _('Warning')),
        ('ERROR', _('Error')),
        ('CRITICAL', _('Critical')),
    )

    logging_enabled = forms.BooleanField(
        label=_('Enable logging'),
        help_text=_("Enables logging of Review Board operations. This is in "
                    "addition to your web server's logging and does not log "
                    "all page visits."),
        required=False)

    logging_directory = forms.CharField(
        label=_('Log directory'),
        help_text=_('The directory where log files will be stored. This must '
                    'be writable by the web server.'),
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}))

    logging_level = forms.ChoiceField(
        label=_('Log level'),
        help_text=_('Indicates the logging threshold. Please note that this '
                    'may increase the size of the log files if a low '
                    'threshold is selected.'),
        required=False,
        choices=LOG_LEVELS)

    logging_allow_profiling = forms.BooleanField(
        label=_('Allow code profiling'),
        help_text=_('Logs the time spent on certain operations. This is '
                    'useful for debugging but may greatly increase the '
                    'size of log files.'),
        required=False)

    def clean_logging_directory(self):
        """Validate that the logging_directory path is valid.

        This checks that the directory path exists, and is writable by the web
        server. If valid, the directory with whitespace stripped will be
        returned.

        Returns:
            unicode:
            The logging directory, with whitespace stripped.

        Raises:
            django.core.exceptions.ValidationError:
                The directory was not valid.
        """
        logging_dir = self.cleaned_data['logging_directory'].strip()

        if not os.path.exists(logging_dir):
            raise ValidationError(ugettext('This path does not exist.'))

        if not os.path.isdir(logging_dir):
            raise ValidationError(ugettext('This is not a directory.'))

        if not os.access(logging_dir, os.W_OK):
            raise ValidationError(
                ugettext('This path is not writable by the web server.'))

        return logging_dir

    def save(self):
        """Save the form.

        This will write the new configuration to the database. It will then
        force a site configuration reload.
        """
        super(LoggingSettingsForm, self).save()

        # Reload any important changes into the Django settings.
        load_site_config()

    class Meta:
        title = _('Logging Settings')
        fieldsets = (
            {
                'classes': ('wide',),
                'fields': ('logging_enabled',
                           'logging_directory',
                           'logging_level'),
            },
            {
                'title': _('Advanced'),
                'classes': ('wide',),
                'fields': ('logging_allow_profiling',),
            }
        )
