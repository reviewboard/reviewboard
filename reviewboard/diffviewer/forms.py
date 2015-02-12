from __future__ import unicode_literals

import dateutil.parser
from django import forms
from django.core.validators import ValidationError
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer.models import DiffCommit, DiffSet


class NoBaseDirError(ValueError):
    pass


class EmptyDiffForm(forms.Form):
    """A form for creating empty DiffSets."""
    basedir = forms.CharField(
        label=_('Base directory'),
        help_text=_('The absolute path in the repository the diff was '
                    'generated in.'))

    def __init__(self, repository, data=None, files=None, request=None,
                 *args, **kwargs):
        super(EmptyDiffForm, self).__init__(data, files, *args, **kwargs)

        self.repository = repository
        self.request = request

        if self.repository.get_scmtool().get_diffs_use_absolute_paths():
            # This SCMTool uses absolute paths, so there's no need to ask
            # the user for the base directory.
            del(self.fields['basedir'])

    def _get_basedir(self):
        if not self.repository.get_scmtool().get_diffs_use_absolute_paths():
            try:
                basedir = smart_unicode(self.cleaned_data['basedir']).strip()
            except AttributeError:
                raise NoBaseDirError(
                    _('The "Base Diff Path" field is required'))
        else:
            basedir = ''

        return basedir

    def create(self, **kwargs):
        return DiffSet.objects.create_empty(repository=self.repository,
                                            request=self.request,
                                            basedir=self._get_basedir(),
                                            **kwargs)


class UploadDiffForm(EmptyDiffForm):
    """A form for uploading diffs as DiffSets."""
    path = forms.FileField(
        label=_('Diff'),
        help_text=_('The new diff to upload.'))
    parent_diff_path = forms.FileField(
        label=_('Parent diff'),
        help_text=_('An optional diff that the main diff is based on. '
                    'This is usually used for distributed revision control '
                    'systems (Git, Mercurial, etc.).'),
        required=False)
    base_commit_id = forms.CharField(
        label=_('Base commit ID'),
        help_text=_('The ID/revision this change is built upon.'),
        required=False)

    def clean_base_commit_id(self):
        """Clean the base_commit_id.

        When a whitespace-only value is presented, return None instead.
        """
        return self.cleaned_data['base_commit_id'].strip() or None

    def create(self, diff_file, parent_diff_file=None, diffset_history=None):
        return DiffSet.objects.create_from_upload(
            repository=self.repository,
            diff_file=diff_file,
            parent_diff_file=parent_diff_file,
            diffset_history=diffset_history,
            basedir=self._get_basedir(),
            base_commit_id=self.cleaned_data['base_commit_id'],
            request=self.request)


def _validate_commit_type(commit_type):
    """Determine if the given commit type is a valid one.

    A valid commit type is either 'change' or 'merge'.
    """
    if commit_type not in ('change', 'merge'):
        raise ValidationError(_('Not a valid commit type: %s') % commit_type)


