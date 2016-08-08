"""Admin-specific form widgets."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.forms.widgets import HiddenInput
from django.template.loader import render_to_string
from django.utils import six
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from djblets.gravatars import get_gravatar_url
from djblets.siteconfig.models import SiteConfiguration


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

    def __init__(self, local_site_name=None):
        super(RelatedUserWidget, self).__init__()

        self.local_site_name = local_site_name

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

        # The Gravatar API in Djblets currently uses the request to determine
        # whether or not to use https://secure.gravatar.com or
        # http://gravatar.com. Unfortunately, it's hard enough to get a copy of
        # the request in a form, much less in a form widget. Instead, we fake
        # the request here and just always use the HTTPS one. This will be
        # dramatically better in 3.0+ with the new avatar services.
        class FakeRequest(object):
            def is_secure(self):
                return True

        fake_request = FakeRequest()
        siteconfig = SiteConfiguration.objects.get_current()
        use_gravatars = siteconfig.get('integration_gravatars')
        user_data = []

        for user in existing_users:
            data = {
                'fullname': user.get_full_name(),
                'id': user.pk,
                'username': user.username,
            }

            if use_gravatars:
                data['avatar_url'] = get_gravatar_url(fake_request, user, 40)

            user_data.append(data)

        extra_html = render_to_string('admin/related_user_widget.html', {
            'input_id': final_attrs['id'],
            'local_site_name': self.local_site_name,
            'use_gravatars': use_gravatars,
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

        if isinstance(value, list):
            return value
        elif isinstance(value, six.string_types):
            return [v for v in value.split(',') if v]
        else:
            return None
