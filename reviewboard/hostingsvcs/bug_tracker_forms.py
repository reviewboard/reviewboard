"""Forms for configuring bug trackers.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext_lazy as _
from djblets.conditions import ConditionSet
from djblets.forms.fields import ConditionsField

from reviewboard.accounts.conditions import user_condition_choices
from reviewboard.admin.form_widgets import RelatedRepositoryWidget
from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    HostingServiceAccount,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import LocalSiteAwareModelFormMixin

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from reviewboard.hostingsvcs.base.forms import (
        BaseBugTrackerConfigForm,
    )
    from reviewboard.hostingsvcs.base.hosting_service import (
        BaseHostingService,
    )


def is_bug_tracker_configurable(
    service_cls: type[BaseHostingService],
) -> bool:
    """Return whether a service supports standalone bug tracker configs.

    In-repo bug trackers are configured through the repository, not
    through standalone configurations.

    Version Added:
        9.0

    Args:
        service_cls (type):
            The hosting service class.

    Returns:
        bool:
        ``True`` if bug tracker configurations can be created for the
        service.
    """
    return bool(service_cls.supports_bug_trackers and
                not getattr(service_cls, 'bugs_in_repo', False) and
                service_cls.hosting_service_id is not None)


def get_bug_tracker_service_choices() -> Sequence[tuple[str, str]]:
    """Return the service choices for bug tracker configuration.

    This includes all registered hosting services that are visible and
    that provide bug tracker support outside of a repository.

    Version Added:
        9.0

    Returns:
        list of tuple:
        The service choices, as (ID, name) pairs.
    """
    choices: list[tuple[str, str]] = []

    for service_cls in hosting_service_registry:
        if (service_cls.visible and
            is_bug_tracker_configurable(service_cls)):
            assert service_cls.hosting_service_id is not None

            choices.append((service_cls.hosting_service_id,
                            str(service_cls.name)))

    choices.sort(key=lambda choice: choice[1].lower())

    return choices


class HostingServiceAccountSelect(forms.Select):
    """A select widget tagging each account with its hosting service.

    The rendered options carry a ``data-service`` attribute, so the form's
    JavaScript can limit the accounts to the selected service.

    Version Added:
        9.0
    """

    def create_option(
        self,
        name: str,
        value: Any,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Return an option to render.

        Args:
            name (str):
                The name of the field.

            value (object):
                The value for the option. For accounts, this wraps the
                account instance.

            *args (tuple):
                Positional arguments for the parent method.

            **kwargs (dict):
                Keyword arguments for the parent method.

        Returns:
            dict:
            The option state to render.
        """
        option = super().create_option(name, value, *args, **kwargs)
        account = getattr(value, 'instance', None)

        if account is not None:
            option['attrs']['data-service'] = account.service_name

        return option


