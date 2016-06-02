"""Database models for integration configuration storage."""

from __future__ import unicode_literals

from django.db import models
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
