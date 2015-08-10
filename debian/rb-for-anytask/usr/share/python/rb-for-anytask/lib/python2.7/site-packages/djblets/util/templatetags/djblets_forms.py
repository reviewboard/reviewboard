#
# djblets_forms.py -- Form-related template tags
#
# Copyright (c) 2008-2009  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django import forms, template
from django.utils.encoding import force_unicode
from django.utils.html import escape


register = template.Library()


@register.simple_tag
def label_tag(field):
    """
    Outputs the tag for a field's label. This gives more fine-grained
    control over the appearance of the form.

    This exists because a template can't access this directly from a field
    in newforms.
    """
    is_checkbox = is_field_checkbox(field)

    s = '<label for="%s"' % form_field_id(field)

    classes = []

    if field.field.required:
        classes.append("required")

    if is_checkbox:
        classes.append("vCheckboxLabel")

    if classes:
        s += ' class="%s"' % " ".join(classes)

    s += '>%s' % force_unicode(escape(field.label))

    if not is_checkbox:
        s += ':'

    s += '</label>'

    return s


@register.filter
def form_field_id(field):
    """
    Outputs the ID of a field.
    """
    widget = field.field.widget
    id_ = widget.attrs.get('id') or field.auto_id

    if id_:
        return widget.id_for_label(id_)

    return ""


@register.filter
def is_field_checkbox(field):
    """
    Returns whether or not this field is a checkbox (a ```BooleanField''').
    """
    return isinstance(field.field, forms.BooleanField)


@register.filter
def is_checkbox_row(field):
    """Returns whether the field's row is a checkbox-ish row.

    This will return True if rendering a checkbox, radio button, or
    multi-select checkbox.
    """
    return isinstance(field.field.widget, (forms.CheckboxInput,
                                           forms.RadioSelect,
                                           forms.CheckboxSelectMultiple))


@register.filter
def form_field_has_label_first(field):
    """
    Returns whether or not this field should display the label before the
    widget. This is the case in all fields except checkboxes.
    """
    return not is_field_checkbox(field)
