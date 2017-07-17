"""OAuth-specific form widgets."""

from __future__ import unicode_literals

from django.forms import widgets
from django.template.loader import render_to_string


class OAuthSecretInputWidget(widgets.TextInput):
    """A text input for updating an OAuth2 application's client secret.

    OAuth applications should never have their client secret determined by the
    user. We do not ever want to risk them using an insecure secret. Therefore,
    forms will always ignore this value and this widget will, upon request, hit
    the web API to generate a new client secret.

    Because this widget requires the ``api_url``, which is dependent on the
    object being edited, this widget must be initialized in the form's
    ``__init__`` method.
    """

    template_name = 'oauth/secret_input_widget.html'

    def __init__(self, api_url=None, *args, **kwargs):
        """Initialize the widget.

        Args:
            api_url (unicode):
                The URL to the :py:class:`reviewboard.webapi.resources.oauth_app.OAuthApplicationResource`.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """

        super(OAuthSecretInputWidget, self).__init__(*args, **kwargs)

        self.api_url = api_url

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (unicode):
                The value of the field.

            attrs (dict, optional):
                The widget's attributes.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        field = super(OAuthSecretInputWidget, self).render(name, value,
                                                           attrs=attrs)

        return render_to_string(
            self.template_name,
            {
                'field': field,
                'id': attrs['id'],
                'name': name,
                'api_url': self.api_url,
            },
        )
