"""Definitions for review request fields."""

from __future__ import unicode_literals

import logging

from django.utils import six
from django.utils.functional import cached_property
from django.utils.html import escape, format_html_join, strip_tags
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.markdown import iter_markdown_lines
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import ALREADY_REGISTERED, NOT_REGISTERED
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.diffviewer.diffutils import get_line_changed_regions
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.registries.registry import Registry, OrderedRegistry
from reviewboard.reviews.markdown_utils import (is_rich_text_default_for_user,
                                                normalize_text_for_edit,
                                                render_markdown)


logger = logging.getLogger(__name__)


try:
    # Python >= 3.4
    from html import unescape
except ImportError:
    # Python < 3.4
    from django.utils.six.moves.html_parser import HTMLParser

    def unescape(s):
        return HTMLParser().unescape(s)


class FieldSetRegistry(OrderedRegistry):
    """A registry for field sets.

    This keeps the fieldsets in the registered order, so iterating through them
    will do so in the same order.
    """

    lookup_attrs = ('fieldset_id',)

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered review request fieldset.'
        ),
        NOT_REGISTERED: _(
            '%(attr_value)s is not a registered review request fieldset.'
        ),
    }

    def __init__(self):
        """Initialize the registry."""
        self._key_order = []
        super(FieldSetRegistry, self).__init__()

    def register(self, fieldset):
        """Register the fieldset.

        This will also register all field classes registered on the fieldset on
        the field registry.

        Args:
            fieldset (type):
                The fieldset to register, as a
                :py:class:`BaseReviewRequestFieldSet` subclass.
        """
        super(FieldSetRegistry, self).register(fieldset)

        # Set the field_classes to an empty list by default if it doesn't
        # explicitly provide its own, so that entries don't go into
        # BaseReviewRequestFieldSet's global list.
        if fieldset.field_classes is None:
            fieldset.field_classes = []

        for field_cls in fieldset.field_classes:
            field_registry.register(field_cls)

    def unregister(self, fieldset):
        """Unregister the fieldset.

        This will unregister all field classes on the fieldset from the field
        registry.

        Args:
            fieldset (type):
                The field to remove, as a
                :py:class:`BaseReviewRequestFieldSet` subclass.
        """
        super(FieldSetRegistry, self).unregister(fieldset)

        for field_cls in fieldset.field_classes:
            fieldset.remove_field(field_cls)

    def get_defaults(self):
        """Return the list of built-in fieldsets.

        Returns:
            list:
            A list of the built-in
            :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`
            subclasses.
        """
        from reviewboard.reviews.builtin_fields import builtin_fieldsets

        return builtin_fieldsets


class FieldRegistry(Registry):
    """A registry for review request fields."""

    lookup_attrs = ['field_id']
    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered review request field. Field '
            'IDs must be unique across all fieldsets.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s is not a registered review request fieldset.'
        ),
    }

    def populate(self):
        """Populate the registry."""
        # Fields are only ever registered via the FieldSetRegistry, so we
        # ensure that it has been populated as well.
        fieldset_registry.populate()


