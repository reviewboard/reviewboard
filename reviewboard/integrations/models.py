"""Database models for integration configuration storage."""

from __future__ import unicode_literals

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.conditions import ConditionSet
from djblets.integrations.models import BaseIntegrationConfig

from reviewboard.integrations.base import GetIntegrationManagerMixin
from reviewboard.site.models import LocalSite


class IntegrationConfig(GetIntegrationManagerMixin, BaseIntegrationConfig):
    """Stored configuration for a particular integration.

    This contains configuration settings for a given instance of an
    integration, along with state indicating if that integration is to be
    enabled and user-specified identifying information.
    """

    local_site = models.ForeignKey(
        LocalSite,
        related_name='integration_configs',
        blank=True,
        null=True)

    def load_conditions(self, form_cls, conditions_key='conditions'):
        """Load a set of conditions from the configuration.

        This loads and deserializes a set of conditions from the configuration
        stored in the provided key. Those conditions can then be matched by the
        caller.

        If the conditions are not found, this will return ``None``.

        If the conditions cannot be deserialized, this will log some diagnostic
        output and error messages and return ``None``.

        Args:
            form_cls (type):
                The configuration form class that owns the condition field.

                This will generally be ``my_integration.form_cls``,
                but can be another form in more complex integrations.

            conditions_key (unicode, optional):
                The key for the conditions data in the configuration.
                Defaults to "conditions".

        Returns:
            djblets.conditions.conditions.ConditionSet:
            The condition set based on the data, if found and if it could be
            loaded. Otherwise, ``None`` will be returned.
        """
        conditions_data = self.get(conditions_key)

        if not conditions_data:
            return None

        try:
            return ConditionSet.deserialize(
                form_cls.base_fields[conditions_key].choices,
                conditions_data,
                choice_kwargs={
                    'local_site': self.local_site,
                })
        except:
            logging.exception('Unable to load bad condition set data for '
                              'integration configuration ID=%s for key="%s"',
                              self.pk, conditions_key)
            logging.debug('Bad conditions data = %r', conditions_data)

            return None

    def match_conditions(self, form_cls, conditions_key='conditions',
                         **match_kwargs):
        """Filter configurations based on a review request.

        If the configuration contains a ``conditions`` key, and the
        configuration form contains a matching field, this will check
        the conditions for matches against the review request.

        Args:
            form_cls (type):
                The configuration form class that owns the condition field.

                This will generally be ``my_integration.form_cls``,
                but can be another form in more complex integrations.

            conditions_key (unicode, optional):
                The key for the conditions data in the configuration.
                Defaults to "conditions".

            **match_kwargs (dict):
                Keyword arguments to match for the conditions.

        Returns:
            bool:
            ``True`` if the specified conditions in the configuration matches
            the provided keyword arguments. ``False`` if not.
        """
        condition_set = self.load_conditions(form_cls, conditions_key)

        if condition_set:
            try:
                return condition_set.matches(**match_kwargs)
            except Exception as e:
                logging.exception(
                    'Unexpected failure when matching conditions for '
                    'integration configuration ID=%s, config_key=%s, '
                    'match_kwargs=%r: %s',
                    self.pk, conditions_key, match_kwargs, e)

        return False

    class Meta:
        db_table = 'integrations_integrationconfig'
        verbose_name = _('Integration Configuration')
        verbose_name_plural = _('Integration Configurations')
