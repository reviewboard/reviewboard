from __future__ import unicode_literals

from django import forms
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer.models import DiffSet


class NoBaseDirError(ValueError):
    pass


class UploadDiffForm(forms.Form):
    basedir = forms.CharField(
        label=_("Base Directory"),
        help_text=_("The absolute path in the repository the diff was "
                    "generated in."))
    path = forms.FileField(
        label=_("Diff"),
        help_text=_("The new diff to upload."))
    parent_diff_path = forms.FileField(
        label=_("Parent Diff"),
        help_text=_("An optional diff that the main diff is based on. "
                    "This is usually used for distributed revision control "
                    "systems (Git, Mercurial, etc.)."),
        required=False)

    base_commit_id = forms.CharField(
        label=_('Base Commit ID'),
        help_text=_('The ID/revision this change is built upon.'),
        required=False)

    def __init__(self, repository, data=None, files=None, request=None,
                 *args, **kwargs):
        super(UploadDiffForm, self).__init__(data=data, files=files,
                                             *args, **kwargs)
        self.repository = repository
        self.request = request

        if self.repository.get_scmtool().diffs_use_absolute_paths:
            # This SCMTool uses absolute paths, so there's no need to ask
            # the user for the base directory.
            del(self.fields['basedir'])

    def clean_base_commit_id(self):
        return self.cleaned_data['base_commit_id'].strip() or None

    def create(self, diff_file, parent_diff_file=None, diffset_history=None):
        tool = self.repository.get_scmtool()

        # Grab the base directory if there is one.
        if not tool.diffs_use_absolute_paths:
            try:
                basedir = smart_unicode(self.cleaned_data['basedir'].strip())
            except AttributeError:
                raise NoBaseDirError(
                    _('The "Base Diff Path" field is required'))
        else:
            basedir = ''

        return DiffSet.objects.create_from_upload(
            repository=self.repository,
            diff_file=diff_file,
            parent_diff_file=parent_diff_file,
            diffset_history=diffset_history,
            basedir=basedir,
            base_commit_id=self.cleaned_data['base_commit_id'],
            request=self.request)
