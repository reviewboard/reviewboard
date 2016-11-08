from __future__ import unicode_literals

import logging

from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.functional import cached_property
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe
from django.utils.six.moves.html_parser import HTMLParser
from djblets.markdown import iter_markdown_lines

from reviewboard.diffviewer.diffutils import get_line_changed_regions
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.reviews.markdown_utils import (is_rich_text_default_for_user,
                                                normalize_text_for_edit,
                                                render_markdown)


_all_fields = {}
_fieldsets = SortedDict()
_populated = False


class BaseReviewRequestFieldSet(object):
    """Base class for sets of review request fields.

    A fieldset stores a list of fields that are rendered on the review
    request page. They may contain default fields, and new fields can be
    added or removed.

    Review Board provides three main fieldsets: "main", "info", and
    "reviewers". Others can be added by subclassing and registering
    through ``register_review_request_fieldset``.
    """
    fieldset_id = None
    label = None
    show_required = False
    field_classes = None
    tag_name = None

    def __init__(self, review_request_details):
        self.review_request_details = review_request_details

    @classmethod
    def is_empty(cls):
        """Returns whether the fieldset is empty.

        A fieldset is empty if there are no field classes registered.
        An empty fieldset will not be displayed on the page.
        """
        return not cls.field_classes

    @classmethod
    def add_field(cls, field_cls):
        """Adds a field class to this fieldset.

        The field will be rendered inside this fieldset on the page.

        A given field class can only be in one fieldset. Its ``field_id``
        must be unique.
        """
        _register_field(field_cls)
        cls.field_classes.append(field_cls)

    @classmethod
    def remove_field(cls, field_cls):
        """Removes a field class from this fieldset.

        The field class must have been previously added to this fieldset.
        """
        field_id = field_cls.field_id

        try:
            cls.field_classes.remove(field_cls)
            del _all_fields[field_id]
        except KeyError:
            logging.error('Failed to unregister unknown review request '
                          'field "%s"',
                          field_id)
            raise KeyError('"%s" is not a registered review request field'
                           % field_id)