fieldset_registry = FieldSetRegistry()
field_registry = FieldRegistry()


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
        """Initialize the field set.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details.BaseReviewRequestDetails):
                The review request or draft.
        """
        self.review_request_details = review_request_details

    @classmethod
    def is_empty(cls):
        """Return whether the fieldset is empty.

        A fieldset is empty if there are no field classes registered.
        An empty fieldset will not be displayed on the page.
        """
        return not cls.field_classes

    @classmethod
    def add_field(cls, field_cls):
        """Add a field class to this fieldset.

        The field will be rendered inside this fieldset on the page.

        A given field class can only be in one fieldset. Its ``field_id``
        must be unique.

        Args:
            field_cls (class):
                The field class to add.
        """
        field_registry.register(field_cls)
        cls.field_classes.append(field_cls)

    @classmethod
    def remove_field(cls, field_cls):
        """Remove a field class from this fieldset.

        The field class must have been previously added to this fieldset.

        Args:
            field_cls (class):
                The field class to remove.
        """
        cls.field_classes.remove(field_cls)

        try:
            field_registry.unregister(field_cls)
        except ItemLookupError as e:
            logger.error('Failed to unregister unknown review request '
                         'field "%s"',
                         field_cls.field_id)
            raise e

    def __str__(self):
        """Represent the field set as a byte string.

        Returns:
            bytes:
            The field set's ID as a byte string.
        """
        if isinstance(self.fieldset_id, six.binary_type):
            return self.fieldset_id

        return self.fieldset_id.encode('utf-8')

    def __unicode__(self):
        """Represent the field set as a unicode string.

        Returns:
            unicode:
            The field set's ID as a unicode string.
        """
        if isinstance(self.fieldset_id, six.binary_type):
            return self.fieldset_id.decode('utf-8')

        return self.fieldset_id


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

    #: The HTML tag to be used when rendering the field.
    tag_name = 'span'

    #: Whether the field should be rendered.
    should_render = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = None

    can_record_change_entry = property(lambda self: self.is_editable)

    def __init__(self, review_request_details, request=None):
        """Initialize the field.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details.BaseReviewRequestDetails):
                The review request or draft.

            request (django.http.HttpRequest, optional):
                The current HTTP request (used to check display preferences
                for the logged-in user).
        """
        self.review_request_details = review_request_details
        self.request = request

    @property
    def value(self):
        """Return the value loaded from the database.

        This will fetch the value with the associated ReviewRequest or
        ReviewRequestDraft, and then cache it for future lookups.

        Returns:
            object:
            The value of the field.
        """
        if not hasattr(self, '_value'):
            self._value = self.load_value(self.review_request_details)

        return self._value

    def has_value_changed(self, old_value, new_value):
        """Return whether the value has changed.

        By default, it performs an inequality check on the values. This
        can be overridden to perform more specialized checks.

        Args:
            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.

        Returns:
            bool:
            Whether the value of the field has changed.
        """
        return old_value != new_value

    def record_change_entry(self, changedesc, old_value, new_value):
        """Record information on the changed values in a ChangeDescription.

        By default, the values are stored as-is along with the field ID.
        This can be overridden to perform more specialized storage.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the entry in.

            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.
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
        """Return sections of change entries with titles and rendered HTML.

        By default, this just returns a single section for the field, with
        the field's title and rendered change HTML.

        Subclasses can override this to provide more information.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            list of dict:
            A list of the change entry sections.
        """
        return [{
            'title': self.label,
            'rendered_html': mark_safe(self.render_change_entry_html(info)),
        }]

    def render_change_entry_html(self, info):
        """Render a change entry to HTML.

        By default, this returns a simple "changed from X to Y" using the old
        and new values. This can be overridden to generate more specialized
        output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Subclasses can override ``render_change_entry_value_html`` to
        change how the value itself will be rendered in the string.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            unicode:
            The HTML representation of the change entry.
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
        """Render the change entry for an added value to HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            return ('<tr class="new-value"><th class="marker">+</th>'
                    '<td class="value">%s</td></tr>' % value_html)
        else:
            return ''

    def render_change_entry_removed_value_html(self, info, value):
        """Render the change entry for a removed value to HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            return ('<tr class="old-value"><th class="marker">-</th>'
                    '<td class="value">%s</td></tr>' % value_html)
        else:
            return ''

    def render_change_entry_value_html(self, info, value):
        """Render the value for a change description string to HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        return escape(six.text_type(value or ''))

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        By default, this loads the value as-is from the extra_data field.
        This can be overridden if you need to deserialize the value in some
        way.

        This must use ``review_request_details`` instead of
        ``self.review_request_details``.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details.BaseReviewRequestDetails):
                The review request or draft.
        """
        return review_request_details.extra_data.get(self.field_id)

    def save_value(self, value):
        """Save the value in the review request or draft.

        By default, this saves the value as-is in the extra_data field.
        This can be overridden if you need to serialize the value in some
        way.

        Args:
            value (object):
                The new value for the field.
        """
        self.review_request_details.extra_data[self.field_id] = value

    def propagate_data(self, review_request_details):
        """Propagate data in from source review request or draft.

        By default, this loads only the field's value from a source review
        request or draft and saves it as-is into the review request or draft
        associated with the field. This can be overridden if you need to
        propagate additional data elements.

        This method is preferable to explicitly calling :py:meth:`load_value`
        and :py:meth:`save_value` in series to propagate data from a source
        into a field, because it allows for copying additional data elements
        beyond only the field's value.

        This function must use the ``review_request_details`` parameter instead
        of the :py:attr:`review_request_details` attribute on the field.

        Args:
            review_request_details (reviewboard.reviews.models.base_review_request_details.BaseReviewRequestDetails):
                The source review request or draft whose data is to be
                propagated.
        """
        self.save_value(self.load_value(review_request_details))

    def render_value(self, value):
        """Render the value in the field.

        By default, this converts to text and escapes it. This can be
        overridden if you need to render it in a more specific way.

        This must use ``value`` instead of ``self.value``.

        Args:
            value (object):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        return escape(six.text_type(value or ''))

    def get_css_classes(self):
        """Return the set of CSS classes to apply to the element.

        By default, this will include the contents of ``default_css_classes``,
        and ``required`` if it's a required field.

        This can be overridden to provide additional CSS classes, if they're
        not appropriate for ``default_css_classes``.

        Returns:
            set of unicode:
            A set of the CSS classes to apply.
        """
        css_classes = set(self.default_css_classes)

        if self.is_required:
            css_classes.add('required')

        return css_classes

    def get_dom_attributes(self):
        """Return any additional attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            Additional key/value pairs for attributes to include in the
            rendered HTML element.
        """
        return {}

    def get_data_attributes(self):
        """Return any data attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            The data attributes to include in the element.
        """
        return {}

    def as_html(self):
        """Return the field rendered to HTML.

        Returns:
            django.utils.safetext.SafeString:
            The rendered field.
        """
        return render_to_string(
            template_name='reviews/review_request_field.html',
            context={
                'field': self,
            })

    def value_as_html(self):
        """Return the field rendered as HTML.

        By default, this just calls ``render_value`` with the value
        from the database.

        Returns:
            unicode:
            The rendered field.
        """
        return self.render_value(self.value)

    def __str__(self):
        """Represent the field as a byte string.

        Returns:
            bytes:
            The field's ID as a byte string.
        """
        if isinstance(self.field_id, six.binary_type):
            return self.field_id

        return self.field_id.encode('utf-8')

    def __unicode__(self):
        """Represent the field as a unicode string.

        Returns:
            unicode:
            The field's ID as a unicode string.
        """
        if isinstance(self.field_id, six.binary_type):
            return self.field_id.decode('utf-8')

        return self.field_id


class BaseEditableField(BaseReviewRequestField):
    """Base class for an editable field.

    This simply marks the field as editable.
    """

    default_css_classes = ['editable']
    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.TextFieldView'


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

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.CommaSeparatedValuesTextFieldView'

    one_line_per_change_entry = True

    def has_value_changed(self, old_value, new_value):
        """Return whether two values have changed.

        If :py:attr:`order_matters` is set to ``True``, this will do a strict
        list comparison. Otherwise, it will compare the items in both lists
        without caring about the ordering.

        Args:
            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.

        Returns:
            bool:
            Whether the value of the field has changed.
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
        """Render the list of items.

        This will call out to ``render_item`` for every item. The list
        of rendered items will be separated by a comma and a space.

        Args:
            value (object):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        return ', '.join([
            self.render_item(value)
            for value in values
        ])

    def render_item(self, item):
        """Render an item from the list.

        By default, this will convert the item to text and then escape it.

        Args:
            item (object):
                The item to render.

        Returns:
            unicode:
            The rendered item.
        """
        return escape(six.text_type(item or ''))

    def render_change_entry_html(self, info):
        """Render a change entry to HTML.

        By default, this returns HTML containing a list of removed items,
        and a list of added items. This can be overridden to generate
        more specialized output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            unicode:
            The HTML representation of the change entry.
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
        """Render a list of items for change description HTML.

        By default, this will call ``render_change_entry_item_html`` for every
        item in the list. The list of rendered items will be separated by a
        comma and a space.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            values (list):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        return ', '.join([
            self.render_change_entry_item_html(info, item)
            for item in values
        ])

    def render_change_entry_item_html(self, info, item):
        """Render an item for change description HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the item.

        Returns:
            unicode:
            The rendered change entry.
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

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.MultilineTextFieldView'

    @cached_property
    def text_type_key(self):
        """Return the text type key for the ``extra_data`` dictionary.

        Returns:
            unicode:
            The key which stores the text type for the field.
        """
        if self.field_id == 'text':
            return 'text_type'
        else:
            return '%s_text_type' % self.field_id

    def is_text_markdown(self, value):
        """Return whether the text is in Markdown format.

        This can be overridden if the field needs to check something else
        to determine if the text is in Markdown format.

        Args:
            value (unicode):
                The value of the field.

        Returns:
            bool:
            Whether the text should be interpreted as Markdown.
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
            review_request_details (reviewboard.reviews.models.base_review_request_details.BaseReviewRequestDetails):
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
        """Return the list of CSS classes.

        If Markdown is enabled, and the text is in Markdown format,
        this will add a "rich-text" field.

        Returns:
            set of unicode:
            A set of the CSS classes to apply.
        """
        css_classes = super(BaseTextAreaField, self).get_css_classes()

        if (self.enable_markdown and self.value and
            (self.should_render_as_markdown(self.value) or
             (self.request.user and
              is_rich_text_default_for_user(self.request.user)))):
            css_classes.add('rich-text')

        return css_classes

    def get_data_attributes(self):
        """Return any data attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            The data attributes to include in the element.
        """
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
        """Return the value of the field.

        If Markdown is enabled, and the text is not in Markdown format,
        the text will be escaped.

        Args:
            text (unicode):
                The value of the field.

        Returns:
            unicode:
            The rendered value.
        """
        text = text or ''

        if self.should_render_as_markdown(text):
            return render_markdown(text)
        else:
            return escape(text)

    def should_render_as_markdown(self, value):
        """Return whether the text should be rendered as Markdown.

        By default, this checks if the field is set to always render
        any text as Markdown, or if the given text is in Markdown format.

        Args:
            value (unicode):
                The value of the field.

        Returns:
            bool:
            Whether the text should be rendered as Markdown.
        """
        return self.always_render_markdown or self.is_text_markdown(value)

    def render_change_entry_html(self, info):
        """Render a change entry to HTML.

        This will render a diff of the changed text.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            unicode:
            The HTML representation of the change entry.
        """
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

            old_regions, new_regions = \
                get_line_changed_regions(unescape(strip_tags(old_line)),
                                         unescape(strip_tags(new_line)))

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


class BaseCheckboxField(BaseReviewRequestField):
    """Base class for a checkbox.

    The field's value will be either True or False.
    """

    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.CheckboxFieldView'

    #: The default value of the field.
    default_value = False

    #: The HTML tag to be used when rendering the field.
    tag_name = 'input'

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            bool:
            The loaded value.
        """
        value = review_request_details.extra_data.get(self.field_id)

        if value is not None:
            return value
        else:
            return self.default_value

    def render_change_entry_html(self, info):
        """Render a change entry to HTML.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            unicode:
            The HTML representation of the change entry.
        """
        old_value = None
        new_value = None

        if 'old' in info:
            old_value = info['old'][0]

        if 'new' in info:
            new_value = info['new'][0]

        s = ['<table class="changed">']

        if old_value is not None:
            s.append(self.render_change_entry_removed_value_html(
                info, old_value))

        if new_value is not None:
            s.append(self.render_change_entry_added_value_html(
                info, new_value))

        s.append('</table>')

        return ''.join(s)

    def render_change_entry_value_html(self, info, value):
        """Render the value for a change description string to HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        if value:
            checked = 'checked'
        else:
            checked = ''

        return ('<input type="checkbox" autocomplete="off" disabled %s>'
                % checked)

    def get_dom_attributes(self):
        """Return any additional attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            Additional key/value pairs for attributes to include in the
            rendered HTML element.
        """
        attrs = {
            'type': 'checkbox',
        }

        if self.value:
            attrs['checked'] = 'checked'

        return attrs

    def value_as_html(self):
        """Return the field rendered as HTML.

        Because the value is included as a boolean attribute on the checkbox
        element, this just returns the empty string.

        Returns:
            unicode:
            The rendered field.
        """
        return ''


class BaseDropdownField(BaseReviewRequestField):
    """Base class for a drop-down field."""

    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DropdownFieldView'

    #: The default value of the field.
    default_value = None

    #: The HTML tag to be used when rendering the field.
    tag_name = 'select'

    #: A list of the available options for the dropdown.
    #:
    #: Each entry in the list should be a 2-tuple of (value, label). The values
    #: must be unique. Both values and labels should be unicode.
    options = []

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            unicode:
            The loaded value.
        """
        value = review_request_details.extra_data.get(self.field_id)

        if value is not None:
            return value
        else:
            return self.default_value

    def render_change_entry_value_html(self, info, value):
        """Render the value for a change description string to HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the field.

        Returns:
            unicode:
            The rendered change entry.
        """
        for key, label in self.options:
            if value == key:
                return escape(label)

        return ''

    def value_as_html(self):
        """Return the field rendered as HTML.

        Select tags are funny kinds of inputs, and need a bunch of
        ``<option>`` elements inside them. This renders the "value" of the
        field as those options, to fit in with the base field's template.

        Returns:
            django.utils.safestring.SafeText:
            The rendered field.
        """
        data = []

        for value, label in self.options:
            if self.value == value:
                selected = ' selected'
            else:
                selected = ''

            data.append((value, selected, label))

        return format_html_join(
            '',
            '<option value="{}"{}>{}</option>',
            data)


