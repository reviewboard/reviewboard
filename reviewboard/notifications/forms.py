"""Notification-related forms."""

from __future__ import unicode_literals

from django import forms
from django.forms.fields import CharField
from django.utils.translation import ugettext_lazy as _, ugettext
from djblets.util.compat.django.core.validators import URLValidator

from reviewboard.admin.form_widgets import RelatedRepositoryWidget
from reviewboard.notifications.models import WebHookTarget
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin


class WebHookTargetForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
    """A form for creating and updating WebHookTargets."""

    url = CharField(
        label=_('URL'),
        validators=[URLValidator()],
        widget=forms.widgets.URLInput(attrs={'size': 100})
    )

    repositories = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        widget=RelatedRepositoryWidget())

    def clean_extra_data(self):
        """Ensure that extra_data is a valid value.

        Returns:
            unicode:
            Either a non-zero length string of JSON-encoded extra data or None.
        """
        return self.cleaned_data['extra_data'] or None

    def clean_events(self):
        events = self.cleaned_data['events']

        if '*' in events:
            events = ['*']

        return events

    def clean(self):
        """Validate the state of the entire form.

        Returns:
            The cleaned form data.
        """
        super(WebHookTargetForm, self).clean()

        custom_content = self.cleaned_data.get('custom_content', '')
        self.cleaned_data['use_custom_content'] = len(custom_content) > 0

        apply_to = self.cleaned_data.get('apply_to')

        if (apply_to != WebHookTarget.APPLY_TO_SELECTED_REPOS or
            'repositories' not in self.cleaned_data):
            self.cleaned_data['repositories'] = Repository.objects.none()

        return self.cleaned_data

    class Meta:
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