class UploadDiffCommitForm(forms.Form):
    """A form for uploading diffs as DiffCommits."""
    path = forms.FileField(
        label=_('Diff'),
        help_text=_('The new diff to upload.'))
    parent_path = forms.FileField(
        label=_('Parent diff'),
        help_text=_('An optional diff that the main diff is based on. '
                    'This is usually used for distributed revision control '
                    'systems (Git, Mercurial, etc.).'),
        required=False)

    author_name = forms.CharField(
        label=_('Commit author name'),
        help_text=_('The name of the author of this commit.'),
        max_length=DiffCommit.NAME_MAX_LENGTH)
    author_email = forms.EmailField(
        label=_('Commit author email'),
        help_text=_('The email of the author of this commit.'),
        max_length=DiffCommit.EMAIL_MAX_LENGTH)
    author_date = forms.CharField(
        help_text=_('The date and time the commit was authored.'))

    committer_name = forms.CharField(
        label=_('Committer name'),
        help_text=_('The committer of this commit.'),
        max_length=DiffCommit.NAME_MAX_LENGTH,
        required=False)
    committer_email = forms.EmailField(
        label=_('Commiter email'),
        help_text=_('The email address of the committer.'),
        max_length=DiffCommit.EMAIL_MAX_LENGTH,
        required=False)
    committer_date = forms.CharField(
        help_text=_('The date and time the commit was committed.'),
        required=False)

    description = forms.CharField(
        label=_('Description'),
        help_text=_('The description of this commit.'),
        required=False)
    commit_id = forms.CharField(
        label=_('Commit ID'),
        help_text=_('The ID/revision of this commit.'),
        max_length=DiffCommit.COMMIT_ID_LENGTH,
        validators=[DiffCommit.validate_commit_id])
    parent_id = forms.CharField(
        label=_('Parent commit ID'),
        help_text=_('The parent ID/revision of this commit.'),
        max_length=DiffCommit.COMMIT_ID_LENGTH,
        validators=[DiffCommit.validate_commit_id])
    merge_parent_ids = forms.CharField(
        label=_('Merge parent IDs'),
        help_text=_('The other merge parent of this commit.'),
        required=False)
    commit_type = forms.CharField(
        label=_('Commit type'),
        validators=[_validate_commit_type])

    def __init__(self, review_request, data=None, files=None, request=None,
                 *args, **kwargs):
        super(UploadDiffCommitForm, self).__init__(data, files, request, *args,
                                                   **kwargs)
        self.repository = review_request.repository
        self.request = request

    def clean_author_date(self):
        """Parse the date and time out of the author_date field."""
        return dateutil.parser.parse(self.cleaned_data['author_date'])

    def clean_committer_date(self):
        """Parse the date and time out of the committer_date field."""
        if not self.cleaned_data['committer_date']:
            return None

        return dateutil.parser.parse(self.cleaned_data['committer_date'])

    def clean_commit_type(self):
        """Parse the commit type as a string into a single character."""
        if self.cleaned_data['commit_type'] == 'change':
            return DiffCommit.COMMIT_CHANGE_TYPE
        elif self.cleaned_data['commit_type'] == 'merge':
            return DiffCommit.COMMIT_MERGE_TYPE

        # We shouldn't reach this code because the form should be doing its own
        # validation with the ``DiffCommit.validate_commit_id`` method.
        assert False

    def clean_merge_parent_ids(self):
        """Clean the list of merge parent IDs.

        The merge parent IDs are sent as a comma separated string of individual
        merge parents. This function splits the string into a list of strings
        and attempts to validate them according to our commit ID validator.
        """
        errors = []

        merge_parent_ids = self.cleaned_data['merge_parent_ids'].strip()

        if merge_parent_ids:
            merge_parent_ids = merge_parent_ids.split(',')

            for i, merge_parent_id in enumerate(merge_parent_ids):
                merge_parent_id = merge_parent_id.strip()

                try:
                    DiffCommit.validate_commit_id(merge_parent_id)
                    merge_parent_ids[i] = merge_parent_id
                except forms.ValidationError as e:
                    errors.append(_('Could not interpret merge parent id: %s.')
                                  % e)

            if errors:
                raise forms.ValidationError(errors)

            return merge_parent_ids

        return None

    def create(self, diffset, diff_file, parent_diff_file=None):
        return DiffCommit.objects.create_from_upload(
            repository=self.repository,
            diff_file=diff_file,
            parent_diff_file=parent_diff_file,
            request=self.request,
            diffset=diffset,
            commit_id=self.cleaned_data['commit_id'],
            parent_id=self.cleaned_data['parent_id'],
            merge_parent_ids=self.cleaned_data['merge_parent_ids'],
            author_name=self.cleaned_data['author_name'],
            author_email=self.cleaned_data['author_email'],
            author_date=self.cleaned_data['author_date'],
            committer_name=self.cleaned_data['committer_name'],
            committer_email=self.cleaned_data['committer_email'],
            committer_date=self.cleaned_data['committer_date'],
            description=self.cleaned_data['description'],
            commit_type=self.cleaned_data['commit_type'])
