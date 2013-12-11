from __future__ import unicode_literals

import re

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from reviewboard.diffviewer import forms as diffviewer_forms
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (DefaultReviewer, Group,
                                        ReviewRequestDraft, Screenshot)
from reviewboard.scmtools.models import Repository
from reviewboard.site.validation import validate_review_groups, validate_users


def regex_validator(value):
    """Validates that the specified regular expression is valid."""
    try:
        re.compile(value)
    except Exception as e:
        raise ValidationError(e)


class DefaultReviewerForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Name"),
        max_length=64,
        widget=forms.TextInput(attrs={'size': '30'}))

    file_regex = forms.CharField(
        label=_("File regular expression"),
        max_length=256,
        widget=forms.TextInput(attrs={'size': '60'}),
        validators=[regex_validator],
        help_text=_('File paths are matched against this regular expression '
                    'to determine if these reviewers should be added.'))

    repository = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        help_text=_('The list of repositories to specifically match this '
                    'default reviewer for. If left empty, this will match '
                    'all repositories.'),
        widget=FilteredSelectMultiple(_("Repositories"), False))

    def clean(self):
        try:
            validate_users(self, 'people')
        except ValidationError as e:
            self._errors['people'] = self.error_class(e.messages)

        try:
            validate_review_groups(self, 'groups')
        except ValidationError as e:
            self._errors['groups'] = self.error_class(e.messages)

        # Now make sure the repositories are valid.
        local_site = self.cleaned_data['local_site']
        repositories = self.cleaned_data['repository']

        for repository in repositories:
            if repository.local_site != local_site:
                self._errors['repository'] = self.error_class([
                    _("The repository '%s' doesn't exist on the local site.")
                    % repository.name,
                ])
                break

        return self.cleaned_data

    class Meta:
        model = DefaultReviewer


class GroupForm(forms.ModelForm):
    def clean(self):
        validate_users(self)

        return self.cleaned_data

    class Meta:
        model = Group


class UploadDiffForm(diffviewer_forms.UploadDiffForm):
    """
    A specialized UploadDiffForm that knows how to interact with review
    requests.
    """
    def __init__(self, review_request, data=None, *args, **kwargs):
        super(UploadDiffForm, self).__init__(review_request.repository,
                                             data, *args, **kwargs)
        self.review_request = review_request

        if ('basedir' in self.fields and
            (not data or 'basedir' not in data)):
            try:
                diffset = DiffSet.objects.filter(
                    history=review_request.diffset_history_id).latest()
                self.fields['basedir'].initial = diffset.basedir
            except DiffSet.DoesNotExist:
                pass

    def create(self, diff_file, parent_diff_file=None,
               attach_to_history=False):
        history = None

        if attach_to_history:
            history = self.review_request.diffset_history

        diffset = super(UploadDiffForm, self).create(diff_file,
                                                     parent_diff_file,
                                                     history)

        if not attach_to_history:
            # Set the initial revision to be one newer than the most recent
            # public revision, so we can reference it in the diff viewer.
            #
            # TODO: It would be nice to later consolidate this with the logic
            #       in DiffSet.save.
            public_diffsets = self.review_request.diffset_history.diffsets

            try:
                latest_diffset = public_diffsets.latest()
                diffset.revision = latest_diffset.revision + 1
            except DiffSet.DoesNotExist:
                diffset.revision = 1

            diffset.save()

        return diffset


class UploadScreenshotForm(forms.Form):
    """
    A form that handles uploading of new screenshots.
    A screenshot takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.ImageField(required=True)

    def create(self, file, review_request):
        screenshot = Screenshot(caption='',
                                draft_caption=self.cleaned_data['caption'])
        screenshot.image.save(file.name, file, save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.screenshots.add(screenshot)
        draft.save()

        return screenshot
