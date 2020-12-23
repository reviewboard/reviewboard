"""Form-related classes for the administration Change Form pages."""

from __future__ import unicode_literals

import itertools

from django import forms
from django.contrib.admin.helpers import Fieldline, Fieldset
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.forms.utils import flatatt
from django.template.defaultfilters import capfirst, linebreaksbr
from django.template.loader import render_to_string
from django.utils import six
from django.utils.encoding import force_text
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from reviewboard.admin.form_widgets import (RelatedGroupWidget,
                                            RelatedRepositoryWidget,
                                            RelatedUserWidget)
from reviewboard.reviews.models import Group
from reviewboard.scmtools.models import Repository


class ChangeFormFieldset(Fieldset):
    """A fieldset in an administration change form.

    This takes care of providing state to the change form to represent a
    fieldset and each row in that fieldset.

    The fieldset makes use of the ``.rb-c-form-fieldset`` CSS component.
    """

    def __init__(self, form, classes=(), **kwargs):
        """Initialize the fieldset.

        Args:
            form (django.contrib.admin.helpers.AdminForm):
                The administration form owning the fieldset.

            classes (tuple, optional):
                Additional CSS classes to add to the ``<fieldset>`` element.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        if classes:
            # Transform any Django-named CSS classes to what we expect for our
            # rb-c-admin-fieldset CSS component's modifiers.
            css_class_map = {
                'collapse': ('-can-collapse', '-is-collapsed'),
                'wide': ('-is-wide',),
            }

            classes = tuple(itertools.chain.from_iterable(
                css_class_map.get(css_class, (css_class,))
                for css_class in classes
            ))

        self.collapsed = '-is-collapsed' in classes

        super(ChangeFormFieldset, self).__init__(
            form,
            classes=('rb-c-form-fieldset',) + classes,
            **kwargs)

    def render(self, context):
        """Render the fieldset to HTML.

        This will default to rendering using the
        ``admin/includes/fieldset.html`` template. A
        :py:class:`~django.contrib.admin.ModelAdmin` subclass my define a
        ``fieldset_template_name`` attribute specifying an alternative template
        to use for its fieldsets.

        The template will inherit the provided context, and will contain
        this fieldset instance as ``fieldset``.

        Args:
            context (django.template.Context):
                The current template context.

        Returns:
            django.utils.safestring.SafeText:
            The resulting HTML for the fieldset.
        """
        template_name = (
            getattr(self.model_admin, 'fieldset_template_name', None) or
            'admin/includes/fieldset.html'
        )

        with context.push():
            context['fieldset'] = self

            return render_to_string(template_name, context.flatten())

    def __iter__(self):
        """Iterate through the rows of the fieldset.

        Yields:
            ChangeFormRow:
            A row in the fieldset.
        """
        readonly_fields = self.readonly_fields
        model_admin = self.model_admin

        for field in self.fields:
            yield ChangeFormRow(form=self.form,
                                field=field,
                                readonly_fields=readonly_fields,
                                model_admin=model_admin)


class ChangeFormRow(Fieldline):
    """A row in a fieldset containing one or more fields.

    A row may contain multiple fields (though it usually contains only one).

    This makes use of the ``.rb-c-form-row`` CSS component.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the row.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        super(ChangeFormRow, self).__init__(*args, **kwargs)

        self.is_multi_line = len(self.fields) > 1
        self.classes = ' '.join(['rb-c-form-row'] + [
            'field-%s' % field_name
            for field_name in self.fields
        ])
        self.row_id = 'row-%s' % self.fields[0]

    def __iter__(self):
        """Iterate through the list of fields in the row.

        Yields:
            ChangeFormField:
            A field in the row.
        """
        for admin_field in super(ChangeFormRow, self).__iter__():
            yield ChangeFormField(self, admin_field)


class ChangeFormField(object):
    """A wrapper for a field on the change form.

    This takes care of providing state to the change form to represent an
    individual field on a row, providing any field validation errors.

    It also takes care of creating ideal representations of some widgets
    (such as our special related object widgets for users, groups, and
    repositories, and filtered multi-select for other many-to-many relations).

    This makes use of the ``.rb-c-form-field`` CSS component.
    """

    def __init__(self, form_row, admin_field):
        """Initialize the field wrapper.

        Args:
            form_row (ChangeFormRow):
                The parent row containing the field.

            admin_field (django.contrib.admin.helpers.AdminField):
                The administration field wrapper containing state for this
                field.
        """
        bound_field = admin_field.field
        has_field_first = False
        show_errors = False
        is_checkbox = getattr(admin_field, 'is_checkbox', False)
        is_readonly = getattr(admin_field, 'is_readonly', False)

        classes = ['rb-c-form-field']

        if is_readonly:
            classes.append('-is-read-only')
            errors = []
        else:
            form_field = bound_field.field
            errors = admin_field.errors()

            if form_field.required:
                classes.append('-is-required')

            if errors:
                classes.append('-has-errors')
                show_errors = True

            if isinstance(form_field, forms.ModelMultipleChoiceField):
                widget = form_field.widget
                model = form_field.queryset.model

                if type(widget) is forms.ModelMultipleChoiceField.widget:
                    # This is a default widget for a model multi-choice field.
                    # Let's see if we use a better default.
                    if model is User:
                        form_field.widget = RelatedUserWidget()
                    elif model is Group:
                        form_field.widget = RelatedGroupWidget()
                    elif model is Repository:
                        form_field.widget = RelatedRepositoryWidget()
                    else:
                        # We can at least use the filtered selector.
                        form_field.widget = FilteredSelectMultiple(
                            form_field.label,
                            is_stacked=False)

                if type(widget) is not widget:
                    # We've replaced the widget, so get rid of the old bound
                    # help text while we're at it.
                    bound_field.help_text = None

        if form_row.is_multi_line:
            classes.append('field-%s' % bound_field.name)
        elif is_checkbox:
            classes.append('-has-input-first')
            has_field_first = True

        self.admin_field = admin_field
        self.classes = ' '.join(classes)
        self.errors = errors
        self.field = bound_field
        self.has_field_first = has_field_first
        self.is_checkbox = is_checkbox
        self.is_first = admin_field.is_first
        self.is_readonly = is_readonly
        self.show_errors = show_errors

    def label_tag(self):
        """Return the HTML for a label tag for this field.

        This will create a ``<label class="rb-c-form-field_label">`` element
        containing the label.

        Returns:
            django.utils.safestring.SafeText:
            The ``<label>`` tag for this field.
        """
        field = self.field
        attrs = {}
        classes = ['rb-c-form-field__label']

        if not self.is_first:
            classes.append('-is-inline')

        attrs['class'] = ' '.join(classes)

        if self.is_readonly:
            return format_html('<label{0}>{1}:</label>',
                               flatatt(attrs),
                               capfirst(force_text(field['label'])))
        else:
            if self.has_field_first:
                label_suffix = ''
            else:
                label_suffix = None

            return field.label_tag(
                contents=conditional_escape(force_text(field.label)),
                attrs=attrs,
                label_suffix=label_suffix)

    def render(self):
        """Render the field.

        This will return the rendered field as HTML, or just the field's value
        if the field is meant to be read-only.

        Returns:
            django.utils.safestring.SafeText:
            The rendered content for the field.
        """
        if self.is_readonly:
            return format_html(
                '<div class="rb-c-form-field__readonly-value">{0}</div>',
                linebreaksbr(self.admin_field.contents()))
        else:
            return mark_safe(six.text_type(self.field))