class BaseReviewRequestField(object):
    """Base class for a field on a review request.

    A field is responsible for displaying data from a review request,
    handling any editing requirements if necessary, recording changes
    in the ChangeDescription, and rendering those changes.

    Each field must have its own unique ``field_id``. This ID will be used
    when looking up or storing the field's value.

    It is recommended that fields provided by extensions prefix their
    field ID with some sort of identifier for the extension or the vendor.

    Creating a new field requires subclassing BaseReviewRequestField and
    overriding any fields or functions necessary. Its class must then be
    added to a fieldset.

    A field will be instantiated with either a ReviewRequest or a
    ReviewRequestDraft, depending on what is being edited. This is stored
    in ``review_request_details``. Functions should optimistically fetch
    values from that, if possible. They can call ``get_review_request()``
    on ``review_request_details`` to fetch the actual ReviewRequest.

    If the function takes a ``review_request_details`` parameter, it must
    use that instead.
    """
    field_id = None
    label = None
    is_editable = False
    is_required = False
    default_css_classes = set()
    change_entry_renders_inline = True
    model = None

    can_record_change_entry = property(lambda self: self.is_editable)

    def __init__(self, review_request_details, request=None):
        self.review_request_details = review_request_details
        self.request = request

    @property
    def value(self):
        """Returns the value loaded from the database.

        This will fetch the value with the associated ReviewRequest or
        ReviewRequestDraft, and then cache it for future lookups.
        """
        if not hasattr(self, '_value'):
            self._value = self.load_value(self.review_request_details)

        return self._value

    def has_value_changed(self, old_value, new_value):
        """Returns whether the value has changed.

        By default, it performs an inequality check on the values. This
        can be overridden to perform more specialized checks.
        """
        return old_value != new_value

    def record_change_entry(self, changedesc, old_value, new_value):
        """Records information on the changed values in a ChangeDescription.

        By default, the values are stored as-is along with the field ID.
        This can be overridden to perform more specialized storage.
        """
        changedesc.record_field_change(self.field_id, old_value, new_value)

    def serialize_change_entry(self, changedesc):
        """Serialize a change entry for public consumption.

        This will output a version of the change entry for use in the API.
        It can be the same content stored in the
        :py:class:`~reviewboard.changedescs.models.ChangeDescription`, but
        does not need to be.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description whose field is to be serialized.

        Returns:
            dict:
            An appropriate serialization for the field.
        """
        field_info = changedesc.fields_changed[self.field_id]

        if self.model:
            return self.serialize_change_entry_for_model_list(field_info)
        else:
            return self.serialize_change_entry_for_singleton(field_info)

    def serialize_change_entry_for_model_list(self, field_info):
        """Return the change entry for a list of models.

        Args:
            field_info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            dict:
            A mapping of each key present in ``field_info`` to its list of
            model instances.
        """
        pks = [
            value[2]
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
            for value in field_info[key]
        ]
        pk_to_objects = dict([
            (obj.pk, obj)
            for obj in self.model.objects.filter(pk__in=pks)
        ])

        return dict([
            (key, [
                pk_to_objects[value[2]]
                for value in field_info[key]
            ])
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        ])

    def serialize_change_entry_for_singleton(self, field_info):
        """Return the change entry for a singleton.

        Singleton fields (e.g., summaries) are stored in
        :py:class:`~reviewboard.changedescs.models.ChangeDescription`\s as
        a list with a single element.

        Args:
            field_info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            dict:
            A mapping of each key in ``field_info`` to a single value.
        """
        return dict([
            (key, field_info[key][0])
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        ])

    def serialize_change_entry_for_list(self, field_info):
        """Return the change entry for a list of plain data.

        Args:
            field_info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            dict:
            A mapping of each key in ``field_info`` to a list of values.
        """
        return dict([
            (key, [
                value[0]
                for value in field_info[key]
            ])
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        ])

    def get_change_entry_sections_html(self, info):
        """Returns sections of change entries with titles and rendered HTML.

        By default, this just returns a single section for the field, with
        the field's title and rendered change HTML.

        Subclasses can override this to provide more information.
        """
        return [{
            'title': self.label,
            'rendered_html': mark_safe(self.render_change_entry_html(info)),
        }]

    def render_change_entry_html(self, info):
        """Renders a change entry to HTML.

        By default, this returns a simple "changed from X to Y" using the old
        and new values. This can be overridden to generate more specialized
        output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Subclasses can override ``render_change_entry_value_html`` to
        change how the value itself will be rendered in the string.
        """
        old_value = ''
        new_value = ''

        if 'old' in info:
            old_value = info['old'][0]

        if 'new' in info:
            new_value = info['new'][0]

        s = ['<table class="changed">']

        if old_value:
            s.append(self.render_change_entry_removed_value_html(
                info, old_value))

        if new_value:
            s.append(self.render_change_entry_added_value_html(
                info, new_value))

        s.append('</table>')

        return ''.join(s)

    def render_change_entry_added_value_html(self, info, value):
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            return ('<tr class="new-value"><th class="marker">+</th>'
                    '<td class="value">%s</td></tr>' % value_html)
        else:
            return ''

    def render_change_entry_removed_value_html(self, info, value):
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            return ('<tr class="old-value"><th class="marker">-</th>'
                    '<td class="value">%s</td></tr>' % value_html)
        else:
            return ''

    def render_change_entry_value_html(self, info, value):
        """Renders the value for a change description string to HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.
        """
        return escape(six.text_type(value or ''))

    def load_value(self, review_request_details):
        """Loads a value from the review request or draft.

        By default, this loads the value as-is from the extra_data field.
        This can be overridden if you need to deserialize the value in some
        way.

        This must use ``review_request_details`` instead of
        ``self.review_request_details``.
        """
        return review_request_details.extra_data.get(self.field_id)

    def save_value(self, value):
        """Saves the value in the review request or draft.

        By default, this saves the value as-is in the extra_data field.
        This can be overridden if you need to serialize the value in some
        way.
        """
        self.review_request_details.extra_data[self.field_id] = value

    def propagate_data(self, review_request_details):
        """Propagate data in from source review request or draft.

        By default, this loads only the field's value from a source review
        request or draft and saves it as-is into the review request or draft
        associated with the field. This can be overridden if you need to
        propagate additional data elements.

        This method is preferable to explictly calling :py:meth:`load_value`
        and :py:meth:`save_value` in series to propagate data from a source
        into a field, because it allows for copying additional data elements
        beyond only the field's value.

        This function must use the ``review_request_details`` parameter instead
        of the :py:attr:`review_request_details` attribute on the field.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details):
                The source review request or draft whose data is to be
                propagated.
        """
        self.save_value(self.load_value(review_request_details))

    def render_value(self, value):
        """Renders the value in the field.

        By default, this converts to text and escapes it. This can be
        overridden if you need to render it in a more specific way.

        This must use ``value`` instead of ``self.value``.
        """
        return escape(six.text_type(value or ''))

    def should_render(self, value):
        """Returns whether the field should be rendered.

        By default, the field is always rendered, but this can be overridden
        if you only want to show under certain conditions (such as if it has
        a value).

        This must use ``value`` instead of ``self.value``.
        """
        return True

    def get_css_classes(self):
        """Returns the list of CSS classes to apply to the element.

        By default, this will include the contents of ``default_css_classes``,
        and ``required`` if it's a required field.

        This can be overridden to provide additional CSS classes, if they're
        not appropraite for ``default_css_classes``.
        """
        css_classes = set(self.default_css_classes)

        if self.is_required:
            css_classes.add('required')

        return css_classes

    def get_data_attributes(self):
        """Returns any data attributes to include in the element.

        By default, this returns nothing.
        """
        return {}

    def as_html(self):
        """Returns the field rendered as HTML.

        By default, this just calls ``render_value`` with the value
        from the database.
        """
        return self.render_value(self.value)


