"""Administration form for SSH settings."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import (ugettext,
                                      ugettext_lazy as _)

from reviewboard.ssh.client import SSHClient


class SSHSettingsForm(forms.Form):
    """SSH key settings for Review Board."""

    generate_key = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput)
    keyfile = forms.FileField(
        label=_('Key file'),
        required=False,
        widget=forms.FileInput(attrs={'size': '35'}))
    delete_key = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.HiddenInput)

    def create(self, files):
        """Generate or import an SSH key.

        This will generate a new SSH key if :py:attr:`generate_key` was set
        to ``True``. Otherwise, a if :py:attr:`keyfile` was provided, its
        corresponding file upload will be used as the new key.

        In either case, the key will be validated, and if validation fails,
        an error will be set for the appropriate field.

        Args:
            files (django.utils.datastructures.MultiValueDict):
                The files uploaded in the request. This may contain a
                ``keyfile`` entry representing a key to upload.

        Raises:
            Exception:
                There was an error generating or importing a key. The form
                will have a suitable error for the field triggering the
                error.
        """
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
        """Return whether the user has requested to delete the user SSH key.

        This checks that :py:attr:`delete_key`` was set in the request.

        Returns:
            ``True`` if the user requested to delete the key. ``False`` if
            they did not.
        """
        return self.cleaned_data.get('delete_key', False)

    def delete(self):
        """Delete the configured SSH user key.

        This will only delete the key if :py:attr:`delete_key` was set.

        Raises:
            Exception:
                There was an unexpected error deleting the key. A validation
                error will be set for the ``delete_key`` field.
        """
        if self.did_request_delete():
            try:
                SSHClient().delete_user_key()
            except Exception as e:
                self.errors['delete_key'] = forms.util.ErrorList([
                    ugettext('Unable to delete SSH key file: %s') % e
                ])
                raise

    class Meta:
        title = _('SSH Settings')
