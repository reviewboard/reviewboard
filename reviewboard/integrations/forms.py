"""Configuration forms for integrations."""

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _
from djblets.integrations.forms import (IntegrationConfigForm as
                                        DjbletsIntegrationConfigForm)

from reviewboard.site.models import LocalSite


class IntegrationConfigForm(DjbletsIntegrationConfigForm):
    """Base class for an integration settings form.

    This makes it easy to provide a basic form for manipulating the settings
    of an integration configuration. It takes care of loading/saving the
    values and prompting the user for a name.

    Integrations should subclass this and provide additional fields that they
    want to display to the user. They must provide a :py:class:`Meta` class
    containing the fieldsets they want to display.
    """

    model_fields = (
        DjbletsIntegrationConfigForm.model_fields +
        ('local_site',)
    )

    local_site = forms.ModelChoiceField(
        label=_('Local Site'),
        queryset=LocalSite.objects.all(),
        required=False)
