from __future__ import unicode_literals

from django.utils import six
from django.utils.html import escape
from djblets.markdown import markdown_escape, markdown_unescape
from djblets.webapi.resources.mixins.forms import (
    UpdateFormMixin as DjbletsUpdateFormMixin)

from reviewboard.reviews.markdown_utils import (markdown_set_field_escaped,
                                                render_markdown)
from reviewboard.webapi.base import ImportExtraDataError


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

    Clients can also pass ``?include-text-types=<type1>[,<type2>,...]``
    (for GET) or ``include_text_types=<type1>[,<type2>,...]`` (for POST/PUT)
    to return the text fields within special :samp:`{type}_text_fields`
    entries in the resource payload. A special type of "raw" is allowed,
    which will return the text types stored in the database.

    (Note that passing ``?include-text-types=raw`` is equivalent to passing
    ``?include-raw-text-fields=1`` in 2.0.9 and 2.0.10. The latter is
    deprecated.)
    """
    TEXT_TYPE_PLAIN = 'plain'
    TEXT_TYPE_MARKDOWN = 'markdown'
    TEXT_TYPE_HTML = 'html'
    TEXT_TYPE_RAW = 'raw'

    TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN, TEXT_TYPE_HTML)
    SAVEABLE_TEXT_TYPES = (TEXT_TYPE_PLAIN, TEXT_TYPE_MARKDOWN)
    INCLUDEABLE_TEXT_TYPES = TEXT_TYPES + (TEXT_TYPE_RAW,)

    DEFAULT_EXTRA_DATA_TEXT_TYPE = TEXT_TYPE_MARKDOWN

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

        if force_text_type not in self.TEXT_TYPES:
            force_text_type = None

        extra_text_type_fields = dict(
            (extra_text_type, {})
            for extra_text_type in self._get_extra_text_types(obj, **kwargs)
        )

        for field, field_info in six.iteritems(self.fields):
            if not field_info.get('supports_text_types'):
                continue

            get_func = getattr(self, 'get_is_%s_rich_text' % field, None)

            if six.callable(get_func):
                getter = lambda obj, *args: get_func(obj)
            else:
                getter = lambda obj, data, rich_text_field, text_type_field: \
                    getattr(obj, rich_text_field, None)

            self._serialize_text_info(obj, data, extra_text_type_fields,
                                      field, force_text_type, getter)

        if 'extra_data' in data:
            extra_data = data['extra_data']
            all_text_types_extra_data = {}

            if obj.extra_data is None:
                obj.extra_data = {}

            # Work on a copy of extra_data, in case we change it.
            for field, value in six.iteritems(obj.extra_data.copy()):
                if not self.get_extra_data_field_supports_markdown(obj, field):
                    continue

                # If all_text_types_extra_data is empty that implies we have
                # encountered the first field in extra_data which supports
                # markdown. In this case we must initialize the dictionary
                # with the extra text types that should be included in the
                # payload.
                if not all_text_types_extra_data:
                    all_text_types_extra_data = dict(
                        (k, {}) for k in six.iterkeys(extra_text_type_fields)
                    )

                # Note that we assume all custom fields are in Markdown by
                # default. This is to preserve compatibility with older
                # fields. New fields will always have the text_type flag
                # set to the proper value.
                self._serialize_text_info(
                    obj, extra_data, all_text_types_extra_data, field,
                    force_text_type, self._extra_data_rich_text_getter)

            for key, values in six.iteritems(all_text_types_extra_data):
                extra_text_type_fields[key]['extra_data'] = values

        for key, values in six.iteritems(extra_text_type_fields):
            data[key + '_text_fields'] = values

        return data

    def _serialize_text_info(self, obj, data, extra_text_type_fields, field,
                             force_text_type, getter):
        text_type_field = self._get_text_type_field_name(field)
        rich_text_field = self._get_rich_text_field_name(field)

        field_is_rich_text = getter(obj, data, rich_text_field,
                                    text_type_field)
        assert field_is_rich_text is not None, \
            'No value for field "%s" found in %r' % (rich_text_field, obj)

        if field_is_rich_text:
            field_text_type = self.TEXT_TYPE_MARKDOWN
        else:
            field_text_type = self.TEXT_TYPE_PLAIN

        value = data.get(field)

        if force_text_type:
            data[text_type_field] = force_text_type

            if value is not None:
                data[field] = self._normalize_text(
                    value, field_is_rich_text, force_text_type)
        else:
            data[text_type_field] = field_text_type

        for extra_text_type in extra_text_type_fields:
            if extra_text_type == self.TEXT_TYPE_RAW:
                norm_extra_text_type = field_text_type
                norm_extra_value = value
            else:
                norm_extra_text_type = extra_text_type
                norm_extra_value = self._normalize_text(
                    value, field_is_rich_text, extra_text_type)

            extra_text_type_fields[extra_text_type].update({
                field: norm_extra_value,
                text_type_field: norm_extra_text_type,
            })

    def serialize_text_type_field(self, obj, request=None, **kwargs):
        return None

    def can_import_extra_data_field(self, obj, field):
        """Returns whether a particular field in extra_data can be imported.

        If an extra_data field is marked as supporting rich text, we'll skip
        importing it through normal means. Instead, it will be handled
        separately later.
        """
        return not self.get_extra_data_field_supports_markdown(obj, field)

    def get_extra_data_field_supports_markdown(self, obj, key):
        """Returns whether a particular field in extra_data supports Markdown.

        If the field supports Markdown text, the value will be normalized
        based on the requested ?force-text-type= parameter.
        """
        return False

    def _get_extra_text_types(self, obj, request=None, **kwargs):
        """Returns any extra text types that should be included in the payload.

        This will return the list of extra text types that can be included,
        filtering the list by those that are supported.

        It also checks for the older ``?include-raw-text-fields=1`` option,
        which is the same as using ``?include-text-types=raw``.
        """
        extra_text_types = set()

        if request:
            if request.method == 'GET':
                include_types = request.GET.get('include-text-types')
                include_raw_text = request.GET.get('include-raw-text-fields')
            else:
                include_types = request.POST.get('include_text_types')
                include_raw_text = request.POST.get('include_raw_text_fields')

            if include_raw_text in ('1', 'true'):
                extra_text_types.add(self.TEXT_TYPE_RAW)

            if include_types:
                extra_text_types.update([
                    text_type
                    for text_type in include_types.split(',')
                    if text_type in self.INCLUDEABLE_TEXT_TYPES
                ])

        return extra_text_types

    def _normalize_text(self, text, field_is_rich_text, force_text_type):
        """Normalizes text to the proper format.

        This considers the requested text format, and whether or not the
        value should be set for rich text.
        """
        assert force_text_type

        if text is not None:
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
        """Normalize Markdown-capable text fields that are being saved.

        Args:
            obj (django.db.models.Model):
                The object containing Markdown-capable fields to modify.

            text_field (unicode):
                The key from ``kwargs`` containing the new value for the
                text fields.

            rich_text_field_name (unicode, optional):
                The name of the boolean field on ``obj`` representing the
                rich text state.

                If not provided, a name will be generated based on the value
                of ``text_field`` (``'rich_text'`` if ``text_field`` is
                ``'text'``, or :samp:`{text_field}_rich_text` otherwise).

            text_type_field_name (unicode, optional):
                The key from ``kwargs`` containing the text type.

                If not provided, a name will be generated based on the value
                of ``text_field`` (``'text_type'`` if ``text_field`` is
                ``'text'``, or :samp:`{text_field}_text_type` otherwise).

            text_model_field (unicode, optional):
                The name of the text field on ``obj``.

                If not provided, ``text_field`` will be used for the value.

            **kwargs (dict):
                Any fields passed by the client. These should be values
                corresponding to ``text_type_field_name`` and ``text_field``
                in here.

                This may also contain a legacy value of ``'text_type'``,
                which will be used if ``text_type_field_name`` is not present.

        Returns:
            set:
            The fields on ``obj`` that were set based on the request.
        """
        modified_fields = set()

        if not text_model_field:
            text_model_field = text_field

        if not text_type_field_name:
            text_type_field_name = self._get_text_type_field_name(text_field)

        if not rich_text_field_name:
            rich_text_field_name = self._get_rich_text_field_name(text_field)

        old_rich_text = getattr(obj, rich_text_field_name, None)
        text = kwargs.get(text_field)

        if text is not None:
            setattr(obj, text_model_field, text.strip())
            modified_fields.add(text_model_field)

        legacy_text_type = kwargs.get('text_type')
        text_type = kwargs.get(text_type_field_name, legacy_text_type)

        if text_type is not None:
            rich_text = (text_type == self.TEXT_TYPE_MARKDOWN)

            setattr(obj, rich_text_field_name, rich_text)
            modified_fields.add(rich_text_field_name)

            # If the caller has changed the text type for this field, but
            # hasn't provided a new field value, then we will need to update
            # the affected field's existing contents by escaping or
            # unescaping.
            if rich_text != old_rich_text and text is None:
                markdown_set_field_escaped(obj, text_model_field, rich_text)
                modified_fields.add(text_model_field)
        elif old_rich_text:
            # The user didn't specify rich-text, but the object may be set
            # for rich-text, in which case we'll need to pre-escape the text
            # field.
            if text is not None:
                markdown_set_field_escaped(obj, text_model_field,
                                           old_rich_text)
                modified_fields.add(text_model_field)

        return modified_fields

    def set_extra_data_text_fields(self, obj, text_field, extra_fields,
                                   **kwargs):
        """Normalize Markdown-capable text fields in extra_data.

        This will check if any Markdown-capable text fields in extra_data
        have been changed (either by changing the text or the text type),
        and handle the saving of the text and type.

        This works just like :py:meth:`set_text_fields`, but specially handles
        how things are stored in extra_data (text_type vs. rich_text fields,
        possible lack of presence of a text_type field, etc.).

        Args:
            obj (django.db.models.Model):
                The object containing Markdown-capable fields to modify.

            text_field (unicode):
                The key from ``kwargs`` containing the new value for the
                text fields.

            extra_fields (dict):
                Fields passed to the API resource that aren't natively handled
                by that resource. These may contain ``extra_data.``-prefixed
                keys.

            **kwargs (dict):
                Any fields passed by the client. This may be checked for a
                legacy ``text_type`` field.

        Returns:
            set:
            The keys in ``extra_data`` that were set based on the request.
        """
        modified_fields = set()

        text_type_field = self._get_text_type_field_name(text_field)
        extra_data = obj.extra_data
        extra_data_text_field = 'extra_data.' + text_field
        extra_data_text_type_field = 'extra_data.' + text_type_field

        if extra_data_text_field in extra_fields:
            # This field was updated in this request. Make sure it's
            # stripped.
            extra_data[text_field] = \
                extra_fields[extra_data_text_field].strip()
            modified_fields.add(text_field)
        elif extra_data_text_type_field not in extra_fields:
            # Nothing about this field has changed, so bail.
            return modified_fields

        old_text_type = extra_data.get(text_type_field)
        text_type = extra_fields.get(extra_data_text_type_field,
                                     kwargs.get('text_type'))

        if text_type is not None:
            if old_text_type is None:
                old_text_type = self.DEFAULT_EXTRA_DATA_TEXT_TYPE

            # If the caller has changed the text type for this field, but
            # hasn't provided a new field value, then we will need to update
            # the affected field's existing contents by escaping or
            # unescaping.
            if (text_type != old_text_type and
                extra_data_text_field not in extra_fields):
                markdown_set_field_escaped(
                    extra_data, text_field,
                    text_type == self.TEXT_TYPE_MARKDOWN)
                modified_fields.add(text_field)
        elif old_text_type:
            # The user didn't specify a text type, but the object may be set
            # for Markdown, in which case we'll need to pre-escape the text
            # field.
            if extra_data_text_field in extra_fields:
                markdown_set_field_escaped(
                    extra_data, text_field,
                    old_text_type == self.TEXT_TYPE_MARKDOWN)
                modified_fields.add(text_field)

        # Ensure we have a text type set for this field. If one wasn't
        # provided or set above, we'll set it to the default now.
        extra_data[text_type_field] = \
            text_type or self.DEFAULT_EXTRA_DATA_TEXT_TYPE
        modified_fields.add(text_type_field)

        return modified_fields

    def _get_text_type_field_name(self, text_field_name):
        if text_field_name == 'text':
            return 'text_type'
        else:
            return '%s_text_type' % text_field_name

    def _get_rich_text_field_name(self, text_field_name):
        if text_field_name == 'text':
            return 'rich_text'
        else:
            return '%s_rich_text' % text_field_name

    def _extra_data_rich_text_getter(self, obj, data, rich_text_field,
                                     text_type_field):
        text_type = data.get(text_type_field,
                             self.DEFAULT_EXTRA_DATA_TEXT_TYPE)

        return text_type == self.TEXT_TYPE_MARKDOWN


class UpdateFormMixin(DjbletsUpdateFormMixin):
    """A mixin for providing the ability to create and update using a form.

    A WebAPIResource class using this mixin must set the :py:attr:`form_class`
    attribute to a :py:class:`ModelForm` instance that corresponds to the model
    being updated.

    Classes using this mixin can provide methods of the form
    ``parse_<field_name>_field`` to do parsing of form data before it is passed
    to the form. These methods may return either a single value or a list (in
    the case where the corresponding field expects a list of values, such as a
    :py:class:`django.forms.ModelMultipleChoiceField`).

    The :py:meth:`create_form` and :py:meth:`save_form` methods should be used
    for creating new form instances and saving them. A form created this way
    can be given an optional instance argument to allow for updating the
    instance. Any fields missing from data (but appearing in the
    :py:class:`form_class`'s :py:attr:`fields` attribute) will be copied over
    from the instance.
    """

    def handle_form_request(self, **kwargs):
        """Handle an HTTP request for creating or updating through a form.

        This simply wraps the parent method and handles
        :py:class:`~reviewboard.webapi.base.ImportExtraDataError` exceptions
        during form save.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent method.

        Returns:
            tuple or django.http.HttpResponse:
            The response to send back to the client.
        """
        try:
            return super(UpdateFormMixin, self).handle_form_request(**kwargs)
        except ImportExtraDataError as e:
            return e.error_payload

    def save_form(self, form, save_kwargs, extra_fields=None, **kwargs):
        """Save the form and extra data.

        Args:
            form (django.forms.ModelForm):
                The form to save.

            save_kwargs (dict):
                Additional keyword arguments to pass to the
                :py:class:`ModelForm.save() <django.forms.ModelForm.save>`.

            extra_fields (dict, optional):
                The extra data to save on the object. These should be key-value
                pairs in the form of ``extra_data.key = value``.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.

        Returns:
            django.db.models.Model:
            The saved model instance.

        Raises:
            reviewboard.webapi.base.ImportExtraDataError:
                Extra data failed to import. The form will not be saved.
        """
        if save_kwargs:
            save_kwargs = save_kwargs.copy()
        else:
            save_kwargs = {}

        save_kwargs['commit'] = False

        instance = super(UpdateFormMixin, self).save_form(
            form=form,
            save_kwargs=save_kwargs,
            **kwargs)

        if extra_fields:
            if not instance.extra_data:
                instance.extra_data = {}

            self.import_extra_data(instance, instance.extra_data, extra_fields)

        instance.save()
        form.save_m2m()

        return instance
