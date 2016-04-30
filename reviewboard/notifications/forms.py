from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext as _

from reviewboard.notifications.models import WebHookTarget
from reviewboard.scmtools.models import Repository


class WebHookTargetForm(forms.ModelForm):
    """A form for creating and updating WebHookTargets."""

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
        else:
            queryset = self.cleaned_data['repositories']
            local_site = self.cleaned_data.get('local_site')
            errors = []

            for repository in queryset:
                if repository.local_site != local_site:
                    errors.append(
                        _('Repository with ID %(id)s is invalid.')
                        % {'id': repository.pk})

            if errors:
                del self.cleaned_data['repositories']
                self._errors['repositories'] = self.error_class(errors)

        return self.cleaned_data

    class Meta:
        model = WebHookTarget
        widgets = {
            'url': forms.widgets.TextInput(attrs={'size': 100}),
            'apply_to': forms.widgets.RadioSelect(),
        }
        error_messages = {
            'repositories': {
                'invalid_choice': _('No such repository with ID %(value)s.'),
                'invalid_pk_value': _('"%(pk)s" is an invalid repository ID.'),
            },
        }
