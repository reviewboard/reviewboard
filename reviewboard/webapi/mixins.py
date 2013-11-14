from __future__ import unicode_literals

from reviewboard.reviews.markdown_utils import markdown_set_field_escaped


class MarkdownFieldsMixin(object):
    """Mixes in common logic for Markdown text fields."""
    def normalize_markdown_fields(self, obj, text_fields, old_rich_text,
                                  model_field_map={}, **kwargs):
        if 'rich_text' in kwargs:
            rich_text = kwargs['rich_text']

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
