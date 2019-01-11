from __future__ import unicode_literals

import re

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from reviewboard.admin.form_widgets import RelatedUserWidget
from reviewboard.diffviewer import forms as diffviewer_forms
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (DefaultReviewer, Group,
                                        ReviewRequestDraft, Screenshot)
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin


def regex_validator(value):
    """Validates that the specified regular expression is valid."""
    try:
        re.compile(value)
    except Exception as e:
        raise ValidationError(e)


class DefaultReviewerForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
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

    people = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('Default users'),
        required=False,
        widget=RelatedUserWidget(),
        error_messages={
            'invalid_choice': _('A user with ID %(value)s was not found.'),
            'invalid_pk_value': _('"%(pk)s" is an invalid user ID.'),
        })

    repository = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        help_text=_('The list of repositories to specifically match this '
                    'default reviewer for. If left empty, this will match '
                    'all repositories.'),
        widget=FilteredSelectMultiple(_("Repositories"), False),
        error_messages={
            'invalid_choice': _('A repository with ID %(value)s was not '
                                'found.'),
            'invalid_pk_value': _('"%(pk)s" is an invalid repository ID.'),
        })

    class Meta:
        model = DefaultReviewer
        error_messages = {
            'groups': {
                'invalid_choice': _('A group with ID %(value)s was not '
                                    'found.'),
                'invalid_pk_value': _('"%(pk)s" is an invalid group ID.'),
            },
        }
        fields = '__all__'


class GroupForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_('Users'),
        required=False,
        widget=RelatedUserWidget(),
        error_messages={
            'invalid_choice': _('A user with ID %(value)s was not found.'),
            'invalid_pk_value': _('"%(pk)s" is an invalid user ID.'),
        })

    class Meta:
        model = Group
        fields = '__all__'


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
            diffset.update_revision_from_history(
                self.review_request.diffset_history)
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
