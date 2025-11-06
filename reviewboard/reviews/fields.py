"""Definitions for review request fields."""

from __future__ import annotations

import logging
from html import unescape
from typing import (Any, Iterable, Iterator, Generic, Optional, Sequence,
                    Type, TYPE_CHECKING, Union)

from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.html import (escape,
                               format_html,
                               format_html_join,
                               strip_tags)
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _
from djblets.markdown import iter_markdown_lines
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import ALREADY_REGISTERED, NOT_REGISTERED
from typing_extensions import TypeVar, TypedDict

from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.diffviewer.diffutils import get_line_changed_regions
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.templatetags.difftags import highlightregion
from reviewboard.registries.registry import Registry, OrderedRegistry
from reviewboard.reviews.markdown_utils import (is_rich_text_default_for_user,
                                                normalize_text_for_edit,
                                                render_markdown)

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest
    from djblets.webapi.responses import WebAPIResponsePayload
    from typelets.django.json import SerializableDjangoJSONDict
    from typelets.django.strings import StrOrPromise

    from reviewboard.changedescs.models import ChangeDescription
    from reviewboard.reviews.models.base_review_request_details import \
        BaseReviewRequestDetails


logger = logging.getLogger(__name__)


#: Generic type for a field's value.
#:
#: Version Added:
#:     7.1
TFieldValue = TypeVar('TFieldValue',
                      bound=Any,
                      default=Any)


class ReviewRequestFieldChangeEntrySection(TypedDict):
    """A rendered section in a Change Description.

    This is returned by :py:meth:`BaseReviewRequestField.
    get_change_entry_sections_html` in order to populate the change history of
    a review request.

    Each section can have a title/label and the HTML of the changed content.

    Version Added:
        7.1
    """

    #: The rendered HTML showing the changes.
    rendered_html: SafeString

    #: The title of the section.
    title: StrOrPromise


class FieldSetRegistry(OrderedRegistry[Type['BaseReviewRequestFieldSet']]):
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

    def __init__(self) -> None:
        """Initialize the registry."""
        self._key_order = []
        super().__init__()

    def register(
        self,
        fieldset: type[BaseReviewRequestFieldSet],
    ) -> None:
        """Register the fieldset.

        This will also register all field classes registered on the fieldset on
        the field registry.

        Args:
            fieldset (type):
                The fieldset to register, as a
                :py:class:`BaseReviewRequestFieldSet` subclass.
        """
        super().register(fieldset)

        # Set the field_classes to an empty list by default if it doesn't
        # explicitly provide its own, so that entries don't go into
        # BaseReviewRequestFieldSet's global list.
        if fieldset.field_classes is None:
            fieldset.field_classes = []

        for field_cls in fieldset.field_classes:
            field_registry.register(field_cls)

    def unregister(
        self,
        fieldset: type[BaseReviewRequestFieldSet],
    ) -> None:
        """Unregister the fieldset.

        This will unregister all field classes on the fieldset from the field
        registry.

        Args:
            fieldset (type):
                The field to remove, as a
                :py:class:`BaseReviewRequestFieldSet` subclass.
        """
        super().unregister(fieldset)

        for field_cls in fieldset.field_classes:
            fieldset.remove_field(field_cls)

    def get_defaults(self) -> Iterable[type[BaseReviewRequestFieldSet]]:
        """Return the list of built-in fieldsets.

        Returns:
            list:
            A list of the built-in
            :py:class:`~reviewboard.reviews.fields.BaseReviewRequestFieldSet`
            subclasses.
        """
        from reviewboard.reviews.builtin_fields import builtin_fieldsets

        return builtin_fieldsets


class FieldRegistry(Registry[Type['BaseReviewRequestField']]):
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

    def populate(self) -> None:
        """Populate the registry."""
        # Fields are only ever registered via the FieldSetRegistry, so we
        # ensure that it has been populated as well.
        fieldset_registry.populate()


fieldset_registry = FieldSetRegistry()
field_registry = FieldRegistry()


