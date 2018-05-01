"""Admin-specific form widgets."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.forms.widgets import HiddenInput
from django.template.loader import render_to_string
from django.utils import six
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe

from reviewboard.avatars import avatar_services


class RelatedUserWidget(HiddenInput):
    """A form widget to allow people to select one or more User relations.

    It's not unheard of to have a server with thousands or tens of thousands of
    registered users. In this case, the existing Django admin widgets fall down
    hard. The filtered select widgets can actually crash the webserver due to
    trying to pre-populate an enormous ``<select>`` element, and the raw ID
    widget is basically a write-only field.

    This field does much better, offering both the ability to see who's already
    in the list, as well as interactive search and filtering.
    """

    # We inherit from HiddenInput in order for the superclass to render a
    # hidden <input> element, but the siteconfig field template special cases
    # when ``is_hidden`` is True. Setting it to False still gives us the
    # rendering and data handling we want but renders fieldset fields
    # correctly.
    is_hidden = False

    def __init__(self, local_site_name=None, multivalued=True):
        """Initalize the RelatedUserWidget.

        Args:
            local_site_name (unicode, optional):
                The name of the LocalSite where the widget is being rendered.

            multivalued (bool, optional):
                Whether or not the widget should allow selecting multiple
                values.
        """
        super(RelatedUserWidget, self).__init__()

        self.local_site_name = local_site_name
        self.multivalued = multivalued

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (list or None):
                The current value of the field.

            attrs (dict):
                Attributes for the HTML element.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        if value:
            if not self.multivalued:
                value = [value]

            value = [v for v in value if v]
            input_value = ','.join(force_text(v) for v in value)
            existing_users = (
                User.objects
                .filter(pk__in=value)
                .order_by('first_name', 'last_name', 'username')
            )
        else:
            input_value = None
            existing_users = []

        final_attrs = self.build_attrs(attrs, name=name)

        input_html = super(RelatedUserWidget, self).render(
            name, input_value, attrs)

        use_avatars = avatar_services.avatars_enabled
        user_data = []

        for user in existing_users:
            data = {
                'fullname': user.get_full_name(),
                'id': user.pk,
                'username': user.username,
            }

            if use_avatars:
                try:
                    data['avatarURL'] = (
                        avatar_services.for_user(user)
                        .get_avatar_urls_uncached(user, 40)
                    )['1x']
                except (AttributeError, KeyError):
                    data['avatarURL'] = None

            user_data.append(data)

        extra_html = render_to_string('admin/related_user_widget.html', {
            'input_id': final_attrs['id'],
            'local_site_name': self.local_site_name,
            'multivalued': self.multivalued,
            'use_avatars': use_avatars,
            'users': user_data,
        })

        return mark_safe(input_html + extra_html)

    def value_from_datadict(self, data, files, name):
        """Unpack the field's value from a datadict.

        Args:
            data (dict):
                The form's data.

            files (dict):
                The form's files.

            name (unicode):
                The name of the field.

        Returns:
            list:
            The list of PKs of User objects.
        """
        value = data.get(name)

        if self.multivalued:
            if isinstance(value, list):
                return value
            elif isinstance(value, six.string_types):
                return [v for v in value.split(',') if v]
            else:
                return None
        elif value:
            return value
        else:
            return None
