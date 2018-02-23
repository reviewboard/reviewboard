"""Forms for uploading diffs."""

from __future__ import unicode_literals

from django import forms
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer.models import DiffSet


class UploadDiffForm(forms.Form):
    """The form for uploading a diff and creating a DiffSet."""

    basedir = forms.CharField(
        label=_('Base Directory'),
        help_text=_('The absolute path in the repository the diff was '
                    'generated in.'))
    path = forms.FileField(
        label=_('Diff'),
        help_text=_('The new diff to upload.'))
    parent_diff_path = forms.FileField(
        label=_('Parent Diff'),
        help_text=_('An optional diff that the main diff is based on. '
                    'This is usually used for distributed revision control '
                    'systems (Git, Mercurial, etc.).'),
        required=False)

    base_commit_id = forms.CharField(
        label=_('Base Commit ID'),
        help_text=_('The ID/revision this change is built upon.'),
        required=False)

    def __init__(self, repository, request=None, *args, **kwargs):
        """Initialize the form.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the DiffSet is to be created against.

            request (django.http.HttpRequest):
                The current HTTP request.

            *args (tuple):
                Additional positional arguments.

            **kwrgs (dict):
                Additional keyword arguments.
        """
        super(UploadDiffForm, self).__init__(*args, **kwargs)
        self.repository = repository
        self.request = request

        if self.repository.get_scmtool().diffs_use_absolute_paths:
            # This SCMTool uses absolute paths, so there's no need to ask
            # the user for the base directory.
            del(self.fields['basedir'])

    def clean_base_commit_id(self):
        """Clean the ``base_commit_id`` field.

        Returns:
            unicode:
            The ``base_commit_id`` field stripped of leading and trailing
            whitespace, or ``None`` if that value would be empty.
        """
        return self.cleaned_data['base_commit_id'].strip() or None

    def clean_basedir(self):
        """Clean the ``basedir`` field.

        Returns:
            unicode:
            The basedir field as a unicode string with leading and trailing
            whitespace removed.
        """
        if self.repository.get_scmtool().diffs_use_absolute_paths:
            return ''

        return smart_unicode(self.cleaned_data['basedir'].strip())

    def create(self, diffset_history=None):
        """Create the DiffSet.

        Args:
            diffset_history (reviewboard.diffviewer.models.DiffSetHistory):
                The DiffSet history to attach the created DiffSet to.

        Returns:
            reviewboard.diffviewer.models.DiffSet:
            The created DiffSet.
        """
        assert self.is_valid()

        return DiffSet.objects.create_from_upload(
            repository=self.repository,
            diff_file=self.cleaned_data['path'],
            parent_diff_file=self.cleaned_data.get('parent_diff_path'),
            diffset_history=diffset_history,
            basedir=self.cleaned_data.get('basedir', ''),
            base_commit_id=self.cleaned_data['base_commit_id'],
            request=self.request)