class BaseReviewRequestFieldSet:
    """Base class for sets of review request fields.

    A fieldset stores a list of fields that are rendered on the review
    request page. They may contain default fields, and new fields can be
    added or removed.

    Review Board provides three main fieldsets: "main", "info", and
    "reviewers". Others can be added by subclassing and registering
    through :py:data:`fieldset_registry`.

    Version Changed:
        4.0.7:
        Subclasses can now dynamically instantiate fields without registering
        their classes by overriding :py:meth:`build_fields`.
    """

    #: The ID of the fieldset.
    #:
    #: This must be unique within the :py:data:`field_registry`.
    #:
    #: Type:
    #:     str
    fieldset_id: Optional[str] = None

    #: The visible label of the fieldset.
    #:
    #: Type:
    #:     str
    label: Optional[StrOrPromise] = None

    #: Whether to show this fieldset as required.
    #:
    #: If set, the fieldset will show as required if the user is able to
    #: modify the review request.
    #:
    #: Type:
    #:     bool
    show_required: bool = False

    #: A list of fields that will by default be instantiated for the fieldset.
    #:
    #: These would be set by subclasses to a list of
    #: :py:class:`BaseReviewRequestField` subclasses.
    #:
    #: Type:
    #:     list of BaseReviewRequestField
    field_classes: Optional[list[type[BaseReviewRequestField]]] = None

    ######################
    # Instance variables #
    ######################

    #: The HTTP request from the client.
    request: Optional[HttpRequest]

    #: The review request details that this field will operate on.
    review_request_details: BaseReviewRequestDetails

    def __init__(
        self,
        review_request_details: BaseReviewRequestDetails,
        request: Optional[HttpRequest] = None,
    ) -> None:
        """Initialize the field set.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

            request (django.http.HttpRequest, optional):
                The HTTP request that resulted in building this fieldset.

                Version Added:
                    4.0.7
        """
        self.review_request_details = review_request_details
        self.request = request

    @classmethod
    def is_empty(cls) -> bool:
        """Return whether the fieldset is empty.

        A fieldset is empty if there are no field classes registered.
        An empty fieldset will not be displayed on the page.
        """
        return not cls.field_classes

    @classmethod
    def add_field(
        cls,
        field_cls: type[BaseReviewRequestField],
    ) -> None:
        """Add a field class to this fieldset.

        The field will be rendered inside this fieldset on the page.

        A given field class can only be in one fieldset. Its ``field_id``
        must be unique.

        Args:
            field_cls (class):
                The field class to add.
        """
        if cls.field_classes is None:
            cls.field_classes = []

        field_registry.register(field_cls)
        cls.field_classes.append(field_cls)

    @classmethod
    def remove_field(
        cls,
        field_cls: type[BaseReviewRequestField],
    ) -> None:
        """Remove a field class from this fieldset.

        The field class must have been previously added to this fieldset.

        Args:
            field_cls (class):
                The field class to remove.
        """
        if cls.field_classes is not None:
            cls.field_classes.remove(field_cls)

        try:
            field_registry.unregister(field_cls)
        except ItemLookupError as e:
            logger.error('Failed to unregister unknown review request '
                         'field "%s"',
                         field_cls.field_id)
            raise e

    @cached_property
    def should_render(self) -> bool:
        """Whether the fieldset should render.

        By default, fieldsets should render if any contained fields should
        render. Subclasses can override this if they need different behavior.

        Version Added:
            4.0.7

        Type:
            bool
        """
        for field in self.fields:
            try:
                if field.should_render:
                    return True
            except Exception as e:
                logger.exception('Failed to call %s.should_render: %s',
                                 type(field).__name__, e)

        return False

    @cached_property
    def fields(self) -> Sequence[BaseReviewRequestField]:
        """A list of all field instances in this fieldset.

        Fields are instantiated through :py:meth:`build_fields` the first time
        this is accessed.

        Version Added:
            4.0.7

        Type:
            list of BaseReviewRequestField
        """
        return self.build_fields()

    def build_fields(self) -> Sequence[BaseReviewRequestField]:
        """Return new fields for use in this fieldset instance.

        By default, this will loop through :py:attr:`field_classes` and
        instantiate each field, returning the final list.

        Subclasses can override this to provide custom logic, including
        returning field instances that aren't registered as field classes.
        This can be used to build fields tailored to a particular review
        request.

        Version Added:
            4.0.7

        Returns:
            list of BaseReviewRequestField:
            The list of new field instances.
        """
        fields: list[BaseReviewRequestField] = []

        if self.field_classes:
            review_request_details = self.review_request_details
            request = self.request

            for field_cls in self.field_classes:
                try:
                    fields.append(field_cls(
                        review_request_details=review_request_details,
                        request=request))
                except Exception as e:
                    logger.exception('Error instantiating field %r: %s',
                                     field_cls, e)

        return fields

    def __str__(self) -> str:
        """Represent the field set as a string.

        Returns:
            str:
            The field set's ID as a string.
        """
        return self.fieldset_id or '<Unset FieldSet ID>'


