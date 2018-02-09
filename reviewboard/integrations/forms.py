"""Configuration forms for integrations."""

from __future__ import unicode_literals

from django import forms
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from djblets.forms.fields import ConditionsField
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

    Attributes:
        limit_to_local_site (reviewboard.site.models.LocalSite):
            The optional LocalSite to limit this configuration to. Any
            configuration-related fields or logic that might need to be bound
            to a LocalSite must make use of this.
    """

    #: A list of fields on the model that should not be saved in settings
    model_fields = DjbletsIntegrationConfigForm.model_fields + ('local_site',)

    #: The fieldset containing basic information on the configuration.
    #:
    #: This is the same as the djblets version, but with the local site field
    #: added in.
    basic_info_fieldset = (None, {
        'fields': ('name', 'enabled', 'local_site'),
        'description': _(
            'Start by giving this configuration a name so you can easily '
            'identify it later. You can also mark this configuration as '
            'enabled or disabled.'
        ),
    })

    local_site = forms.ModelChoiceField(
        label=_('Local Site'),
        queryset=LocalSite.objects.all(),
        required=False)

    def __init__(self, *args, **kwargs):
        """Initialize the form.

        Args:
            limit_to_local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site to limit configurations to. If ``None`` (or not
                provided), the configuration's Local Site (or lack thereof) can
                be specified by the user.

            *args (tuple):
                Positional arguments to pass to the parent form.

            **kwargs (dict):
                Keyword arguments to pass to the parent form.
        """
        local_site = kwargs.pop('limit_to_local_site', None)
        self.limit_to_local_site = local_site

        super(IntegrationConfigForm, self).__init__(*args, **kwargs)

        if local_site:
            self.fields['local_site'].queryset = \
                LocalSite.objects.filter(pk=local_site.pk)

            # Limit LocalSites for all condition fields.
            for field in six.itervalues(self.fields):
                if isinstance(field, ConditionsField):
                    field.choice_kwargs['local_site'] = local_site
