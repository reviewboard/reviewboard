from __future__ import unicode_literals

import re

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext, ugettext_lazy as _

from reviewboard.admin.form_widgets import RelatedUserWidget
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

    people = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        label=_('Default users'),
        required=False,
        widget=RelatedUserWidget())

    repository = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        help_text=_('The list of repositories to specifically match this '
                    'default reviewer for. If left empty, this will match '
                    'all repositories.'),
        widget=FilteredSelectMultiple(_("Repositories"), False))

    def __init__(self, *args, **kwargs):
        local_site_name = kwargs.pop('local_site_name', None)
        local_site = kwargs.pop('local_site', None)

        super(DefaultReviewerForm, self).__init__(*args, **kwargs)

        if local_site:
            local_site_name = local_site.name

        self.fields['people'].widget.local_site_name = local_site_name

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

        return super(DefaultReviewerForm, self).clean()

    class Meta:
        model = DefaultReviewer
        fields = '__all__'


class GroupForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_('Users'),
        required=False,
        widget=RelatedUserWidget())

    def __init__(self, *args, **kwargs):
        local_site_name = kwargs.pop('local_site_name', None)

        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['users'].widget.local_site_name = local_site_name

    def clean(self):
        validate_users(self)

        return super(GroupForm, self).clean()


    class Meta:
        model = Group
        fields = '__all__'


class UploadDiffForm(diffviewer_forms.UploadDiffForm):
    """A specialized UploadDiffForm for interacting with review requests."""

    def __init__(self, review_request, request=None, *args, **kwargs):
        """Initialize the form.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request that the uploaded diff will be attached to.

            request (django.http.HttpRequest):
                The current HTTP request.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """
        super(UploadDiffForm, self).__init__(review_request.repository,
                                             request,
                                             *args,
                                             **kwargs)
        self.review_request = review_request

        if ('basedir' in self.fields and
            (not self.data or 'basedir' not in self.data)):
            try:
                diffset = DiffSet.objects.filter(
                    history=review_request.diffset_history_id).latest()
                self.fields['basedir'].initial = diffset.basedir
            except DiffSet.DoesNotExist:
                pass

    def clean(self):
        """Clean the form.

        This ensures that the associated review request was not created with
        history.

        Returns:
            dict:
            The cleaned form data.

        Raises:
            django.core.exceptions.ValidationError:
                The form cannot be validated.
        """
        super(UploadDiffForm, self).clean()

        if self.review_request.created_with_history:
            raise ValidationError(ugettext(
                'The review request was created with history support and '
                'DiffSets cannot be attached in this way. Instead, attach '
                'DiffCommits.'))

        return self.cleaned_data

    def create(self, attach_to_history=False):
        """Create the DiffSet and optionally attach it to the history.

        Args:
            attach_to_history (bool):
                Whether or not the created
                :py:class:`~reviewboard.diffviewer.models.diffset.DiffSet` will
                be attached to the diffset history of the
                :py:class:`reviewboard.reviews.models.review_request.
                ReviewRequest`.

                Defaults to ``False``.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
            The created DiffSet.
        """
        assert self.is_valid()
        history = None

        if attach_to_history:
            history = self.review_request.diffset_history

        diffset = super(UploadDiffForm, self).create(history)

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