class BaseEditableField(BaseReviewRequestField):
    """Base class for an editable field.

    This simply marks the field as editable.
    """
    default_css_classes = ['editable']
    is_editable = True


class BaseCommaEditableField(BaseEditableField):
    """Base class for an editable comma-separated list of values.

    This is used for dealing with lists of items that appear
    comma-separated in the UI. It works with stored lists of content
    on the review request or draft, and on the ChangeDescription.

    Subclasses can override this to provide specialized rendering
    on a per-item-basis. That's useful for showing links to items,
    for example.
    """
    default_css_classes = ['editable', 'comma-editable']
    order_matters = False

    one_line_per_change_entry = True

    def has_value_changed(self, old_value, new_value):
        """Returns whether two values have changed.

        If ``order_matters`` is set to ``True``, this will do a strict
        list comparison. Otherwise, it will compare the items in both
        lists without caring about the ordering.
        """
        if self.order_matters:
            return old_value != new_value
        else:
            return set(old_value or []) != set(new_value or [])

    def serialize_change_entry(self, changedesc):
        """Serialize a change entry for public consumption.

        This will output a version of the change entry for use in the API.
        It can be the same content stored in the
        :py:class:`~reviewboard.changedescs.models.ChangeDescription`, but
        does not need to be.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description whose field is to be serialized.

        Returns:
            dict:
            An appropriate serialization for the field.
        """
        field_info = changedesc.fields_changed[self.field_id]

        if self.model:
            return self.serialize_change_entry_for_model_list(field_info)
        else:
            return self.serialize_change_entry_for_list(field_info)

    def render_value(self, values):
        """Renders the list of items.

        This will call out to ``render_item`` for every item. The list
        of rendered items will be separated by a comma and a space.
        """
        return ', '.join([
            self.render_item(value)
            for value in values
        ])

    def render_item(self, item):
        """Renders an item from the list.

        By default, this will convert the item to text and then escape it.
        """
        return escape(six.text_type(item or ''))

    def render_change_entry_html(self, info):
        """Renders a change entry to HTML.

        By default, this returns HTML containing a list of removed items,
        and a list of added items. This can be overridden to generate
        more specialized output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.
        """
        s = ['<table class="changed">']

        if 'removed' in info:
            values = info['removed']

            if self.one_line_per_change_entry:
                s += [
                    self.render_change_entry_removed_value_html(info, [value])
                    for value in values
                ]
            else:
                s.append(self.render_change_entry_removed_value_html(
                    info, values))

        if 'added' in info:
            values = info['added']

            if self.one_line_per_change_entry:
                s += [
                    self.render_change_entry_added_value_html(info, [value])
                    for value in values
                ]
            else:
                s.append(self.render_change_entry_added_value_html(
                    info, values))

        s.append('</table>')

        return ''.join(s)

    def render_change_entry_value_html(self, info, values):
        """Renders a list of items for change description HTML.

        By default, this will call ``render_change_entry_item_html`` for every
        item in the list. The list of rendered items will be separated by a
        comma and a space.
        """
        return ', '.join([
            self.render_change_entry_item_html(info, item)
            for item in values
        ])

    def render_change_entry_item_html(self, info, item):
        """Renders an item for change description HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.
        """
        return escape(six.text_type(item[0]))


