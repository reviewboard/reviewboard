"""Administration form for search settings."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.inspect import func_accepts_kwargs
from django.utils.translation import gettext, gettext_lazy as _
from djblets.siteconfig.forms import SiteSettingsForm

from reviewboard.admin.siteconfig import load_site_config
from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.search import search_backend_registry


class SearchSettingsForm(SiteSettingsForm):
    """Form for search settings.

    This form manages the main search settings (enabled, how many results, and
    what backend to use), as well as displaying per-search backend forms so
    that they may be configured.

    For example, Elasticsearch requires a URL and index name, while Whoosh
    requires a file path to store its index. These fields (and fields for any
    other added search backend) will only be shown to the user when the
    appropriate search backend is selected.
    """

    search_enable = forms.BooleanField(
        label=_('Enable search'),
        help_text=_('If enabled, provides a search field for quickly '
                    'searching through review requests, diffs, and users.'),
        required=False)

    search_results_per_page = forms.IntegerField(
        label=_('Search results per page'),
        min_value=1,
        required=False)

    search_backend_id = forms.ChoiceField(
        label=_('Search backend'),
        required=False,
        widget=forms.Select(attrs={
            'data-subform-group': 'search-backend',
        }))

    search_on_the_fly_indexing = forms.BooleanField(
        label=_('On-the-fly indexing'),
        required=False,
        help_text=('If enabled, the search index will be updated dynamically '
                   'when review requests or users change.<br>'
                   '<strong>Note:</strong> This is not recommended for use '
                   'with the Whoosh engine for large or multi-server '
                   'installs.'))

    def __init__(self, siteconfig, data=None, *args, **kwargs):
        """Initialize the search engine settings form.

        This will also initialize the settings forms for each search engine
        backend.

        Args:
            site_config (djblets.siteconfig.models.SiteConfiguration):
                The site configuration handling the server's settings.

            data (dict, optional):
                The form data.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """
        super(SearchSettingsForm, self).__init__(siteconfig, data, *args,
                                                 **kwargs)

        request = kwargs.get('request')
        cur_search_backend_id = (self['search_backend_id'].data or
                                 self.fields['search_backend_id'].initial)

        choices = []
        search_backend_forms = {}

        for backend in search_backend_registry:
            search_backend_id = backend.search_backend_id

            if cur_search_backend_id == search_backend_id:
                subform = backend.get_config_form(data,
                                                  files=kwargs.get('files'),
                                                  request=request)
            else:
                subform = backend.get_config_form(request=request)

            search_backend_forms[search_backend_id] = subform
            choices.append((search_backend_id, backend.name))

        self.search_backend_forms = search_backend_forms
        self.fields['search_backend_id'].choices = choices

    def is_valid(self):
        """Return whether the form is valid.

        This will check the validity of the fields on this form and on
        the selected search backend's settings form.

        Returns:
            bool:
            ``True`` if the main settings form and search backend's settings
            form is valid. ``False`` if either form is invalid.
        """
        if not super(SearchSettingsForm, self).is_valid():
            return False

        backend_id = self.cleaned_data['search_backend_id']
        backend_form = self.search_backend_forms[backend_id]

        return backend_form.is_valid()

    def clean_search_backend_id(self):
        """Clean the ``search_backend_id`` field.

        This will ensure the chosen search backend is valid (i.e., it is
        available in the registry) and that its dependencies have been
        installed.

        Returns:
            unicode:
            The search backend ID.

        Raises:
            django.core.exceptions.ValidationError:
                Raised if the search engine ID chosen cannot be used.
        """
        search_backend_id = self.cleaned_data['search_backend_id']
        search_backend = search_backend_registry.get_search_backend(
            search_backend_id)

        if not search_backend:
            raise ValidationError(
                gettext('The search engine "%s" could not be found. '
                        'If this is provided by an extension, you will have '
                        'to make sure that extension is enabled.')
                % search_backend_id
            )

        return search_backend_id

    def clean(self):
        """Clean the form and the sub-form for the selected search backend.

        Returns:
            dict:
            The cleaned data.
        """
        cleaned_data = self.cleaned_data

        if cleaned_data['search_enable']:
            search_backend_id = cleaned_data.get('search_backend_id')

            # The search_backend_id field is only available if the backend
            # passed validation.
            if search_backend_id:
                backend_form = self.search_backend_forms[search_backend_id]

                # Validate the configuration form.
                if backend_form.is_valid():
                    # Validate the search backend, ensuring the configuration
                    # is correct.
                    search_backend = \
                        search_backend_registry.get_search_backend(
                            search_backend_id)
                    configuration = \
                        search_backend.get_configuration_from_form_data(
                            backend_form.cleaned_data)

                    try:
                        if func_accepts_kwargs(search_backend.validate):
                            search_backend.validate(
                                configuration=configuration)
                        else:
                            RemovedInReviewBoard60Warning.warn(
                                '%s.validate() must accept keyword '
                                'arguments. This will be required in '
                                'Review Board 6.0.'
                                % search_backend.__class__.__name__)
                            search_backend.validate()
                    except ValidationError as e:
                        self.add_error('search_backend_id', e.error_list)
                else:
                    # The configuration form had issues.
                    self._errors.update(backend_form.errors)

        return cleaned_data

    def save(self):
        """Save the form and sub-form for the selected search backend.

        This forces a site configuration reload.
        """
        search_backend_id = self.cleaned_data['search_backend_id']

        if self.cleaned_data['search_enable']:
            # We only need to update the backend settings when search is
            # enabled.
            backend_form = self.search_backend_forms[search_backend_id]
            backend = search_backend_registry.get_search_backend(
                search_backend_id)
            backend.configuration = backend.get_configuration_from_form_data(
                backend_form.cleaned_data)

        super(SearchSettingsForm, self).save()

        # Reload any import changes to the Django settings.
        load_site_config()

    class Meta:
        title = _('Search Settings')
        subforms = (
            {
                'subforms_attr': 'search_backend_forms',
                'controller_field': 'search_backend_id',
            },
        )
