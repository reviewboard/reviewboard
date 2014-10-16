from __future__ import unicode_literals

from django.utils import six
from django.utils.html import escape

from reviewboard.reviews.markdown_utils import (markdown_escape,
                                                markdown_set_field_escaped,
                                                markdown_unescape,
                                                render_markdown)


class MarkdownFieldsMixin(object):
    """Mixes in common logic for Markdown text fields.

    Any resource implementing this is assumed to have at least one
    Markdown-capable text field.

    Clients can pass ``?force-text-type=`` (for GET) or ``force_text_type=``
    (for POST/PUT) with a value of ``plain``, ``markdown`` or ``html`` to
    return the given text fields in the payload using the requested format.

    When ``markdown`` is specified, the Markdown text fields will return valid
    Markdown content, escaping if necessary.

    When ``plain`` is specified, plain text will be returned instead. If
    the content was in Markdown before, this will unescape the content.

    When ``html`` is specified, the content will be transformed into HTML
    suitable for display.

    Clients can also pass ``?include-raw-text-fields=1`` (for GET) or
    ``include_raw_text_fields=`` (for POST/PUT) to return the raw fields
    within a special ``raw_text_fields`` entry in the resource payload.
    """
    TEXT_TYPE_PLAIN = 'plain'
    TEXT_TYPE_MARKDOWN = 'markdown'
    TEXT_TYPE_HTML = 'html'

    TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN, TEXT_TYPE_HTML)
    SAVEABLE_TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN)

    def serialize_object(self, obj, *args, **kwargs):
        """Serializes the object, transforming text fields.

        This is a specialization of serialize_object that transforms any
        text fields that support text types. It also handles attaching
        the raw text to the payload, on request.
        """
        data = super(MarkdownFieldsMixin, self).serialize_object(
            obj, *args, **kwargs)

        request = kwargs.get('request')

        if not request:
            force_text_type = None
        elif request.method == 'GET':
            force_text_type = request.GET.get('force-text-type')
        else:
            force_text_type = request.POST.get('force_text_type')

        if force_text_type in self.TEXT_TYPES:
            include_raw_text_fields = \
                self._get_include_raw_text_fields(obj, **kwargs)
        else:
            force_text_type = None
            include_raw_text_fields = False

        raw_fields = {}

        for field, field_info in six.iteritems(self.fields):
            if not field_info.get('supports_text_types'):
                continue

            get_func = getattr(self, 'get_is_%s_rich_text' % field, None)

            if six.callable(get_func):
                getter = lambda obj, *args: get_func(obj)
            else:
                getter = lambda obj, data, field, default: \
                    getattr(obj, field, default)

            self._serialize_text_info(obj, data, raw_fields, field,
                                      force_text_type,
                                      include_raw_text_fields,
                                      getter)

        if 'extra_data' in data:
            raw_extra_data = {}
            extra_data = data['extra_data']

            for field, value in six.iteritems(obj.extra_data):
                if not self.get_extra_data_field_supports_markdown(obj, field):
                    continue

                self._serialize_text_info(
                    obj, extra_data, raw_extra_data, field, force_text_type,
                    include_raw_text_fields,
                    lambda obj, data, field, default: data.get(field, default))

        if include_raw_text_fields:
            data['raw_text_fields'] = raw_fields

        return data

    def _serialize_text_info(self, obj, data, raw_data, field,
                             force_text_type, include_raw_text_fields,
                             getter, rich_text_field=None,
                             default_is_rich_text=None):
        if field == 'text':
            text_type_field = 'text_type'
            rich_text_field = rich_text_field or 'rich_text'
        else:
            text_type_field = '%s_text_type' % field
            rich_text_field = rich_text_field or '%s_rich_text' % field

        field_is_rich_text = getter(obj, data, rich_text_field,
                                    default_is_rich_text)
        assert field_is_rich_text is not None, \
            'No value for field "%s" found in %r' % (rich_text_field, obj)

        if force_text_type:
            data[text_type_field] = force_text_type
            value = data.get(field)

            if value is not None:
                data[field] = self._normalize_text(
                    data[field], field_is_rich_text, force_text_type)

            if include_raw_text_fields:
                raw_data[field] = value
                text_types_data = raw_data
            else:
                text_types_data = None
        else:
            text_types_data = data

        if text_types_data is not None:
            if field_is_rich_text:
                text_types_data[text_type_field] = self.TEXT_TYPE_MARKDOWN
            else:
                text_types_data[text_type_field] = self.TEXT_TYPE_PLAIN

    def serialize_text_type_field(self, obj, request=None, **kwargs):
        return None

    def get_extra_data_field_supports_markdown(self, obj, key):
        """Returns whether a particular field in extra_data supports Markdown.

        If the field supports Markdown text, the value will be normalized
        based on the requested ?force-text-type= parameter.
        """
        return False

    def _get_include_raw_text_fields(self, obj, request=None, **kwargs):
        """Returns whether raw text fields should be returned in the payload.

        If ``?include-raw-text-fields=1`` (for GET) or
        ``include_raw_text_fields=`` (for POST/PUT) is passed, this will
        return True. Otherwise, it will return False.
        """
        include_raw_text = False

        if request:
            if request.method == 'GET':
                include_raw_text = request.GET.get('include-raw-text-fields')
            else:
                include_raw_text = request.POST.get('include_raw_text_fields')

        return include_raw_text in ('1', 'true')

    def _normalize_text(self, text, field_is_rich_text, force_text_type):
        """Normalizes text to the proper format.

        This considers the requested text format, and whether or not the
        value should be set for rich text.
        """
        assert force_text_type

        if force_text_type == self.TEXT_TYPE_PLAIN and field_is_rich_text:
            text = markdown_unescape(text)
        elif (force_text_type == self.TEXT_TYPE_MARKDOWN and
              not field_is_rich_text):
            text = markdown_escape(text)
        elif force_text_type == self.TEXT_TYPE_HTML:
            if field_is_rich_text:
                text = render_markdown(text)
            else:
                text = escape(text)

        return text

    def set_text_fields(self, obj, text_field,
                        rich_text_field_name=None,
                        text_type_field_name=None,
                        text_model_field=None,
                        **kwargs):
        """Normalizes Markdown-capable text fields that are being saved."""
        if not text_model_field:
            text_model_field = text_field

        if not text_type_field_name:
            if text_field == 'text':
                text_type_field_name = 'text_type'
            else:
                text_type_field_name = '%s_text_type' % text_field

        if not rich_text_field_name:
            if text_field == 'text':
                rich_text_field_name = 'rich_text'
            else:
                rich_text_field_name = '%s_rich_text' % text_field

        old_rich_text = getattr(obj, rich_text_field_name, None)

        if text_field in kwargs:
            setattr(obj, text_model_field, kwargs[text_field].strip())

        if text_type_field_name in kwargs or 'text_type' in kwargs:
            text_type = kwargs.get(text_type_field_name,
                                   kwargs.get('text_type'))
            rich_text = (text_type == self.TEXT_TYPE_MARKDOWN)

            setattr(obj, rich_text_field_name, rich_text)

            # If the caller has changed the text type for this field, but
            # hasn't provided a new field value, then we will need to update
            # the affected field's existing contents by escaping or
            # unescaping.
            if rich_text != old_rich_text and text_field not in kwargs:
                markdown_set_field_escaped(obj, text_model_field,
                                           rich_text)
        elif old_rich_text:
            # The user didn't specify rich-text, but the object may be set for
            # for rich-text, in which case we'll need to pre-escape the text
            # field.
            if text_field in kwargs:
                markdown_set_field_escaped(obj, text_model_field,
                                           old_rich_text)
