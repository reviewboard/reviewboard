"""Base configuration form for broker settings.

Version Added:
    9.0
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _
from djblets.forms.forms import KeyValueForm
from djblets.siteconfig.models import SiteConfiguration
from typelets.json import JSONDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.broker.base.backends import BaseBrokerBackend


logger = logging.getLogger(__name__)


class BaseBrokerSettingsForm(KeyValueForm[JSONDict]):
    """Base configuration form for broker settings.

    This can be subclassed and used by broker backends to provide admin UI
    configuration for a broker's settings.

    Subclasses can define fields for each broker setting. They'll be
    loaded automatically from stored broker settings and saved back out.

    As part of validation, the form will also check that the broker can be
    used with the new settings by attempting to establish a connection to
    the broker.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The parent broker class.
    broker_cls: type[BaseBrokerBackend]

    #: The site configuration where broker settings will be stored.
    siteconfig: SiteConfiguration

    def __init__(
        self,
        *args,
        broker_cls: type[BaseBrokerBackend],
        **kwargs,
    ) -> None:
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent.

            broker_cls (type):
                The broker class that owns this form.

            **kwargs (dict):
                Keyword arguments to pass to the parent.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        self.broker_cls = broker_cls
        self.siteconfig = siteconfig

        # The form works on its own copy of any existing settings. Settings
        # will only be added to siteconfig once the form is saved.
        instance: JSONDict = {}
        brokers_settings = siteconfig.get('brokers')

        if isinstance(brokers_settings, dict):
            broker_settings = brokers_settings.get(broker_cls.broker_id)

            if isinstance(broker_settings, dict):
                # Broker settings were found. Set a deep copy of this as our
                # working instance.
                instance = copy.deepcopy(broker_settings)

        super().__init__(
            *args,
            instance=instance,
            **kwargs,
        )

    def full_clean(self) -> None:
        """Clean and validate all form fields.

        Once the fields are valid, this will check that the broker can be
        used with the new settings. If it can't, the form will be invalid and
        an error will be provided.
        """
        super().full_clean()

        if self.is_bound and not self.errors:
            broker_cls = self.broker_cls
            broker_settings = self.get_pending_broker_settings()

            try:
                broker_cls().check_connection(broker_settings)
            except Exception as e:
                logger.exception(
                    'Error checking the connection to broker backend "%s": %s',
                    broker_cls.broker_id, e,
                )

                self.add_error(
                    None,
                    _('Unable to connect to the "{name}" broker: {error}')
                    .format(
                        name=broker_cls.name,
                        error=e,
                    ),
                )

    def get_pending_broker_settings(self) -> JSONDict:
        """Return the broker settings as they'd be after saving the form.

        This won't modify the stored settings, which makes it useful for
        checking new settings before they're saved.

        The form must be valid before calling this.

        Returns:
            dict:
            A copy of the stored broker settings based on the form.
        """
        # Save to our copy of the settings, but don't save to the siteconfig,
        # since we're not writing there. 
        return super().save(commit=False)

    def save(
        self,
        commit: bool = True,
        *args,
        **kwargs,
    ) -> JSONDict:
        """Save the broker settings.

        This will update the broker settings in the site configuration
        based on the form.

        Args:
            commit (bool, optional):
                Whether to save the site configuration to the database.

                If ``False``, the site configuration will be updated in
                memory, and the caller will be responsible for saving it.

            *args (tuple):
                Extra positional arguments to pass to the parent method.

            **kwargs (dict):
                Extra keyword arguments to pass to the parent method.

        Returns:
            dict:
            The new broker settings.

        Raises:
            ValueError:
                The form couldn't be saved due to errors.
        """
        broker_settings = super().save(
            commit=False,
            *args,
            **kwargs,
        )

        # Start by getting the broker settings. This is going to ensure
        # we have a dictionary in the right place in siteconfig we can
        # write to.
        #
        # We're then going to just replace it with our pending copy, which
        # is based off the stored broker settings, so it'll carry over any
        # extra state not managed by the form.
        stored_settings = self.broker_cls.get_broker_settings()
        stored_settings.update(copy.deepcopy(broker_settings))

        if commit:
            self.siteconfig.save()

        return broker_settings