class BaseTextAreaField(BaseEditableField):
    """Base class for a multi-line text area field.

    The text area can take either plain text or Markdown text. By default,
    Markdown is supported, but this can be changed by setting
    ``enable_markdown`` to ``False``.
    """
    default_css_classes = ['editable', 'field-text-area']
    enable_markdown = True
    always_render_markdown = False
    tag_name = 'pre'

    @cached_property
    def text_type_key(self):
        """Return the text type key for the ``extra_data`` dictionary."""
        if self.field_id == 'text':
            return 'text_type'
        else:
            return '%s_text_type' % self.field_id

    def is_text_markdown(self, value):
        """Returns whether the text is in Markdown format.

        This can be overridden if the field needs to check something else
        to determine if the text is in Markdown format.
        """
        text_type = self.review_request_details.extra_data.get(
            self.text_type_key, 'plain')

        return text_type == 'markdown'

    def propagate_data(self, review_request_details):
        """Propagate data in from source review request or draft.

        In addition to the value propagation handled by the base class, this
        copies the text type details from a source review request or draft and
        saves it as-is into the review request or draft associated with the
        field.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details):
                The source review request or draft whose data is to be
                propagated.
        """
        super(BaseTextAreaField, self).propagate_data(review_request_details)

        source_text_type = review_request_details.extra_data.get(
            self.text_type_key, None)

        if source_text_type is not None:
            self.review_request_details.extra_data[self.text_type_key] = \
                source_text_type

    def get_css_classes(self):
        """Returns the list of CSS classes.

        If Markdown is enabled, and the text is in Markdown format,
        this will add a "rich-text" field.
        """
        css_classes = super(BaseTextAreaField, self).get_css_classes()

        if (self.enable_markdown and self.value and
            (self.should_render_as_markdown(self.value) or
             (self.request.user and
              is_rich_text_default_for_user(self.request.user)))):
            css_classes.add('rich-text')

        return css_classes

    def get_data_attributes(self):
        attrs = super(BaseTextAreaField, self).get_data_attributes()

        if self.enable_markdown:
            if self.request:
                user = self.request.user
            else:
                user = None

            attrs.update({
                'allow-markdown': True,
                'raw-value': normalize_text_for_edit(
                    user, self.value,
                    self.should_render_as_markdown(self.value)),
            })

        return attrs

    def render_value(self, text):
        """Returns the value of the field.

        If Markdown is enabled, and the text is not in Markdown format,
        the text will be escaped.
        """
        text = text or ''

        if self.should_render_as_markdown(text):
            return render_markdown(text)
        else:
            return escape(text)

    def should_render_as_markdown(self, value):
        """Returns whether the text should be rendered as Markdown.

        By default, this checks if the field is set to always render
        any text as Markdown, or if the given text is in Markdown format.
        """
        return self.always_render_markdown or self.is_text_markdown(value)

    def render_change_entry_html(self, info):
        old_value = ''
        new_value = ''

        if 'old' in info:
            old_value = info['old'][0] or ''

        if 'new' in info:
            new_value = info['new'][0] or ''

        old_value = render_markdown(old_value)
        new_value = render_markdown(new_value)
        old_lines = list(iter_markdown_lines(old_value))
        new_lines = list(iter_markdown_lines(new_value))

        differ = MyersDiffer(old_lines, new_lines)

        return ('<table class="diffed-text-area">%s</table>'
                % ''.join(self._render_all_change_lines(differ, old_lines,
                                                        new_lines)))

    def _render_all_change_lines(self, differ, old_lines, new_lines):
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                lines = self._render_change_lines(differ, tag, None, None,
                                                  i1, i2, old_lines)
            elif tag == 'insert':
                lines = self._render_change_lines(differ, tag, None, '+',
                                                  j1, j2, new_lines)
            elif tag == 'delete':
                lines = self._render_change_lines(differ, tag, '-', None,
                                                  i1, i2, old_lines)
            elif tag == 'replace':
                lines = self._render_change_replace_lines(differ, i1, i2,
                                                          j1, j2, old_lines,
                                                          new_lines)
            else:
                raise ValueError('Unexpected tag "%s"' % tag)

            for line in lines:
                yield line

    def _render_change_lines(self, differ, tag, old_marker, new_marker,
                             i1, i2, lines):
        old_marker = old_marker or '&nbsp;'
        new_marker = new_marker or '&nbsp;'

        for i in range(i1, i2):
            line = lines[i]

            yield ('<tr class="%s">'
                   ' <td class="marker">%s</td>'
                   ' <td class="marker">%s</td>'
                   ' <td class="line rich-text">%s</td>'
                   '</tr>'
                   % (tag, old_marker, new_marker, line))

    def _render_change_replace_lines(self, differ, i1, i2, j1, j2,
                                     old_lines, new_lines):
        replace_new_lines = []

        for i, j in zip(range(i1, i2), range(j1, j2)):
            old_line = old_lines[i]
            new_line = new_lines[j]

            parser = HTMLParser()

            old_regions, new_regions = \
                get_line_changed_regions(parser.unescape(strip_tags(old_line)),
                                         parser.unescape(strip_tags(new_line)))

            old_line = highlightregion(old_line, old_regions)
            new_line = highlightregion(new_line, new_regions)

            yield (
                '<tr class="replace-old">'
                ' <td class="marker">~</td>'
                ' <td class="marker">&nbsp;</td>'
                ' <td class="line rich-text">%s</td>'
                '</tr>'
                % old_line)

            replace_new_lines.append(new_line)

        for line in replace_new_lines:
            yield (
                '<tr class="replace-new">'
                ' <td class="marker">&nbsp;</td>'
                ' <td class="marker">~</td>'
                ' <td class="line rich-text">%s</td>'
                '</tr>'
                % line)


