"""Administration form for the Background Tasks settings.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.broker.registry import broker_registry

if TYPE_CHECKING:
    from djblets.siteconfig.models import SiteConfiguration
    from typelets.django.strings import StrOrPromise

    from reviewboard.broker.base.backends import BaseBrokerBackend
    from reviewboard.broker.base.forms import BaseBrokerSettingsForm


logger = logging.getLogger(__name__)


class BackgroundTasksForm(SiteSettingsForm):
    """Background Tasks settings for Review Board.

    This allows administrators to configure the broker used for background
    tasks. Review Board defaults to a local filesystem broker, but a
    dedicated broker (backed by RabbitMQ or another service) can be chosen
    for scaled-out deployments.

    Version Added:
        9.0
    """

    broker_id = forms.ChoiceField(
        label=_('Message broker'),
        choices=(),
        help_text=_(
            'The message broker used for background task processing '
            'and communication with services like Review Bot. You can '
            'choose local for a single-server deployment, and other '
            'brokers for multi-server.'
        ),
        required=True,
        widget=forms.Select(attrs={
            'data-subform-group': 'broker-backend',
        }),
    )

    ######################
    # Instance variables #
    ######################

    #: The mapping of broker IDs to settings forms for brokers.
    #:
    #: Only the form for the selected primary broker will be shown.
    #:
    #: A broker whose settings form failed to load will map to ``None``.
    #: Brokers without a settings form won't be included.
    broker_backend_forms: dict[str, BaseBrokerSettingsForm | None]

    def __init__(
        self,
        siteconfig: SiteConfiguration,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the settings form.

        This will load the list of available broker backends and their
        settings forms and prepare them as subforms.

        Args:
            siteconfig (djblets.siteconfig.models.SiteConfiguration):
                The site configuration handling the server's settings.

            *args (tuple):
                Additional positional arguments for the parent class.

            **kwargs (dict):
                Additional keyword arguments for the parent class.
        """
        super().__init__(siteconfig, *args, **kwargs)

        cur_broker_id = (
            self['broker_id'].data or
            self.fields['broker_id'].initial
        )

        broker_choices: list[tuple[str, StrOrPromise]] = []
        broker_backend_forms: dict[str, BaseBrokerSettingsForm | None] = {}

        # Go through all the registered broker classes and turn their
        # settings forms into subforms.
        for broker_cls in broker_registry:
            broker_id = broker_cls.broker_id

            if broker_cls.settings_form is not None:
                try:
                    backend_form = self._create_broker_form(
                        broker_cls,
                        bound=(broker_id == cur_broker_id),
                    )
                    broker_backend_forms[broker_id] = backend_form
                except Exception as e:
                    logger.exception(
                        'Error loading settings form for broker backend '
                        '"%s": %s',
                        broker_id, e,
                    )

                    broker_backend_forms[broker_id] = None

            # If the settings form fails to load above, the broker will still
            # be listed so the admin can see what was configured, but can't
            # be saved.
            broker_choices.append((broker_id, broker_cls.name))

        broker_choices.sort(key=lambda pair: pair[1])

        # Check if the existing configured broker was found above.
        #
        # If it's not found, then the existing broker was probably provided
        # by an extension that's no longer enabled. We'll explicitly add this
        # with a "(no longer available)" note, but will refuse to save it.
        #
        # If for some reason this broker ID is not a string (which probably
        # will have led to problems elsewhere), we'll just skip this entirely
        # so a new broker will have to be selected.
        stored_broker_id = siteconfig.get('broker_id')

        if (stored_broker_id and
            isinstance(stored_broker_id, str) and
            broker_registry.get_broker(stored_broker_id) is None):
            broker_choices.append((
                stored_broker_id,
                (_('{broker_id} (no longer available)')
                 .format(broker_id=stored_broker_id)),
            ))

        self.fields['broker_id'].choices = broker_choices
        self.broker_backend_forms = broker_backend_forms

    def clean_broker_id(self) -> str:
        """Clean the broker_id field.

        This will make sure the selected broker is still registered and
        that its settings form could be loaded.

        Returns:
            str:
            The broker ID.

        Raises:
            django.core.exceptions.ValidationError:
                The selected broker is no longer available, or its settings
                form failed to load.
        """
        broker_id = self.cleaned_data['broker_id']
        broker_cls = broker_registry.get_broker(broker_id)

        if broker_cls is None:
            raise ValidationError(
                _(
                    'The broker "{broker_id}" is no longer available. '
                    'Please choose a different broker.'
                ).format(broker_id=broker_id)
            )

        broker_backend_forms = self.broker_backend_forms

        if (broker_id in broker_backend_forms and
            broker_backend_forms[broker_id] is None):
            raise ValidationError(
                _(
                    'The settings for broker "{name}" could not be '
                    'loaded. Check the Review Board log for details.'
                ).format(name=broker_cls.name)
            )

        return broker_id

    def is_valid(self) -> bool:
        """Return whether the form is valid.

        This will validate that both this form and any selected broker's
        subform is valid.

        Returns:
            bool:
            ``True`` if the forms are valid. ``False`` if any are not.
        """
        if not super().is_valid():
            return False

        broker_id = self.cleaned_data['broker_id']
        backend_form = self.broker_backend_forms.get(broker_id)

        return backend_form is None or backend_form.is_valid()

    def full_clean(self) -> None:
        """Clean and validate all form fields.

        This will clean and validate this form and the selected broker's
        settings form.

        The connection to the configured broker will be tested as part of
        validation, helping to ensure that the configuration is correct.
        """
        super().full_clean()

        if self.is_bound and (broker_id := self.cleaned_data.get('broker_id')):
            # There's a valid broker ID. Look for the corresponding subform
            # (if any) and clean it. The subform will take care of a broker
            # connection check.
            if backend_form := self.broker_backend_forms.get(broker_id):
                backend_form.full_clean()

    def save(self) -> None:
        """Save the form.

        This will save the subforms and then reload the site configuration.
        """
        # If there's a broker-specific subform, save that.
        broker_id = self.cleaned_data['broker_id']
        backend_form = self.broker_backend_forms.get(broker_id)

        if backend_form is not None:
            backend_form.save(commit=False)

        super().save()

        load_site_config()

    def _create_broker_form(
        self,
        broker_cls: type[BaseBrokerBackend],
        *,
        bound: bool,
    ) -> BaseBrokerSettingsForm:
        """Return a settings form for a broker.

        This will prefix fields by the broker ID, so that brokers can use the
        same field names without conflicting.

        Args:
            broker_cls (type):
                The broker class owning the settings form.

            bound (bool):
                Whether to bind the form to the data posted to this form.

        Returns:
            reviewboard.broker.base.forms.BaseBrokerSettingsForm:
            The new settings form.
        """
        settings_form_cls = broker_cls.settings_form
        assert settings_form_cls is not None

        if bound and self.is_bound:
            return settings_form_cls(
                data=self.data,
                files=self.files,
                broker_cls=broker_cls,
                prefix=broker_cls.broker_id,
            )
        else:
            return settings_form_cls(
                broker_cls=broker_cls,
                prefix=broker_cls.broker_id,
            )

    class Meta:
        title = _('Background Tasks Settings')

        subforms = (
            {
                'subforms_attr': 'broker_backend_forms',
                'controller_field': 'broker_id',
            },
        )

        fieldsets = (
            {
                'classes': ('wide',),
                'title': _('Message Broker'),
                'description': _(
                    "If you're using a single-server deployment, you can "
                    "stick with the Local broker. If you're scaling out "
                    "Review Board or using Review Bot, you can set up a "
                    "dedicated broker and configure it."
                ),
                'fields': (
                    'broker_id',
                ),
            },
        )