class BaseReviewRequestField(Generic[TFieldValue]):
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

    #: The unique ID of the field.
    field_id: Optional[str] = None

    #: The visible label for the field.
    label: Optional[StrOrPromise] = None

    #: Whether the contents of this field can be edited.
    is_editable: bool = False

    #: Whether a value is required for this field.
    is_required: bool = False

    #: The default CSS classes to use on this field.
    default_css_classes: Sequence[str] = []

    #: Whether change entries for this field should render inline.
    #:
    #: These will be presented in a more compact format. This should be
    #: disabled for longer fields, such as those containing multi-line text
    #: or other contents.
    change_entry_renders_inline: bool = True

    #: An optional database model that backs this field.
    #:
    #: If set, this field will track changes made to instances of this model.
    model: Optional[type[Model]] = None

    #: The HTML tag to be used when rendering the field.
    tag_name: str = 'span'

    #: Whether the field should be rendered.
    should_render: bool = True

    #: The class name for the JavaScript view representing this field.
    js_view_class: Optional[str] = None

    can_record_change_entry = property(lambda self: self.is_editable)

    ######################
    # Instance variables #
    ######################

    #: The HTTP request from the client.
    request: Optional[HttpRequest]

    #: The review request details that this field will operate on.
    review_request_details: BaseReviewRequestDetails

    #: The loaded value for the field.
    #:
    #: This is internal and may not be present on the field. Please
    #: use :py:attr:`value` instead.
    _value: Optional[TFieldValue]

    def __init__(
        self,
        review_request_details: BaseReviewRequestDetails,
        request: Optional[HttpRequest] = None,
    ) -> None:
        """Initialize the field.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

            request (django.http.HttpRequest, optional):
                The current HTTP request (used to check display preferences
                for the logged-in user).
        """
        self.review_request_details = review_request_details
        self.request = request

    @property
    def value(self) -> Optional[TFieldValue]:
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

    def has_value_changed(
        self,
        old_value: TFieldValue,
        new_value: TFieldValue,
    ) -> bool:
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

    def record_change_entry(
        self,
        changedesc: ChangeDescription,
        old_value: TFieldValue,
        new_value: TFieldValue,
    ) -> None:
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
        assert self.field_id

        changedesc.record_field_change(field=self.field_id,
                                       old_value=old_value,
                                       new_value=new_value)

    def serialize_change_entry(
        self,
        changedesc: ChangeDescription,
    ) -> Union[WebAPIResponsePayload, Sequence[WebAPIResponsePayload]]:
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

    def serialize_change_entry_for_model_list(
        self,
        field_info: Any,
    ) -> Union[WebAPIResponsePayload, Sequence[WebAPIResponsePayload]]:
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
        model = self.model
        assert model is not None

        pks = [
            value[2]
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
            for value in field_info[key]
        ]
        pk_to_objects: dict[str, Model] = {
            obj.pk: obj
            for obj in model.objects.filter(pk__in=pks)
        }

        return {
            key: [
                pk_to_objects[value[2]]
                for value in field_info[key]
            ]
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        }

    def serialize_change_entry_for_singleton(
        self,
        field_info: Any,
    ) -> Union[WebAPIResponsePayload, Sequence[WebAPIResponsePayload]]:
        """Return the change entry for a singleton.

        Singleton fields (e.g., summaries) are stored in
        :py:class:`~reviewboard.changedescs.models.ChangeDescription` as
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
        return {
            key: field_info[key][0]
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        }

    def serialize_change_entry_for_list(
        self,
        field_info: Any,
    ) -> Union[WebAPIResponsePayload, Sequence[WebAPIResponsePayload]]:
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
        return {
            key: [
                value[0]
                for value in field_info[key]
            ]
            for key in ('new', 'old', 'added', 'removed')
            if key in field_info
        }

    def get_change_entry_sections_html(
        self,
        info: Any,
    ) -> Sequence[ReviewRequestFieldChangeEntrySection]:
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
        assert self.label

        rendered_html = _legacy_mark_safe(
            self.render_change_entry_html(info),
            self,
            'render_change_entry_html')

        return [{
            'title': self.label,
            'rendered_html': rendered_html,
        }]

    def render_change_entry_html(
        self,
        info: Any,
    ) -> SafeString:
        """Render a change entry to HTML.

        By default, this returns a simple "changed from X to Y" using the old
        and new values. This can be overridden to generate more specialized
        output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Subclasses can override :py:meth:`render_change_entry_value_html` to
        change how the value itself will be rendered in the string.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

                For standard field changes, this is guaranteed to have ``new``
                and ``old`` keys, but may also contain ``added`` and
                ``removed`` keys as well.

                Subclasses may store and render data in custom formats.

        Returns:
            django.utils.safestring.SafeString:
            The HTML representation of the change entry.
        """
        rendered_old_value: SafeString
        rendered_new_value: SafeString

        assert isinstance(info, dict)

        if 'old' in info:
            rendered_old_value = _legacy_mark_safe(
                self.render_change_entry_removed_value_html(info,
                                                            info['old'][0]),
                self,
                'render_change_entry_removed_value_html')
        else:
            rendered_old_value = mark_safe('')

        if 'new' in info:
            rendered_new_value = _legacy_mark_safe(
                self.render_change_entry_added_value_html(info,
                                                          info['new'][0]),
                self,
                'render_change_entry_added_value_html')
        else:
            rendered_new_value = mark_safe('')

        return format_html(
            '<div class="rb-c-review-request-changed-value">{}{}</div>',
            rendered_old_value,
            rendered_new_value)

    def render_change_entry_added_value_html(
        self,
        info: Any,
        value: Any,
    ) -> SafeString:
        """Render the change entry for an added value to HTML.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

                The format and types are dependent on the way this field
                stores data. Subclasses can override the type to be more
                specific.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            value_html = _legacy_mark_safe(
                value_html,
                self,
                'render_change_entry_value_html')

            return format_html(
                '<div class="rb-c-review-request-changed-value__new">'
                '<div class="rb-c-review-request-changed-value__marker"'
                ' aria-label="{label}"></div>'
                '<div class="rb-c-review-request-changed-value__value">'
                '{value_html}</div>'
                '</div>',
                label=_('New value'),
                value_html=value_html)
        else:
            return mark_safe('')

    def render_change_entry_removed_value_html(
        self,
        info: Any,
        value: Any,
    ) -> SafeString:
        """Render the change entry for a removed value to HTML.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

                The format and types are dependent on the way this field
                stores data. Subclasses can override the type to be more
                specific.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        value_html = self.render_change_entry_value_html(info, value)

        if value_html:
            value_html = _legacy_mark_safe(
                value_html,
                self,
                'render_change_entry_value_html')

            return format_html(
                '<div class="rb-c-review-request-changed-value__old">'
                '<div class="rb-c-review-request-changed-value__marker"'
                ' aria-label="{label}"></div>'
                '<div class="rb-c-review-request-changed-value__value">'
                '{value_html}</div>'
                '</div>',
                label=_('Old value'),
                value_html=value_html)
        else:
            return mark_safe('')

    def render_change_entry_value_html(
        self,
        info: Any,
        value: Any,
    ) -> SafeString:
        """Render the value for a change description string to HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (object):
                The value of the field.

                The format and types are dependent on the way this field
                stores data. Subclasses can override the type to be more
                specific.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        return escape(str(value or ''))

    def load_value(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> Optional[TFieldValue]:
        """Load a value from the review request or draft.

        By default, this loads the value as-is from the extra_data field.
        This can be overridden if you need to deserialize the value in some
        way.

        This must use ``review_request_details`` instead of
        ``self.review_request_details``.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.
        """
        return review_request_details.extra_data.get(self.field_id)

    def save_value(
        self,
        value: Optional[TFieldValue],
    ) -> None:
        """Save the value in the review request or draft.

        By default, this saves the value as-is in the extra_data field.
        This can be overridden if you need to serialize the value in some
        way.

        Args:
            value (object):
                The new value for the field.
        """
        self.review_request_details.extra_data[self.field_id] = value

    def propagate_data(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> None:
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
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The source review request or draft whose data is to be
                propagated.
        """
        self.save_value(self.load_value(review_request_details))

    def render_value(
        self,
        value: Optional[TFieldValue],
    ) -> SafeString:
        """Render the value in the field.

        By default, this converts to text and escapes it. This can be
        overridden if you need to render it in a more specific way.

        This must use ``value`` instead of ``self.value``.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            value (object):
                The value to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered value.
        """
        return escape(str(value or ''))

    def get_css_classes(self) -> set[str]:
        """Return the set of CSS classes to apply to the element.

        By default, this will include the contents of
        :py:attr:`default_css_classes`,
        and ``"required"`` if it's a required field.

        This can be overridden to provide additional CSS classes, if they're
        not appropriate for :py:attr:default_css_classes`.

        Returns:
            set of str:
            A set of the CSS classes to apply.
        """
        css_classes = set(self.default_css_classes)

        if self.is_required:
            css_classes.add('required')

        return css_classes

    def get_dom_attributes(self) -> dict[str, str]:
        """Return any additional attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            Additional key/value pairs for attributes to include in the
            rendered HTML element.
        """
        return {}

    def get_data_attributes(self) -> dict[str, Any]:
        """Return any data attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            The data attributes to include in the element.
        """
        return {}

    def as_html(self) -> SafeString:
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

    def value_as_html(self) -> SafeString:
        """Return the field rendered as HTML.

        By default, this just calls ``render_value`` with the value
        from the database.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Returns:
            django.utils.safestring.SafeString:
            The rendered field.
        """
        return _legacy_mark_safe(self.render_value(self.value),
                                 self,
                                 'render_value')

    def __str__(self) -> str:
        """Represent the field as a string.

        Returns:
            str:
            The field's ID as a string.
        """
        return self.field_id or '<Unset Field ID>'


class BaseEditableField(BaseReviewRequestField[TFieldValue]):
    """Base class for an editable field.

    This simply marks the field as editable.
    """

    default_css_classes = ['editable']
    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.TextFieldView'


class BaseCommaEditableField(BaseEditableField[Sequence[TFieldValue]]):
    """Base class for an editable comma-separated list of values.

    This is used for dealing with lists of items that appear
    comma-separated in the UI. It works with stored lists of content
    on the review request or draft, and on the ChangeDescription.

    Subclasses can override this to provide specialized rendering
    on a per-item-basis. That's useful for showing links to items,
    for example.
    """

    default_css_classes = ['editable', 'comma-editable']

    #: Whether order matters for the items.
    #:
    #: If order matters, that order will be preserved. Otherwise, it may
    #: be changed when editing.
    order_matters = False

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.CommaSeparatedValuesTextFieldView'

    one_line_per_change_entry = True

    def has_value_changed(
        self,
        old_value: Sequence[TFieldValue],
        new_value: Sequence[TFieldValue],
    ) -> bool:
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

    def serialize_change_entry(
        self,
        changedesc: ChangeDescription,
    ) -> SerializableDjangoJSONDict:
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

    def render_value(
        self,
        value: Optional[Sequence[TFieldValue]],
    ) -> SafeString:
        """Render the list of items.

        This will call out to ``render_item`` for every item. The list
        of rendered items will be separated by a comma and a space.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            value (object):
                The value to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered value.
        """
        return format_html_join(', ', '{}', (
            (_legacy_mark_safe(self.render_item(item), self, 'render_item'),)
            for item in (value or [])
        ))

    def render_item(
        self,
        item: TFieldValue,
    ) -> SafeString:
        """Render an item from the list.

        By default, this will convert the item to text and then escape it.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            item (object):
                The item to render.

        Returns:
            django.utils.safestring.SafeString:
            The rendered item.
        """
        return escape(str(item or ''))

    def render_change_entry_html(
        self,
        info: Any,
    ) -> SafeString:
        """Render a change entry to HTML.

        By default, this returns HTML containing a list of removed items,
        and a list of added items. This can be overridden to generate
        more specialized output.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            django.utils.safestring.SafeString:
            The HTML representation of the change entry.
        """
        removed_items: SafeString
        added_items: SafeString

        assert isinstance(info, dict)

        if 'removed' in info:
            values = info['removed']

            if not self.one_line_per_change_entry:
                values = [values]

            removed_items = format_html_join('', '{}', (
                (_legacy_mark_safe(
                    self.render_change_entry_removed_value_html(info, [value]),
                    self,
                    'render_change_entry_removed_value_html'),)
                for value in values
            ))
        else:
            removed_items = mark_safe('')

        if 'added' in info:
            values = info['added']

            if not self.one_line_per_change_entry:
                values = [values]

            added_items = format_html_join('', '{}', (
                (_legacy_mark_safe(
                    self.render_change_entry_added_value_html(info, [value]),
                    self,
                    'render_change_entry_added_value_html'),)
                for value in values
            ))
        else:
            added_items = mark_safe('')

        return format_html(
            '<div class="rb-c-review-request-changed-value">{}{}</table>',
            removed_items,
            added_items)

    def render_change_entry_value_html(
        self,
        info: Any,
        value: Sequence[Any],
    ) -> SafeString:
        """Render a list of items for change description HTML.

        By default, this will call ``render_change_entry_item_html`` for every
        item in the list. The list of rendered items will be separated by a
        comma and a space.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (list):
                The value of the field.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        return format_html_join(', ', '{}', (
            (_legacy_mark_safe(
                self.render_change_entry_item_html(info, item),
                self,
                'render_change_entry_item_html'),)
            for item in value
        ))

    def render_change_entry_item_html(
        self,
        info: Any,
        item: Any,
    ) -> SafeString:
        """Render an item for change description HTML.

        By default, this just converts the value to text and escapes it.
        This can be overridden to customize how the value is displayed.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the item.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        assert isinstance(item, (tuple, list))

        return escape(str(item[0]))


class BaseTextAreaField(BaseEditableField[str]):
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
    def text_type_key(self) -> str:
        """Return the text type key for the ``extra_data`` dictionary.

        Returns:
            str:
            The key which stores the text type for the field.
        """
        field_id = self.field_id

        if field_id == 'text':
            return 'text_type'
        else:
            return f'{field_id}_text_type'

    def is_text_markdown(
        self,
        value: Optional[str],
    ) -> bool:
        """Return whether the text is in Markdown format.

        This can be overridden if the field needs to check something else
        to determine if the text is in Markdown format.

        Args:
            value (str):
                The value of the field.

        Returns:
            bool:
            Whether the text should be interpreted as Markdown.
        """
        text_type = self.review_request_details.extra_data.get(
            self.text_type_key, 'plain')

        return text_type == 'markdown'

    def propagate_data(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> None:
        """Propagate data in from source review request or draft.

        In addition to the value propagation handled by the base class, this
        copies the text type details from a source review request or draft and
        saves it as-is into the review request or draft associated with the
        field.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The source review request or draft whose data is to be
                propagated.
        """
        super().propagate_data(review_request_details)

        source_text_type = review_request_details.extra_data.get(
            self.text_type_key, None)

        if source_text_type is not None:
            self.review_request_details.extra_data[self.text_type_key] = \
                source_text_type

    def get_css_classes(self) -> set[str]:
        """Return the list of CSS classes.

        If Markdown is enabled, and the text is in Markdown format,
        this will add a "rich-text" field.

        Returns:
            set of str:
            A set of the CSS classes to apply.
        """
        css_classes = super().get_css_classes()

        if (self.enable_markdown and self.value and
            (self.should_render_as_markdown(self.value) or
             (self.request and
              self.request.user and
              is_rich_text_default_for_user(self.request.user)))):
            css_classes.add('rich-text')

        return css_classes

    def get_data_attributes(self) -> dict[str, Any]:
        """Return any data attributes to include in the element.

        By default, this returns nothing.

        Returns:
            dict:
            The data attributes to include in the element.
        """
        attrs = super().get_data_attributes()

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

    def render_value(
        self,
        value: Optional[str],
    ) -> SafeString:
        """Return the value of the field.

        If Markdown is enabled, and the text is not in Markdown format,
        the text will be escaped.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            value (str):
                The value of the field.

        Returns:
            django.utils.safestring.SafeString:
            The rendered value.
        """
        text = value or ''

        if self.should_render_as_markdown(text):
            return mark_safe(render_markdown(text))
        else:
            return escape(text)

    def should_render_as_markdown(
        self,
        value: Optional[str],
    ) -> bool:
        """Return whether the text should be rendered as Markdown.

        By default, this checks if the field is set to always render
        any text as Markdown, or if the given text is in Markdown format.

        Args:
            value (str):
                The value of the field.

        Returns:
            bool:
            Whether the text should be rendered as Markdown.
        """
        return self.always_render_markdown or self.is_text_markdown(value)

    def render_change_entry_html(
        self,
        info: Any,
    ) -> SafeString:
        """Render a change entry to HTML.

        This will render a diff of the changed text.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            django.utils.safestring.SafeString:
            The HTML representation of the change entry.
        """
        assert isinstance(info, dict)

        old_value = ''
        new_value = ''

        if 'old' in info:
            old_value = info['old'][0] or ''

        if 'new' in info:
            new_value = info['new'][0] or ''

        # NOTE: These are HTML-safe strings, but not a SafeString. Changing
        #       iter_markdown_lines to yield SafeStrings is an API breakage
        #       (it could have consequences in rendering pipelines), so it
        #       cannot be done until a major Djblets release.
        #
        #       We will be treating these as strings here and marking them
        #       safe later.
        old_value = render_markdown(old_value)
        new_value = render_markdown(new_value)
        old_lines = list(iter_markdown_lines(old_value))
        new_lines = list(iter_markdown_lines(new_value))

        differ = MyersDiffer(old_lines, new_lines)

        return format_html(
            '<table class="diffed-text-area">{}</table>',
            format_html_join(
                '',
                '{}',
                (
                    (line,)
                    for line in self._render_all_change_lines(
                        differ=differ,
                        old_lines=old_lines,
                        new_lines=new_lines)
                )))

    def _render_all_change_lines(
        self,
        *,
        differ: MyersDiffer,
        old_lines: Sequence[str],
        new_lines: Sequence[str],
    ) -> Iterator[SafeString]:
        """Render all lines of a diff.

        Version Changed:
            7.1:
            All arguments are now keyword-only arguments.

        Args:
            differ (reviewboard.diffviewer.myersdiff.MyersDiffer):
                The differ used to generate the lines.

            old_lines (list of str):
                The list of old lines to diff.

            new_lines (list of str):
                The list of new lines to diff.

        Yields:
            django.utils.safestring.SafeString:
            Each line in the diff.
        """
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                yield from self._render_change_lines(
                    tag=tag,
                    i1=i1,
                    i2=i2,
                    lines=old_lines)
            elif tag == 'insert':
                yield from self._render_change_lines(
                    tag=tag,
                    new_marker='+',
                    i1=j1,
                    i2=j2,
                    lines=new_lines)
            elif tag == 'delete':
                yield from self._render_change_lines(
                    tag=tag,
                    old_marker='-',
                    i1=i1,
                    i2=i2,
                    lines=old_lines)
            elif tag == 'replace':
                yield from self._render_change_replace_lines(
                    i1=i1,
                    i2=i2,
                    j1=j1,
                    j2=j2,
                    old_lines=old_lines,
                    new_lines=new_lines)
            else:
                raise ValueError(f'Unexpected tag "{tag}"')

    def _render_change_lines(
        self,
        *,
        tag: str,
        i1: int,
        i2: int,
        lines: Sequence[str],
        old_marker: str = '&nbsp;',
        new_marker: str = '&nbsp;',
    ) -> Iterator[SafeString]:
        """Render all lines in an equal/insert/delete chunk.

        Version Changed:
            7.1:
            All arguments are now keyword-only arguments.

        Args:
            tag (str);
                The equal/insert/delete tag.

            i1 (int):
                The starting line offset of the chunk.

            i2 (int):
                The ending line offset of the chunk.

            lines (list of str):
                The lines in the chunk.

            old_marker (str, optional):
                The marker to show for the original line.

            new_marker (str, optional):
                The marker to show for the modified line.

        Yields:
            django.utils.safestring.SafeString:
            Each line in the chunk.
        """
        for i in range(i1, i2):
            # NOTE: These variables are HTML-safe, but are standard strings.
            yield mark_safe(
                f'<tr class="{tag}">'
                f' <td class="marker">{old_marker}</td>'
                f' <td class="marker">{new_marker}</td>'
                f' <td class="line rich-text">{lines[i]}</td>'
                f'</tr>')

    def _render_change_replace_lines(
        self,
        *,
        i1: int,
        i2: int,
        j1: int,
        j2: int,
        old_lines: Sequence[str],
        new_lines: Sequence[str],
    ) -> Iterator[SafeString]:
        """Render all lines in a replace chunk.

        Version Changed:
            7.1:
            All arguments are now keyword-only arguments.

        Args:
            i1 (int):
                The starting line offset of the original chunk.

            i2 (int):
                The ending line offset of the original chunk.

            j1 (int):
                The starting line offset of the modified chunk.

            j2 (int):
                The ending line offset of the modified chunk.

            old_lines (list of str):
                The original lines in the chunk.

            new_lines (list of str):
                The modified lines in the chunk.

        Yields:
            django.utils.safestring.SafeString:
            Each line in the chunk.
        """
        replace_new_lines: list[str] = []

        for i, j in zip(range(i1, i2), range(j1, j2)):
            old_line = old_lines[i]
            new_line = new_lines[j]

            old_regions, new_regions = \
                get_line_changed_regions(unescape(strip_tags(old_line)),
                                         unescape(strip_tags(new_line)))

            old_line = highlightregion(old_line, old_regions)
            new_line = highlightregion(new_line, new_regions)

            # NOTE: old_line is HTML-safe, but is a standard string.
            yield mark_safe(
                f'<tr class="replace-old">'
                f' <td class="marker">~</td>'
                f' <td class="marker">&nbsp;</td>'
                f' <td class="line rich-text">{old_line}</td>'
                f'</tr>')

            replace_new_lines.append(new_line)

        for line in replace_new_lines:
            # NOTE: line is HTML-safe, but is a standard string.
            yield mark_safe(
                f'<tr class="replace-new">'
                f' <td class="marker">&nbsp;</td>'
                f' <td class="marker">~</td>'
                f' <td class="line rich-text">{line}</td>'
                f'</tr>')


class BaseCheckboxField(BaseReviewRequestField[bool]):
    """Base class for a checkbox.

    The field's value will be either True or False.
    """

    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.CheckboxFieldView'

    #: The default value of the field.
    #:
    #: This can be set by subclasses to override the default checkbox state.
    default_value: bool = False

    #: The HTML tag to be used when rendering the field.
    tag_name = 'input'

    def load_value(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> bool:
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

    def render_change_entry_html(
        self,
        info: Any,
    ) -> SafeString:
        """Render a change entry to HTML.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            django.utils.safestring.SafeString:
            The HTML representation of the change entry.
        """
        assert isinstance(info, dict)

        rendered_old_value: Optional[SafeString] = None
        rendered_new_value: Optional[SafeString] = None

        if 'old' in info:
            rendered_old_value = _legacy_mark_safe(
                self.render_change_entry_removed_value_html(info,
                                                            info['old'][0]),
                self,
                'render_change_entry_removed_value_html')
        else:
            rendered_old_value = mark_safe('')

        if 'new' in info:
            rendered_new_value = _legacy_mark_safe(
                self.render_change_entry_added_value_html(info,
                                                          info['new'][0]),
                self,
                'render_change_entry_added_value_html')
        else:
            rendered_new_value = mark_safe('')

        return format_html(
            '<table class="changed">{}{}</table>',
            rendered_old_value,
            rendered_new_value)

    def render_change_entry_value_html(
        self,
        info: Any,
        value: bool,
    ) -> SafeString:
        """Render the value for a change description string to HTML.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the field.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        if value:
            checked = ' checked'
        else:
            checked = ''

        return mark_safe(
            f'<input type="checkbox" autocomplete="off" disabled{checked}>'
        )

    def get_dom_attributes(self) -> dict[str, str]:
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

    def value_as_html(self) -> SafeString:
        """Return the field rendered as HTML.

        Because the value is included as a boolean attribute on the checkbox
        element, this just returns the empty string.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Returns:
            django.utils.safestring.SafeString:
            The rendered field.
        """
        return mark_safe('')


class BaseDropdownField(BaseReviewRequestField[str]):
    """Base class for a drop-down field."""

    is_editable = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DropdownFieldView'

    #: The default value of the field.
    default_value: Optional[str] = None

    #: The HTML tag to be used when rendering the field.
    tag_name = 'select'

    #: A list of the available options for the dropdown.
    #:
    #: Each entry in the list should be a 2-tuple of (value, label). The
    #: values must be unique.
    options: Sequence[tuple[str, StrOrPromise]] = []

    def load_value(
        self,
        review_request_details,
    ) -> Optional[str]:
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            str:
            The loaded value.
        """
        value = review_request_details.extra_data.get(self.field_id)

        if value is not None:
            return value
        else:
            return self.default_value

    def render_change_entry_value_html(
        self,
        info: Any,
        value: str,
    ) -> SafeString:
        """Render the value for a change description string to HTML.

        Version Changed:
            7.1:
            This is now expected to return a
            :py:class:`~django.utils.safestring.SafeString`, and this will
            be required in Review Board 9. Subclasses must use functions
            like :py:func:`django.utils.html.format_html()`.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            value (str):
                The value of the field.

        Returns:
            django.utils.safestring.SafeString:
            The rendered change entry.
        """
        for key, label in self.options:
            if value == key:
                return escape(label)

        return mark_safe('')

    def value_as_html(self) -> SafeString:
        """Return the field rendered as HTML.

        Select tags are funny kinds of inputs, and need a bunch of
        ``<option>`` elements inside them. This renders the "value" of the
        field as those options, to fit in with the base field's template.

        Returns:
            django.utils.safestring.SafeString:
            The rendered field.
        """
        data: list[tuple[str, str, StrOrPromise]] = []

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


class BaseDateField(BaseEditableField[str]):
    """Base class for a date field."""

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DateFieldView'

    #: The default value of the field.
    default_value: str = ''

    def load_value(
        self,
        review_request_details: BaseReviewRequestDetails,
    ) -> str:
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            str:
            The loaded value.
        """
        value = review_request_details.extra_data.get(self.field_id)

        if value is not None:
            return value
        else:
            return self.default_value


def get_review_request_fields() -> Iterator[type[BaseReviewRequestField]]:
    """Yield all registered field classes.

    Yields:
        type:
        The field classes, as subclasses of :py:class:`BaseReviewRequestField`
    """
    yield from field_registry


def get_review_request_fieldsets(
    include_change_entries_only: bool = False,
) -> Sequence[type[BaseReviewRequestFieldSet]]:
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
    excluded_ids: list[str] = []

    if not include_change_entries_only:
        excluded_ids.append('_change_entries_only')

    return [
        fieldset
        for fieldset in fieldset_registry
        if fieldset.fieldset_id not in excluded_ids
    ]


def get_review_request_fieldset(
    fieldset_id: str,
) -> Optional[type[BaseReviewRequestFieldSet]]:
    """Return the fieldset with the specified ID.

    Args:
        fieldset_id (str):
            The fieldset's ID.

    Returns:
        BaseReviewRequestFieldSet:
        The requested fieldset, or ``None`` if it could not be found.
    """
    return fieldset_registry.get('fieldset_id', fieldset_id)


def get_review_request_field(
    field_id: str,
) -> Optional[type[BaseReviewRequestField]]:
    """Return the field with the specified ID.

    Args:
        field_id (str):
            The field's ID.

    Returns:
        BaseReviewRequestField:
        The requested field, or ``None`` if it could not be found.
    """
    return field_registry.get('field_id', field_id)


def register_review_request_fieldset(
    fieldset: type[BaseReviewRequestFieldSet],
) -> None:
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


def unregister_review_request_fieldset(
    fieldset: type[BaseReviewRequestFieldSet],
) -> None:
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


def _legacy_mark_safe(
    s: Union[str, SafeString],
    obj: object,
    func_name: str,
) -> SafeString:
    """Ensure a SafeString, warning if the string is not safe.

    This is a compatibility function for taking in a string and ensuring a safe
    string result. If it's not a safe string, this will emit a deprecation
    warning and then cast, ensuring old implementations continue to work.

    This will be removed in Review Board 9.

    Version Added:
        7.1

    Args:
        s (str or django.utils.safestring.SafeString):
            The string to process.

        obj (object):
            The object containing the function called to generate the string.

        func_name (str):
            The name of the function that generated the string.

    Returns:
        django.utils.safestring.SafeString:
        The safe string.
    """
    if not isinstance(s, SafeString):
        RemovedInReviewBoard90Warning.warn(
            f'{type(obj).__name__}.{func_name}() must return an HTML-safe '
            'string (using format_html() or similar). This will be required '
            'in Review Board 9.',
            stacklevel=3)

        s = mark_safe(s)

    return s
