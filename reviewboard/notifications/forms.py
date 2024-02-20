"""Notification-related forms."""

from __future__ import annotations

from typing import Any, Optional

from django import forms
from django.core.validators import URLValidator
from django.forms.fields import CharField, MultipleChoiceField
from django.utils.translation import gettext_lazy as _

from reviewboard.admin.form_widgets import RelatedRepositoryWidget
from reviewboard.notifications.models import WebHookTarget
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin


class WebHookTargetForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
    """A form for creating and updating WebHookTargets."""

    url = CharField(
        label=_('URL'),
        validators=[URLValidator()],
        widget=forms.widgets.URLInput(attrs={'size': 100}),
    )

    events = MultipleChoiceField(
        choices=WebHookTarget.EVENT_CHOICES,
        required=False,
        widget=forms.widgets.CheckboxSelectMultiple)

    repositories = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        widget=RelatedRepositoryWidget())

    def clean_extra_data(self) -> Optional[str]:
        """Ensure that extra_data is a valid value.

        Returns:
            str:
            Either a non-zero length string of JSON-encoded extra data or None.
        """
        return self.cleaned_data['extra_data'] or None

    def clean_events(self) -> list[str]:
        """Clean the "events" field.

        Returns:
            list of str:
            The cleaned events field data.
        """
        events = self.cleaned_data['events']

        if '*' in events:
            events = ['*']

        return events

    def clean(self) -> dict[str, Any]:
        """Validate the state of the entire form.

        Returns:
            The cleaned form data.
        """
        super().clean()

        custom_content = self.cleaned_data.get('custom_content', '')
        self.cleaned_data['use_custom_content'] = len(custom_content) > 0

        apply_to = self.cleaned_data.get('apply_to')

        if (apply_to != WebHookTarget.APPLY_TO_SELECTED_REPOS or
            'repositories' not in self.cleaned_data):
            self.cleaned_data['repositories'] = Repository.objects.none()

        return self.cleaned_data

    class Meta:
        """Metadata for the WebHookTarget form."""

        model = WebHookTarget
        widgets = {
            'apply_to': forms.widgets.RadioSelect(),
        }
        error_messages = {
            'repositories': {
                'invalid_choice': _('A repository with ID %(value)s was not '
                                    'found.'),
                'invalid_pk_value': _('"%(pk)s" is an invalid repository ID.'),
            },
        }
        fields = '__all__'
