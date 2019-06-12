"""Admin-specific form widgets."""

from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.utils import six
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from djblets.forms.widgets import (
    RelatedObjectWidget as DjbletsRelatedObjectWidget)
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.avatars import avatar_services
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


class RelatedObjectWidget(DjbletsRelatedObjectWidget):
    """A base class form widget that lets people select one or more objects.

    This is a base class. Extended classes must define their own render()
    method, to render their own widget with their own data.

    This should be used with relatedObjectSelectorView.es6.js, which extends
    a Backbone view to display data.
    """

    def __init__(self, local_site_name=None, multivalued=True):
        super(RelatedObjectWidget, self).__init__(multivalued)

        self.local_site_name=local_site_name


class RelatedUserWidget(RelatedObjectWidget):
    """A form widget to allow people to select one or more User relations.

    It's not unheard of to have a server with thousands or tens of thousands of
    registered users. In this case, the existing Django admin widgets fall down
    hard. The filtered select widgets can actually crash the webserver due to
    trying to pre-populate an enormous ``<select>`` element, and the raw ID
    widget is basically a write-only field.

    This field does much better, offering both the ability to see who's already
    in the list, as well as interactive search and filtering.
    """

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
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

        final_attrs = dict(self.attrs, **attrs)
        final_attrs['name'] = name

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
                    data['avatarHTML'] = (
                        avatar_services.for_user(user)
                        .render(request=None,
                                user=user,
                                size=20)
                    )
                except Exception as e:
                    logger.exception(
                        'Error rendering avatar for RelatedUserWidget: %s',
                        e)
                    data['avatarHTML'] = None

            user_data.append(data)

        return render_to_string(
            template_name='admin/related_user_widget.html',
            context={
                'input_html': mark_safe(input_html),
                'input_id': final_attrs['id'],
                'local_site_name': self.local_site_name,
                'multivalued': self.multivalued,
                'use_avatars': use_avatars,
                'users': user_data,
            })

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


class RelatedRepositoryWidget(RelatedObjectWidget):
    """A form widget allowing people to select one or more Repository objects.

    This widget offers both the ability to see which repositories are already
    in the list, as well as interactive search and filtering.
    """

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
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
            existing_repos = (
                Repository.objects
                .filter(pk__in=value)
                .order_by('name')
            )
        else:
            input_value = None
            existing_repos = []

        final_attrs = dict(self.attrs, **attrs)
        final_attrs['name'] = name

        input_html = super(RelatedRepositoryWidget, self).render(
            name, input_value, attrs)

        repo_data = [
            {
                'id': repo.pk,
                'name': repo.name,
            }
            for repo in existing_repos
        ]

        return render_to_string(
            template_name='admin/related_repo_widget.html',
            context={
                'input_html': mark_safe(input_html),
                'input_id': final_attrs['id'],
                'local_site_name': self.local_site_name,
                'multivalued': self.multivalued,
                'repos': repo_data,
            })

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
            The list of IDs of
            :py:class:`~reviewboard.scmtools.models.Repository` objects.
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


class RelatedGroupWidget(RelatedObjectWidget):
    """A form widget allowing people to select one or more Group objects.

    This widget offers both the ability to see which groups are already in the
    list, as well as interactive search and filtering.
    """

    def __init__(self, invite_only=False, *args, **kwargs):
        """Initialize the RelatedGroupWidget.

        Args:
            invite_only (bool, optional):
                Whether or not to display groups that are invite-only.

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (dict):
                Keyword arguments to pass to the handler.
        """
        super(RelatedGroupWidget, self).__init__(*args, **kwargs)
        self.invite_only = invite_only

    def render(self, name, value, attrs=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
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
            existing_groups = (
                Group.objects
                .filter(pk__in=value)
                .order_by('name')
            )
        else:
            input_value = None
            existing_groups = []

        final_attrs = dict(self.attrs, **attrs)
        final_attrs['name'] = name

        input_html = super(RelatedGroupWidget, self).render(
            name, input_value, attrs)

        group_data = []

        for group in existing_groups:
            data = {
                'name': group.name,
                'display_name': group.display_name,
                'id': group.pk,
            }

            group_data.append(data)

        return render_to_string(
            template_name='admin/related_group_widget.html',
            context={
                'input_html': mark_safe(input_html),
                'input_id': final_attrs['id'],
                'local_site_name': self.local_site_name,
                'multivalued': self.multivalued,
                'groups': group_data,
                'invite_only': self.invite_only,
            })

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
            The list of PKs of Group objects.
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