class BaseDateField(BaseEditableField):
    """Base class for a date field."""

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DateFieldView'

    #: The default value of the field.
    default_value = ''

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            unicode:
            The loaded value.
        """
        value = review_request_details.extra_data.get(self.field_id)

        if value is not None:
            return value
        else:
            return self.default_value


def get_review_request_fields():
    """Yield all registered field classes.

    Yields:
        type:
        The field classes, as subclasses of :py:class:`BaseReviewRequestField`
    """
    for field in field_registry:
        yield field


def get_review_request_fieldsets(include_change_entries_only=False):
    """Return a list of all registered fieldset classes.

    As an internal optimization, the "main" fieldset can be filtered out,
    to help with rendering the side of the review request page.

    Args:
        include_change_entries_only (bool):
            Whether or not to include the change-entry only fieldset.

    Returns:
        list:
        The requested :py:class:`fieldsets <BaseReviewRequestFieldSet>`.
    """
    excluded_ids = []

    if not include_change_entries_only:
        excluded_ids.append('_change_entries_only')

    return [
        fieldset
        for fieldset in fieldset_registry
        if fieldset.fieldset_id not in excluded_ids
    ]


def get_review_request_fieldset(fieldset_id):
    """Return the fieldset with the specified ID.

    Args:
        fieldset_id (unicode):
            The fieldset's ID.

    Returns:
        BaseReviewRequestFieldSet:
        The requested fieldset, or ``None`` if it could not be found.
    """
    return fieldset_registry.get('fieldset_id', fieldset_id)


def get_review_request_field(field_id):
    """Return the field with the specified ID.

    Args:
        field_id (unicode):
            The field's ID.

    Returns:
        BaseReviewRequestField:
        The requested field, or ``None`` if it could not be found.
    """
    return field_registry.get('field_id', field_id)


def register_review_request_fieldset(fieldset):
    """Register a custom review request fieldset.

    The fieldset must have a :py:attr:`~BaseReviewRequestFieldSet.fieldset_id`
    attribute. This ID **must** be unique across all registered fieldsets, or
    an exception will be thrown.

    Args:
        fieldset (type):
            The :py:class:`BaseReviewRequestFieldSet` subclass.

    Raises:
        djblets.registries.errors.ItemLookupError:
            This will be thrown if a fieldset is already registered with the
            same ID.
    """
    fieldset_registry.register(fieldset)


def unregister_review_request_fieldset(fieldset):
    """Unregister a previously registered review request fieldset.

    Args:
        fieldset (type):
            The :py:class:`BaseReviewRequestFieldSet` subclass.

    Raises:
        djblets.registries.errors.ItemLookupError:
            This will be thrown if the fieldset is not already registered.
    """
    try:
        fieldset_registry.unregister(fieldset)
    except ItemLookupError as e:
        logger.error('Failed to unregister unknown review request fieldset '
                     '"%s"',
                     fieldset.fieldset_id)
        raise e