class BugTrackerForm(LocalSiteAwareModelFormMixin, forms.ModelForm):
    """A form for creating and updating bug tracker configurations.

    Service-specific settings are edited through the service's own bug
    tracker configuration form, and stored unprefixed in the
    configuration's settings.

    A subform is built for every service the form offers, since the
    service is chosen on the form. Only the selected service's subform is
    validated and saved. The others are rendered so the page can swap
    between them without a round trip.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The settings subforms, keyed by hosting service ID.
    #:
    #: Services without a configuration form are not included.
    settings_forms: dict[str, BaseBugTrackerConfigForm]

    service_name = forms.ChoiceField(
        label=_('Service'),
        choices=get_bug_tracker_service_choices,
    )

    hosting_account = forms.ModelChoiceField(
        label=_('Account'),
        required=False,
        queryset=HostingServiceAccount.objects.order_by('username'),
        widget=HostingServiceAccountSelect(),
        help_text=_(
            'The account used to talk to the bug tracker, for services that '
            'require one.'
        ),
    )

    repositories = forms.ModelMultipleChoiceField(
        label=_('Repositories'),
        required=False,
        queryset=Repository.objects.filter(visible=True).order_by('name'),
        widget=RelatedRepositoryWidget())

    accessible_to_everyone = forms.BooleanField(
        label=_('Accessible to everyone'),
        required=False,
        initial=True,
        help_text=_(
            'Uncheck this to limit the bug tracker to certain users.'
        ),
    )

    user_conditions = ConditionsField(
        choices=user_condition_choices,
        label=_('Users who have access'),
        required=False,
        help_text=_(
            'Conditions the user must match to interact with this bug '
            'tracker. Users failing the conditions see bare bug IDs only.'
        ),
    )

    display_mode = forms.ChoiceField(
        label=_('Display mode'),
        required=False,
        choices=ConfiguredBugTracker.DISPLAY_MODE_CHOICES,
        initial=ConfiguredBugTracker.DISPLAY_MODE_COMPACT,
        widget=forms.widgets.RadioSelect(),
        help_text=_(
            'How bugs on this tracker are shown on review requests.'
        ),
    )

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments for the parent form.

            **kwargs (dict):
                Keyword arguments for the parent form.
        """
        super().__init__(*args, **kwargs)

        # Rows created outside the form store empty user conditions as an
        # empty dict. Normalize the initial value to an empty serialized
        # condition set so the conditions widget can render it.
        initial_conditions = self.initial.get('user_conditions')

        if (not initial_conditions or
            'conditions' not in initial_conditions):
            self.initial['user_conditions'] = \
                ConditionSet(ConditionSet.MODE_ALL, []).serialize()

        # Access is limited by the presence of conditions, rather than by
        # a field of its own.
        self.initial['accessible_to_everyone'] = \
            not (initial_conditions or {}).get('conditions')

        # The display mode lives in the settings, rather than in a field
        # of its own.
        self.initial['display_mode'] = self.instance.display_mode

        # The settings are edited through each service's own form, so the
        # raw field has no place on this form. It is absent entirely when
        # the caller limits the form's fields, such as the administration
        # UI building a form from its fieldsets.
        self.fields.pop('settings', None)

        self.settings_forms = self._build_settings_forms()

    def _build_settings_forms(
        self,
    ) -> dict[str, BaseBugTrackerConfigForm]:
        """Return a settings subform for each service the form offers.

        The subform for the configuration's own service is populated with
        the stored settings. Bound forms bind every subform, so that the
        selected service's subform can be validated in
        :py:meth:`_clean_service_settings`.

        Version Added:
            9.0

        Returns:
            dict:
            The settings subforms, keyed by hosting service ID.
        """
        instance = self.instance
        instance_settings = instance.settings or None
        instance_service_name = instance.service_name

        if self.is_bound:
            data = self.data
        else:
            data = None

        settings_forms: dict[str, BaseBugTrackerConfigForm] = {}

        for service_id, _name in get_bug_tracker_service_choices():
            service_cls = \
                hosting_service_registry.get_hosting_service(service_id)

            if service_cls is None:
                continue

            form_cls = service_cls.bug_tracker_config_form

            if form_cls is None:
                continue

            if service_id == instance_service_name:
                initial = instance_settings
            else:
                initial = None

            settings_forms[service_id] = form_cls(
                data=data,
                initial=initial,
                hosting_service_cls=service_cls)

        return settings_forms

    @property
    def settings_fieldsets(
        self,
    ) -> Sequence[tuple[str, str, BaseBugTrackerConfigForm]]:
        """The settings subforms to render, as fieldsets.

        Each service's settings are shown in a fieldset of its own, so that
        they read as settings for that service rather than as more fields on
        the configuration.

        Each entry is the hosting service ID, the fieldset's name, and the
        settings subform.

        Version Added:
            9.0

        Type:
            list of tuple
        """
        fieldsets: list[tuple[str, str, BaseBugTrackerConfigForm]] = []

        for service_id, settings_form in self.settings_forms.items():
            service_cls = \
                hosting_service_registry.get_hosting_service(service_id)
            assert service_cls is not None

            fieldsets.append((
                service_id,
                _('%(service)s Settings') % {'service': service_cls.name},
                settings_form,
            ))

        return fieldsets

    @property
    def settings_form(self) -> BaseBugTrackerConfigForm | None:
        """The settings subform for the selected service.

        This is ``None`` when no valid service is selected, or when the
        service has no configuration form.

        Type:
            reviewboard.hostingsvcs.base.forms.
            BaseBugTrackerConfigForm
        """
        if self.is_bound:
            service_name = self.data.get(self.add_prefix('service_name'))
        else:
            service_name = (self.instance.service_name or
                            self.get_initial_for_field(
                                self.fields['service_name'], 'service_name'))

        if not service_name:
            return None

        return self.settings_forms.get(service_name)

    def clean(self) -> dict[str, Any]:
        """Clean the form fields.

        This validates the repository scoping, the account's service, and
        the service-specific settings.

        Returns:
            dict:
            The cleaned form data.
        """
        cleaned_data = super().clean() or self.cleaned_data

        if cleaned_data.get('apply_to') != \
           ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS:
            cleaned_data['repositories'] = Repository.objects.none()

        if cleaned_data.get('accessible_to_everyone'):
            # The conditions are hidden in this state, but still submitted.
            # Drop them, along with any errors they produced, so that a
            # hidden field can't block the save.
            self.errors.pop('user_conditions', None)
            cleaned_data['user_conditions'] = \
                ConditionSet(ConditionSet.MODE_ALL, []).serialize()

        service_name = cleaned_data.get('service_name')
        service_cls = None

        if service_name:
            service_cls = \
                hosting_service_registry.get_hosting_service(service_name)

            if (service_cls is None or
                service_name == SENTINEL_BUG_TRACKER_SERVICE_NAME):
                self.add_error('service_name',
                               _('This is not a valid service.'))
                service_cls = None

        hosting_account = cleaned_data.get('hosting_account')

        if (service_cls is not None and
            hosting_account is not None and
            hosting_account.service_name != service_name):
            self.add_error(
                'hosting_account',
                _('This account is not on the selected service.'))

        if service_cls is not None:
            self._clean_service_settings(cleaned_data, service_cls)

        # The display mode is stored alongside the service's settings.
        if (settings := cleaned_data.get('settings')) is not None:
            settings[ConfiguredBugTracker.DISPLAY_MODE_KEY] = (
                cleaned_data.get('display_mode') or
                ConfiguredBugTracker.DISPLAY_MODE_COMPACT)

        # This runs after the settings are cleaned, so services can exempt
        # configurations based on their settings (such as migrated legacy
        # configurations carrying their own server).
        if (service_cls is not None and
            hosting_account is None and
            'hosting_account' not in self.errors and
            service_cls.is_bug_tracker_account_required(
                cleaned_data.get('settings') or {})):
            self.add_error(
                'hosting_account',
                _('This service requires a linked account.'))

        return cleaned_data

    def _clean_service_settings(
        self,
        cleaned_data: dict[str, Any],
        service_cls: type[BaseHostingService],
    ) -> None:
        """Validate the settings through the service's settings subform.

        Values from the subform are merged over the configuration's
        existing settings, preserving keys the form does not manage.

        Field errors are left on the subform, so that they render beside
        the fields that produced them. A general error is also added to
        this form, so that it reports itself as invalid and the admin
        shows its error banner.

        Args:
            cleaned_data (dict):
                The cleaned form data. The merged settings are written
                back to its ``settings`` key.

            service_cls (type):
                The hosting service class.
        """
        settings = dict(self.instance.settings or {})
        settings_form = self.settings_forms.get(
            service_cls.hosting_service_id or '')

        if settings_form is not None:
            if settings_form.is_valid():
                settings.update(settings_form.cleaned_data)
            else:
                self.add_error(
                    None,
                    _(
                        'Please correct the errors in the {service} settings '
                        'below.'
                    ).format(service=service_cls.name))

        cleaned_data['settings'] = settings

    def save(
        self,
        commit: bool = True,
    ) -> ConfiguredBugTracker:
        """Save the bug tracker configuration.

        The merged settings are applied to the instance, since the raw
        ``settings`` form field is not present.

        Args:
            commit (bool, optional):
                Whether to save the instance to the database.

        Returns:
            reviewboard.hostingsvcs.models.ConfiguredBugTracker:
            The saved bug tracker configuration.
        """
        self.instance.settings = self.cleaned_data.get('settings') or {}

        return super().save(commit=commit)

    class Meta:
        """Metadata for the form."""

        model = ConfiguredBugTracker
        error_messages = {
            'repositories': {
                'invalid_pk_value': _('%(pk)s is not a valid repository ID'),
            },
        }
        fields = '__all__'
        widgets = {
            'apply_to': forms.widgets.RadioSelect(),
        }