def _populate_defaults():
    """Populates the default list of fieldsets and their fields."""
    global _populated

    if not _populated:
        from reviewboard.reviews.builtin_fields import builtin_fieldsets

        _populated = True

        for fieldset_cls in builtin_fieldsets:
            register_review_request_fieldset(fieldset_cls)


def _register_field(field_cls):
    """Registers a field.

    This will check if the field has already been registered before
    adding it. It's called internally when first adding a fieldset, or
    when adding a field to a fieldset.
    """
    field_id = field_cls.field_id

    if field_id in _all_fields:
        raise KeyError(
            '"%s" is already a registered review request field. '
            'Field IDs must be unique across all fieldsets.'
            % field_id)

    _all_fields[field_id] = field_cls


def get_review_request_fields():
    """Returns a list of all registered field classes."""
    _populate_defaults()

    return six.itervalues(_all_fields)


def get_review_request_fieldsets(include_main=False,
                                 include_change_entries_only=False):
    """Returns a list of all registered fieldset classes.

    As an internal optimization, the "main" fieldset can be filtered out,
    to help with rendering the side of the review request page.
    """
    _populate_defaults()

    if include_main and include_change_entries_only:
        return six.itervalues(_fieldsets)
    else:
        excluded_ids = []

        if not include_main:
            excluded_ids.append('main')

        if not include_change_entries_only:
            excluded_ids.append('_change_entries_only')

        return [
            fieldset
            for fieldset in six.itervalues(_fieldsets)
            if fieldset.fieldset_id not in excluded_ids
        ]


def get_review_request_fieldset(fieldset_id):
    """Returns the fieldset with the specified ID.

    If the fieldset could not be found, this will return None.
    """
    _populate_defaults()

    try:
        return _fieldsets[fieldset_id]
    except KeyError:
        return None


def get_review_request_field(field_id):
    """Returns the field with the specified ID.

    If the field could not be found, this will return None.
    """
    _populate_defaults()

    try:
        return _all_fields[field_id]
    except KeyError:
        return None


def register_review_request_fieldset(fieldset):
    """Registers a custom review request fieldset.

    A fieldset ID is considered unique and can only be registered once. A
    KeyError will be thrown if attempting to register a second time.
    """
    _populate_defaults()

    fieldset_id = fieldset.fieldset_id

    if fieldset_id in _fieldsets:
        raise KeyError('"%s" is already a registered review request fieldset'
                       % fieldset_id)

    _fieldsets[fieldset_id] = fieldset

    # Set the field_classes to an empty list by default if it doesn't
    # explicitly provide its own, so that entries don't go into
    # BaseReviewRequestFieldSet's global list.
    if fieldset.field_classes is None:
        fieldset.field_classes = []

    for field_cls in fieldset.field_classes:
        _register_field(field_cls)


def unregister_review_request_fieldset(fieldset):
    """Unregisters a previously registered review request fieldset."""
    _populate_defaults()

    fieldset_id = fieldset.fieldset_id

    if fieldset_id not in _fieldsets:
        logging.error('Failed to unregister unknown review request fieldset '
                      '"%s"',
                      fieldset_id)
        raise KeyError('"%s" is not a registered review request fieldset'
                       % fieldset_id)

    fieldset = _fieldsets[fieldset_id]

    for field_cls in fieldset.field_classes:
        fieldset.remove_field(field_cls)

    del _fieldsets[fieldset_id]
