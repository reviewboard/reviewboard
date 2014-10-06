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

    Clients can pass ``?force-text-type=`` with a value of ``plain`` or
    ``markdown`` to provide those text fields in the requested format.

    When ``markdown`` is specified, the Markdown text fields will return valid
    Markdown content, escaping if necessary.

    When ``plain`` is specified, plain text will be returned instead. If
    the content was in Markdown before, this will unescape the content.
    """
    TEXT_TYPE_PLAIN = 'plain'
    TEXT_TYPE_MARKDOWN = 'markdown'
    TEXT_TYPE_HTML = 'html'

    TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN, TEXT_TYPE_HTML)
    SAVEABLE_TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN)

    def serialize_text_type_field(self, obj, request=None, **kwargs):
        return self.get_requested_text_type(obj, request)

    def serialize_extra_data_field(self, obj, **kwargs):
        extra_data = {}

        for key, value in six.iteritems(obj.extra_data):
            if value and self.get_extra_data_field_supports_markdown(obj, key):
                extra_data[key] = self.normalize_text(obj, value, **kwargs)
            else:
                extra_data[key] = value

        return extra_data

    def get_extra_data_field_supports_markdown(self, obj, key):
        """Returns whether a particular field in extra_data supports Markdown.

        If the field supports Markdown text, the value will be normalized
        based on the requested ?force-text-type= parameter.
        """
        return False

    def get_requested_text_type(self, obj, request=None):
        """Returns the text type requested by the user.

        If the user did not request a text type, or a valid text type,
        this will fall back to the proper type for the given object.
        """
        if request:
            if request.method == 'GET':
                text_type = request.GET.get('force-text-type')
            else:
                text_type = request.POST.get('force_text_type')
        else:
            text_type = None

        if not text_type or text_type not in self.TEXT_TYPES:
            if obj.rich_text:
                text_type = self.TEXT_TYPE_MARKDOWN
            else:
                text_type = self.TEXT_TYPE_PLAIN

        return text_type

    def normalize_text(self, obj, text, request=None, **kwargs):
        """Normalizes text to the proper format.

        This considers the requested text format, and whether or not the
        object is set for having rich text.
        """
        text_type = self.get_requested_text_type(obj, request)

        if text_type == self.TEXT_TYPE_PLAIN and obj.rich_text:
            text = markdown_unescape(text)
        elif text_type == self.TEXT_TYPE_MARKDOWN and not obj.rich_text:
            text = markdown_escape(text)
        elif text_type == self.TEXT_TYPE_HTML:
            if obj.rich_text:
                text = render_markdown(text)
            else:
                text = escape(text)

        return text

    def normalize_markdown_fields(self, obj, text_fields, old_rich_text,
                                  model_field_map={}, **kwargs):
        """Normalizes Markdown-capable text fields that are being saved."""
        if 'text_type' in kwargs:
            rich_text = (kwargs['text_type'] == self.TEXT_TYPE_MARKDOWN)

            # If the caller has changed the rich_text setting, we will need to
            # update any affected fields we already have stored that weren't
            # changed in this request by escaping or unescaping their
            # contents.
            if rich_text != old_rich_text:
                for text_field in text_fields:
                    if text_field not in kwargs:
                        model_field = \
                            model_field_map.get(text_field, text_field)
                        markdown_set_field_escaped(obj, model_field, rich_text)
        elif old_rich_text:
            # The user didn't specify rich-text, but the object may be set for
            # for rich-text, in which case we'll need to pre-escape any text
            # fields that came in.
            for text_field in text_fields:
                if text_field in kwargs:
                    model_field = model_field_map.get(text_field, text_field)
                    markdown_set_field_escaped(obj, model_field, old_rich_text)
