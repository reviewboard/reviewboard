"""The base search backend classes."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from djblets.siteconfig.models import SiteConfiguration
from haystack.utils.loading import load_backend


class SearchBackendForm(forms.Form):
    """A search backend configuration form.

    This form allows the configuration of a Haystack backend to be configured
    from the admin interface and reloaded on the fly.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the backend.

        Args:
            request (django.http.HttpRequest):
                The current HTTP request.
        """
        self.request = kwargs.pop('request')

        super(SearchBackendForm, self).__init__(*args, **kwargs)


class SearchBackend(object):
    """A search backend.

    A SearchBackend is a wrapper around a Haystack backend that has methods for
    getting and setting per-backend configuration. This allows the backend to
    be configured at runtime and live reloaded, instead of having them
    hardcoded in :file:`settings.py`.
    """

    #: The search engine's unique identifier.
    search_backend_id = None

    #: The human-readable name for the search engine.
    name = None

    #: The name of the Haystack search engine backend.
    haystack_backend_name = None

    #: The configuration form class for the search engine.
    config_form_class = None

    #: The default search engine settings.
    default_settings = {}

    #: A mapping of search engine settings to form fields.
    form_field_map = {}

    @property
    def configuration(self):
        """The configuration for the search engine.

        Returns:
            dict:
            The configuration for the search engine.
        """
        engine_settings = (
            SiteConfiguration.objects
            .get_current()
            .get('search_backend_settings')
            .get(self.search_backend_id, {})
        )

        configuration = {
            key: engine_settings.get(key, self.default_settings[key])
            for key in self.default_settings.keys()
        }
        configuration['ENGINE'] = self.haystack_backend_name

        return configuration

    @configuration.setter
    def configuration(self, value):
        """Set the configuration for the search engine.

        This does not save the configuration to the database.
        :py:meth:`djblets.siteconfig.models.SiteConfiguration.save` must be
        called.

        Args:
            value (dict):
                The configuration to set.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        search_backend_settings = siteconfig.get('search_backend_settings')
        engine_settings = \
            search_backend_settings.setdefault(self.search_backend_id, {})

        engine_settings.update({
            key: value[key]
            for key in self.default_settings.keys()
            if key in value
        })

        siteconfig.set('search_backend_settings', search_backend_settings)
        siteconfig.save(update_fields=('settings',))

    def get_configuration_from_form_data(self, form_data):
        """Return the configuration from the form's data.

         Args:
             form_data (dict):
                The form data.

        Returns:
            dict:
            The search engine configuration.
        """
        return {
            config_key: form_data.get(field_name)
            for field_name, config_key in self.form_field_map.items()
        }

    def get_form_data(self):
        """Return the form data for the current configuration.

        Returns:
            dict:
            The search engine form data.
        """
        configuration = self.configuration

        return {
            field_name: configuration[config_key]
            for field_name, config_key in self.form_field_map.items()
        }

    def load_haystack_engine(self, **kwargs):
        """Load the Haystack backend engine.

        This will construct the engine with the provided parameters. A new
        instance will be constructed every time this is called.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the engine constructor.

        Returns:
            django_haystack.backends.BaseEngine:
            The resulting engine instance.
        """
        engine_cls = load_backend(self.haystack_backend_name)

        return engine_cls(**kwargs)

    def validate(self, configuration, **kwargs):
        """Validate the settings and dependencies for the search backend.

        This will perform a test search to ensure the configuration works.

        Subclasses can override this to perform other checks that may be
        required (such as checking for a suitable module). They should call
        the parent method in order to perform a test search using the
        configured settings.

        Version Changed:
            4.0.5:
            Added the ``configuration`` and ``**kwargs`` arguments. Subclasses
            msut be updated to take ``**kwargs``.

        Raises:
            django.core.exceptions.ValidationError:
                Backend configuration, supporting modules, or the test
                search failed.
        """
        new_config = configuration.copy()
        new_config['SILENTLY_FAIL'] = False

        engine = self.load_haystack_engine()
        backend = engine.backend(engine.using, **new_config)

        try:
            backend.search('___reviewboard-search-config-test___')
        except Exception as e:
            raise ValidationError(
                _('Performing a test query failed. Make sure your '
                  'configuration is correct. The error we received from the '
                  'search backend was: %s')
                % e)

    def get_config_form(self, data=None, **kwargs):
        """Create and return a new configuration form instance.

        The returned form will have a prefix of the search engine ID.

        Args:
            data (dict, optional):
                The form data.

            **kwargs (dict):
                Additional keyword arguments to pass to the form.

        Returns:
            SearchBackendForm:
            The instantiated form class.
        """
        return self.config_form_class(initial=self.get_form_data(),
                                      data=data,
                                      prefix=self.search_backend_id,
                                      **kwargs)
