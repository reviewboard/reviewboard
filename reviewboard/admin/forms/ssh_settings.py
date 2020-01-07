"""Administration form for SSH settings."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import (ugettext,
                                      ugettext_lazy as _)

from reviewboard.ssh.client import SSHClient


class SSHSettingsForm(forms.Form):
    """SSH key settings for Review Board."""

    generate_key = forms.BooleanField(required=False,
                                      initial=True,
                                      widget=forms.HiddenInput)
    keyfile = forms.FileField(label=_('Key file'),
                              required=False,
                              widget=forms.FileInput(attrs={'size': '35'}))
    delete_key = forms.BooleanField(required=False,
                                    initial=True,
                                    widget=forms.HiddenInput)

    def create(self, files):
        """Generate or import an SSH key."""
        if self.cleaned_data['generate_key']:
            try:
                SSHClient().generate_user_key()
            except IOError as e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    ugettext('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception as e:
                self.errors['generate_key'] = forms.util.ErrorList([
                    ugettext('Error generating SSH key: %s') % e
                ])
                raise
        elif self.cleaned_data['keyfile']:
            try:
                SSHClient().import_user_key(files['keyfile'])
            except IOError as e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    ugettext('Unable to write SSH key file: %s') % e
                ])
                raise
            except Exception as e:
                self.errors['keyfile'] = forms.util.ErrorList([
                    ugettext('Error uploading SSH key: %s') % e
                ])
                raise

    def did_request_delete(self):
        """Return whether the user has requested to delete the user SSH key."""
        return 'delete_key' in self.cleaned_data

    def delete(self):
        """Try to delete the user SSH key upon request."""
        if self.cleaned_data['delete_key']:
            try:
                SSHClient().delete_user_key()
            except Exception as e:
                self.errors['delete_key'] = forms.util.ErrorList([
                    ugettext('Unable to delete SSH key file: %s') % e
                ])
                raise

    class Meta:
        title = _('SSH Settings')
