"""Admin-specific form widgets."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional, TYPE_CHECKING

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.forms.widgets import MultiWidget, Select, TextInput
from djblets.forms.widgets import (
    RelatedObjectWidget as DjbletsRelatedObjectWidget)
from pygments.lexers import get_all_lexers

from reviewboard.avatars import avatar_services
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository

if TYPE_CHECKING:
    from django.forms.renderers import BaseRenderer
    from django.utils.safestring import SafeString


logger = logging.getLogger(__name__)


class RelatedObjectWidget(DjbletsRelatedObjectWidget):
    """A base class form widget that lets people select one or more objects.

    This is a base class. Extended classes must define their own render()
    method, to render their own widget with their own data.

    This should be used with relatedObjectSelectorView.es6.js, which extends
    a Backbone view to display data.
    """

    ######################
    # Instance variables #
    ######################

    #: The optional Local Site to bound the API requests to.
    local_site_name: Optional[str]

    def __init__(
        self,
        local_site_name: Optional[str] = None,
        multivalued: bool = True,
        **kwargs,
    ) -> None:
        """Initialize the widget.

        Args:
            local_site_name (str, optional):
                The optional Local Site to bound the API requests to.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent.
        """
        super().__init__(multivalued=multivalued,
                         **kwargs)

        self.local_site_name = local_site_name


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

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget.

        Args:
            name (unicode):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
                Attributes for the HTML element.

            renderer (django.forms.renderers.BaseRenderer, optional):
                The form renderer.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        if value:
            if not self.multivalued:
                value = [value]

            value = [v for v in value if v]
            input_value = ','.join(force_str(v) for v in value)
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
            name, input_value, attrs, renderer)

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
            elif isinstance(value, str):
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

    ######################
    # Instance variables #
    ######################

    #: Whether to include accessible invisible repositories in the results.
    #:
    #: Version Added:
    #:     5.0.6
    show_invisible: bool

    def __init__(
        self,
        *args,
        show_invisible: bool = True,
        **kwargs,
    ) -> None:
        """Initialize the RelatedGroupWidget.

        Version Changed:
            5.0.6:
            Added the ``show_invisible`` argument.

        Args:
            show_invisible (bool, optional):
                Whether to include accessible invisible repositories in the
                results.

                This is the default.

                Version Added:
                    5.0.6

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (dict):
                Keyword arguments to pass to the handler.
        """
        super().__init__(*args, **kwargs)

        self.show_invisible = show_invisible

    def render(
        self,
        name: str,
        value: Any,
        attrs: Optional[Dict[str, Any]] = None,
        renderer: Optional[BaseRenderer] = None,
    ) -> SafeString:
        """Render the widget.

        Args:
            name (str):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
                Attributes for the HTML element.

            renderer (django.forms.renderers.BaseRenderer, optional):
                The form renderer.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        existing_repos: Iterable[Repository]
        input_value: Optional[str]

        if value:
            if not self.multivalued:
                value = [value]

            value = [v for v in value if v]
            input_value = ','.join(force_str(v) for v in value)
            existing_repos = (
                Repository.objects
                .filter(pk__in=value)
                .order_by('name')
            )
        else:
            input_value = None
            existing_repos = []

        if attrs:
            final_attrs = dict(self.attrs, **attrs)
        else:
            final_attrs = self.attrs.copy()

        final_attrs['name'] = name

        input_html = super().render(name, input_value, attrs, renderer)

        repo_data = [
            {
                'id': repo.pk,
                'name': repo.name,
            }
            for repo in existing_repos
        ]

        js_view_data: Dict[str, Any] = {
            'initialOptions': repo_data,
            'multivalued': self.multivalued,
            'showInvisible': self.show_invisible,
        }

        if self.local_site_name:
            js_view_data['localSitePrefix'] = f's/{self.local_site_name}/'

        return render_to_string(
            template_name='admin/related_repo_widget.html',
            context={
                'input_html': mark_safe(input_html),
                'input_id': final_attrs['id'],
                'js_view_data': js_view_data,
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
            elif isinstance(value, str):
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

    Version Changed:
        5.0.6:
        * Added an option for enabling specifying invisible review groups.
        * Added support for Python type hints.
    """

    ######################
    # Instance variables #
    ######################

    #: Whether or not to display review groups that are invite-only.
    invite_only: bool

    #: Whether or not to limit review groups to ones that are visible.
    #:
    #: Version Added:
    #:     5.0.6
    show_invisible: bool

    def __init__(
        self,
        invite_only: bool = False,
        *args,
        show_invisible: bool = True,
        **kwargs,
    ) -> None:
        """Initialize the RelatedGroupWidget.

        Version Changed:
            5.0.6:
            Added the ``show_invisible`` argument.

        Args:
            invite_only (bool, optional):
                Whether or not to limit results to accessible review groups
                that are invite-only.

            show_invisible (bool, optional):
                Whether to include accessible invisible review groups in the
                results.

                This is the default.

                Version Added:
                    5.0.6

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (dict):
                Keyword arguments to pass to the handler.
        """
        super().__init__(*args, **kwargs)

        self.invite_only = invite_only
        self.show_invisible = show_invisible

    def render(
        self,
        name: str,
        value: Any,
        attrs: Optional[Dict[str, Any]] = None,
        renderer: Optional[BaseRenderer] = None,
    ) -> SafeString:
        """Render the widget.

        Args:
            name (str):
                The name of the field.

            value (list):
                The current value of the field.

            attrs (dict, optional):
                Attributes for the HTML element.

            renderer (django.forms.renderers.BaseRenderer, optional):
                The form renderer.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        existing_groups: Iterable[Group]
        input_value: Optional[str]

        if value:
            if not self.multivalued:
                value = [value]

            value = [v for v in value if v]
            input_value = ','.join(force_str(v) for v in value)
            existing_groups = (
                Group.objects
                .filter(pk__in=value)
                .order_by('name')
            )
        else:
            input_value = None
            existing_groups = []

        if attrs:
            final_attrs = dict(self.attrs, **attrs)
        else:
            final_attrs = self.attrs.copy()

        final_attrs['name'] = name

        input_html = super().render(name, input_value, attrs, renderer)

        group_data = []

        for group in existing_groups:
            data = {
                'name': group.name,
                'display_name': group.display_name,
                'id': group.pk,
            }

            group_data.append(data)

        js_view_data: Dict[str, Any] = {
            'initialOptions': group_data,
            'inviteOnly': self.invite_only,
            'multivalued': self.multivalued,
            'showInvisible': self.show_invisible,
        }

        if self.local_site_name:
            js_view_data['localSitePrefix'] = f's/{self.local_site_name}/'

        return render_to_string(
            template_name='admin/related_group_widget.html',
            context={
                'input_html': mark_safe(input_html),
                'input_id': final_attrs['id'],
                'js_view_data': js_view_data,
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
            elif isinstance(value, str):
                return [v for v in value.split(',') if v]
            else:
                return None
        elif value:
            return value
        else:
            return None


class LexersMappingWidget(MultiWidget):
    """A form widget for mapping a string to a Pygments Lexer class.

    This widget displays a text input with a drop-down list of
    Pygments Lexer names next to it.

    Version Added:
        5.0
    """

    def __init__(self, attrs=None):
        """Initialize the LexersMappingWidget.

        Args:
            attrs (dict, optional):
                A dictionary containing HTML attributes to be set
                on the rendered widget.
        """
        lexer_choices = [(lex[0], lex[0]) for lex in get_all_lexers()]
        widgets = (
            TextInput(attrs=attrs),
            Select(attrs=attrs, choices=lexer_choices))
        super(LexersMappingWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        """Decompress the value into a list of values for each widget.

        Args:
            value (tuple of str):
                The value from the field. A tuple containing two strings,
                a key and a Pygments Lexer name.

        Returns:
            list of str:
            The list containing a key and lexer name for the widgets.
        """
        if value:
            return list(value)

        return [None, None]

    def value_from_datadict(self, data, files, name):
        """Unpack the field's value from a datadict.

        Args:
            data (dict):
                The form's data.

            files (dict):
                The form's files.

            name (str):
                The name of the field.

        Returns:
            tuple of str:
            The tuple containing a key and lexer name.
        """
        key_lexer = [
            widget.value_from_datadict(data, files, '%s_%s' % (name, i))
            for i, widget in enumerate(self.widgets)]

        if key_lexer:
            return tuple(key_lexer)
        else:
            return (None, None)
