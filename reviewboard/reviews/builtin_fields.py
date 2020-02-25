from __future__ import unicode_literals

import logging
import uuid
from itertools import chain

from django.contrib.auth.models import User
from django.core.urlresolvers import NoReverseMatch
from django.db import models
from django.template.loader import get_template
from django.utils import six
from django.utils.functional import cached_property
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.util.compat.django.template.loader import render_to_string

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.diffutils import get_sorted_filediffs
from reviewboard.diffviewer.models import DiffCommit, DiffSet
from reviewboard.reviews.fields import (BaseCommaEditableField,
                                        BaseEditableField,
                                        BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        BaseTextAreaField)
from reviewboard.reviews.models import (Group, ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot)
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse


logger = logging.getLogger(__name__)


class BuiltinFieldMixin(object):
    """Mixin for built-in fields.

    This overrides some functions to work with native fields on a
    ReviewRequest or ReviewRequestDraft, rather than working with those
    stored in extra_data.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the field.

        Args:
            *args (tuple):
                Positional arguments to pass through to the superclass.

            **kwargs (dict):
                Keyword arguments to pass through to the superclass.
        """
        super(BuiltinFieldMixin, self).__init__(*args, **kwargs)

        if (not hasattr(self.review_request_details, self.field_id) and
            isinstance(self.review_request_details, ReviewRequestDraft)):
            # This field only exists in ReviewRequest, and not in
            # the draft, so we're going to work there instead.
            self.review_request_details = \
                self.review_request_details.get_review_request()

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        value = getattr(review_request_details, self.field_id)

        if isinstance(value, models.Manager):
            value = list(value.all())

        return value

    def save_value(self, value):
        """Save the value in the review request or draft.

        Args:
            value (object):
                The new value for the field.
        """
        setattr(self.review_request_details, self.field_id, value)


class BuiltinTextAreaFieldMixin(BuiltinFieldMixin):
    """Mixin for built-in text area fields.

    This will ensure that the text is always rendered in Markdown,
    no matter whether the source text is plain or Markdown. It will
    still escape the text if it's not in Markdown format before
    rendering.
    """

    def get_data_attributes(self):
        """Return any data attributes to include in the element.

        Returns:
            dict:
            The data attributes to include in the element.
        """
        attrs = super(BuiltinTextAreaFieldMixin, self).get_data_attributes()

        # This is already available in the review request state fed to the
        # page, so we don't need it in the data attributes as well.
        attrs.pop('raw-value', None)

        return attrs


class ReviewRequestPageDataMixin(object):
    """Mixin for internal fields needing access to the page data.

    These are used by fields that operate on state generated when creating the
    review request page. The view handling that page makes a lot of queries,
    and stores the results. This mixin allows access to those results,
    preventing additional queries.

    The data structure is not meant to be public API, and this mixin should not
    be used by any classes outside this file.

    By default, this will not render or handle any value loading or change
    entry recording. Subclasses must implement those manually.
    """

    #: Whether the field should be rendered.
    should_render = False

    def __init__(self, review_request_details, data=None, *args, **kwargs):
        """Initialize the mixin.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request (or the active draft thereof). In practice
                this will either be a
                :py:class:`reviewboard.reviews.models.ReviewRequest` or a
                :py:class:`reviewboard.reviews.models.ReviewRequestDraft`.

            data (reviewboard.reviews.detail.ReviewRequestPageData):
                The data already queried for the review request page.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.
        """
        super(ReviewRequestPageDataMixin, self).__init__(
            review_request_details, *args, **kwargs)

        self.data = data

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        return None

    def record_change_entry(self, changedesc, old_value, new_value):
        """Record information on the changed values in a ChangeDescription.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the entry in.

            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.
        """
        pass


class BaseCaptionsField(ReviewRequestPageDataMixin, BaseReviewRequestField):
    """Base class for rendering captions for attachments.

    This serves as a base for FileAttachmentCaptionsField and
    ScreenshotCaptionsField. It provides the base rendering and
    for caption changes on file attachments or screenshots.
    """

    obj_map_attr = None
    caption_object_field = None

    change_entry_renders_inline = False

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
        render_item = super(BaseCaptionsField, self).render_change_entry_html
        obj_map = getattr(self.data, self.obj_map_attr)

        s = ['<table class="caption-changed">']

        for id_str, caption in six.iteritems(info):
            obj = obj_map[int(id_str)]

            s.append(format_html(
                '<tr>'
                ' <th><a href="{url}">{filename}</a>:</th>'
                ' <td>{caption}</td>'
                '</tr>',
                url=obj.get_absolute_url(),
                filename=obj.filename,
                caption=mark_safe(render_item(caption))))

        s.append('</table>')

        return ''.join(s)

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
            list:
            An appropriate serialization for the field.
        """
        data = changedesc.fields_changed[self.field_id]

        return [
            {
                'old': data[six.text_type(obj.pk)]['old'][0],
                'new': data[six.text_type(obj.pk)]['new'][0],
                self.caption_object_field: obj,
            }
            for obj in self.model.objects.filter(pk__in=six.iterkeys(data))
        ]


class BaseModelListEditableField(BaseCommaEditableField):
    """Base class for editable comma-separated list of model instances.

    This is used for built-in classes that work with ManyToManyFields.
    """

    model_name_attr = None

    def has_value_changed(self, old_value, new_value):
        """Return whether the value has changed.

        Args:
            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.

        Returns:
            bool:
            Whether the value of the field has changed.
        """
        old_values = set([obj.pk for obj in old_value])
        new_values = set([obj.pk for obj in new_value])

        return old_values.symmetric_difference(new_values)

    def record_change_entry(self, changedesc, old_value, new_value):
        """Record information on the changed values in a ChangeDescription.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the entry in.

            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.
        """
        changedesc.record_field_change(self.field_id, old_value, new_value,
                                       self.model_name_attr)

    def render_change_entry_item_html(self, info, item):
        """Render an item for change description HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the item.

        Returns:
            unicode:
            The rendered change entry.
        """
        label, url, pk = item

        if url:
            return '<a href="%s">%s</a>' % (escape(url), escape(label))
        else:
            return escape(label)

    def save_value(self, value):
        """Save the value in the review request or draft.

        Args:
            value (object):
                The new value for the field.
        """
        setattr(self, self.field_id, value)


class StatusField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Status field on a review request."""

    field_id = 'status'
    label = _('Status')
    is_required = True

    #: Whether the field should be rendered.
    should_render = False

    def get_change_entry_sections_html(self, info):
        """Return sections of change entries with titles and rendered HTML.

        Because the status field is specially handled, this just returns an
        empty list.
        """
        return []


class SummaryField(BuiltinFieldMixin, BaseEditableField):
    """The Summary field on a review request."""

    field_id = 'summary'
    label = _('Summary')
    is_required = True
    tag_name = 'h1'

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.SummaryFieldView'


class DescriptionField(BuiltinTextAreaFieldMixin, BaseTextAreaField):
    """The Description field on a review request."""

    field_id = 'description'
    label = _('Description')
    is_required = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DescriptionFieldView'

    def is_text_markdown(self, value):
        """Return whether the description uses Markdown.

        Returns:
            bool:
            True if the description field should be formatted using Markdown.
        """
        return self.review_request_details.description_rich_text


class TestingDoneField(BuiltinTextAreaFieldMixin, BaseTextAreaField):
    """The Testing Done field on a review request."""

    field_id = 'testing_done'
    label = _('Testing Done')

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.TestingDoneFieldView'

    def is_text_markdown(self, value):
        """Return whether the description uses Markdown.

        Returns:
            bool:
            True if the description field should be formatted using Markdown.
        """
        return self.review_request_details.testing_done_rich_text


class OwnerField(BuiltinFieldMixin, BaseEditableField):
    """The Owner field on a review request."""

    field_id = 'submitter'
    label = _('Owner')
    model = User
    model_name_attr = 'username'
    is_required = True

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.OwnerFieldView'

    def render_value(self, user):
        """Render the value in the field.

        Args:
            user (django.contrib.auth.models.User):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        return format_html(
            '<a class="user" href="{0}">{1}</a>',
            local_site_reverse(
                'user',
                local_site=self.review_request_details.local_site,
                args=[user]),
            user.get_profile().get_display_name(self.request.user))

    def record_change_entry(self, changedesc, old_value, new_value):
        """Record information on the changed values in a ChangeDescription.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the entry in.

            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.
        """
        changedesc.record_field_change(self.field_id, old_value, new_value,
                                       self.model_name_attr)

    def render_change_entry_value_html(self, info, item):
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
        label, url, pk = item

        if url:
            return '<a href="%s">%s</a>' % (escape(url), escape(label))
        else:
            return escape(label)

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
        entry = super(OwnerField, self).serialize_change_entry(changedesc)

        return dict(
            (key, value[0])
            for key, value in six.iteritems(entry)
        )


class RepositoryField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Repository field on a review request."""

    field_id = 'repository'
    label = _('Repository')
    model = Repository

    @property
    def should_render(self):
        """Whether the field should be rendered."""
        review_request = self.review_request_details.get_review_request()

        return review_request.repository_id is not None


class BranchField(BuiltinFieldMixin, BaseEditableField):
    """The Branch field on a review request."""

    field_id = 'branch'
    label = _('Branch')

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.BranchFieldView'


class BugsField(BuiltinFieldMixin, BaseCommaEditableField):
    """The Bugs field on a review request."""

    field_id = 'bugs_closed'
    label = _('Bugs')

    one_line_per_change_entry = False

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.BugsFieldView'

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        return review_request_details.get_bug_list()

    def save_value(self, value):
        """Save the value in the review request or draft.

        Args:
            value (object):
                The new value for the field.
        """
        setattr(self.review_request_details, self.field_id, ', '.join(value))

    def render_item(self, bug_id):
        """Render an item from the list.

        Args:
            item (object):
                The item to render.

        Returns:
            unicode:
            The rendered item.
        """
        bug_url = self._get_bug_url(bug_id)

        if bug_url:
            return format_html('<a class="bug" href="{url}">{id}</a>',
                               url=bug_url, id=bug_id)
        else:
            return escape(bug_id)

    def render_change_entry_item_html(self, info, item):
        """Render an item for change description HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the item.

        Returns:
            unicode:
            The rendered change entry.
        """
        return self.render_item(item[0])

    def _get_bug_url(self, bug_id):
        """Return the URL to link to a specific bug.

        Args:
            bug_id (unicode):
                The ID of the bug to link to.

        Returns:
            unicode:
            The link to view the bug in the bug tracker, if available.
        """
        review_request = self.review_request_details.get_review_request()
        repository = self.review_request_details.repository
        local_site_name = None
        bug_url = None

        if review_request.local_site:
            local_site_name = review_request.local_site.name

        try:
            if (repository and
                repository.bug_tracker and
                '%s' in repository.bug_tracker):
                bug_url = local_site_reverse(
                    'bug_url', local_site_name=local_site_name,
                    args=[review_request.display_id, bug_id])
        except NoReverseMatch:
            pass

        return bug_url


class DependsOnField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Depends On field on a review request."""

    field_id = 'depends_on'
    label = _('Depends On')
    model = ReviewRequest
    model_name_attr = 'summary'

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.DependsOnFieldView'

    def render_change_entry_item_html(self, info, item):
        """Render an item for change description HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed.

            item (object):
                The value of the item.

        Returns:
            unicode:
            The rendered change entry.
        """
        item = ReviewRequest.objects.get(pk=item[2])

        rendered_item = format_html(
            '<a href="{url}">{id} - {summary}</a>',
            url=item.get_absolute_url(),
            id=item.pk,
            summary=item.summary)

        if item.status in (ReviewRequest.SUBMITTED,
                           ReviewRequest.DISCARDED):
            return '<s>%s</s>' % rendered_item
        else:
            return rendered_item

    def render_item(self, item):
        """Render an item from the list.

        Args:
            item (object):
                The item to render.

        Returns:
            unicode:
            The rendered item.
        """
        rendered_item = format_html(
            '<a href="{url}" title="{summary}"'
            '   class="review-request-link">{id}</a>',
            url=item.get_absolute_url(),
            summary=item.summary,
            id=item.display_id)

        if item.status in (ReviewRequest.SUBMITTED,
                           ReviewRequest.DISCARDED):
            return '<s>%s</s>' % rendered_item
        else:
            return rendered_item


class BlocksField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Blocks field on a review request."""

    field_id = 'blocks'
    label = _('Blocks')
    model = ReviewRequest

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        return review_request_details.get_review_request().get_blocks()

    @property
    def should_render(self):
        """Whether the field should be rendered."""
        return len(self.value) > 0

    def render_value(self, blocks):
        """Render the value in the field.

        Args:
            blocks (list):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        return format_html_join(
            ', ',
            '<a href="{0}" class="review-request-link">{1}</a>',
            [
                (item.get_absolute_url(), item.display_id)
                for item in blocks
            ])


class ChangeField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Change field on a review request.

    This is shown for repositories supporting changesets. The change
    number is similar to a commit ID, with the exception that it's only
    ever stored on the ReviewRequest and never changes.

    If both ``changenum`` and ``commit_id`` are provided on the review
    request, only this field will be shown, as both are likely to have
    values.
    """

    field_id = 'changenum'
    label = _('Change')

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        return review_request_details.get_review_request().changenum

    @property
    def should_render(self):
        """Whether the field should be rendered."""
        return bool(self.value)

    def render_value(self, changenum):
        """Render the value in the field.

        Args:
            changenum (unicode):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        review_request = self.review_request_details.get_review_request()

        is_pending, changenum = review_request.changeset_is_pending(changenum)

        if is_pending:
            return escape(_('%s (pending)') % changenum)
        else:
            return changenum


class CommitField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Commit field on a review request.

    This displays the ID of the commit the review request is representing.

    Since the ``commit_id`` and ``changenum`` fields are both populated, we
    let ChangeField take precedence. It knows how to render information based
    on a changeset ID.
    """

    field_id = 'commit_id'
    label = _('Commit')
    can_record_change_entry = True
    tag_name = 'span'

    @property
    def should_render(self):
        """Whether the field should be rendered."""
        return (bool(self.value) and
                not self.review_request_details.get_review_request().changenum)

    def render_value(self, commit_id):
        """Render the value in the field.

        Args:
            commit_id (unicode):
                The value to render.

        Returns:
            unicode:
            The rendered value.
        """
        # Abbreviate SHA-1s
        if len(commit_id) == 40:
            abbrev_commit_id = commit_id[:7] + '...'

            return '<span title="%s">%s</span>' % (escape(commit_id),
                                                   escape(abbrev_commit_id))
        else:
            return escape(commit_id)


class DiffField(ReviewRequestPageDataMixin, BuiltinFieldMixin,
                BaseReviewRequestField):
    """Represents a newly uploaded diff on a review request.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription population
    and processing steps.
    """

    field_id = 'diff'
    label = _('Diff')

    can_record_change_entry = True

    MAX_FILES_PREVIEW = 8

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
        added_diff_info = info['added'][0]
        review_request = self.review_request_details.get_review_request()

        try:
            diffset = self.data.diffsets_by_id[added_diff_info[2]]
        except KeyError:
            # If a published revision of a diff has been deleted from the
            # database, this will explode. Just return a blank string for this,
            # so that it doesn't show a traceback.
            return ''

        diff_revision = diffset.revision
        past_revision = diff_revision - 1
        diff_url = added_diff_info[1]

        s = []

        # Fetch the total number of inserts/deletes. These will be shown
        # alongside the diff revision.
        counts = diffset.get_total_line_counts()
        raw_insert_count = counts.get('raw_insert_count', 0)
        raw_delete_count = counts.get('raw_delete_count', 0)

        line_counts = []

        if raw_insert_count > 0:
            line_counts.append('<span class="insert-count">+%d</span>'
                               % raw_insert_count)

        if raw_delete_count > 0:
            line_counts.append('<span class="delete-count">-%d</span>'
                               % raw_delete_count)

        # Display the label, URL, and line counts for the diff.
        s.append(format_html(
            '<p class="diff-changes">'
            ' <a href="{url}">{label}</a>'
            ' <span class="line-counts">({line_counts})</span>'
            '</p>',
            url=diff_url,
            label=_('Revision %s') % diff_revision,
            count=_('%d files') % len(diffset.cumulative_files),
            line_counts=mark_safe(' '.join(line_counts))))

        if past_revision > 0:
            # This is not the first diff revision. Include an interdiff link.
            interdiff_url = local_site_reverse(
                'view-interdiff',
                local_site=review_request.local_site,
                args=[
                    review_request.display_id,
                    past_revision,
                    diff_revision,
                ])

            s.append(format_html(
                '<p><a href="{url}">{text}</a>',
                url=interdiff_url,
                text=_('Show changes')))

        file_count = len(diffset.cumulative_files)

        if file_count > 0:
            # Begin displaying the list of files modified in this diff.
            # It will be capped at a fixed number (MAX_FILES_PREVIEW).
            s += [
                '<div class="diff-index">',
                ' <table>',
            ]

            # We want a sorted list of filediffs, but tagged with the order in
            # which they come from the database, so that we can properly link
            # to the respective files in the diff viewer.
            files = get_sorted_filediffs(enumerate(diffset.cumulative_files),
                                         key=lambda i: i[1])

            for i, filediff in files[:self.MAX_FILES_PREVIEW]:
                counts = filediff.get_line_counts()

                data_attrs = [
                    'data-%s="%s"' % (attr.replace('_', '-'), counts[attr])
                    for attr in ('insert_count', 'delete_count',
                                 'replace_count', 'total_line_count')
                    if counts.get(attr) is not None
                ]

                s.append(format_html(
                    '<tr {data_attrs}>'
                    ' <td class="diff-file-icon"></td>'
                    ' <td class="diff-file-info">'
                    '  <a href="{url}">{filename}</a>'
                    ' </td>'
                    '</tr>',
                    data_attrs=mark_safe(' '.join(data_attrs)),
                    url=diff_url + '#%d' % i,
                    filename=filediff.source_file))

            num_remaining = file_count - self.MAX_FILES_PREVIEW

            if num_remaining > 0:
                # There are more files remaining than we've shown, so show
                # the count.
                s.append(format_html(
                    '<tr>'
                    ' <td></td>'
                    ' <td class="diff-file-info">{text}</td>'
                    '</tr>',
                    text=_('%s more') % num_remaining))

            s += [
                ' </table>',
                '</div>',
            ]

        return ''.join(s)

    def has_value_changed(self, old_value, new_value):
        """Return whether the value has changed.

        Args:
            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.

        Returns:
            bool:
            Whether the value of the field has changed.
        """
        # If there's a new diffset at all (in new_value), then it passes
        # the test.
        return new_value is not None

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            object:
            The loaded value.
        """
        # This will be None for a ReviewRequest, and may have a value for
        # ReviewRequestDraft if a new diff was attached.
        return getattr(review_request_details, 'diffset', None)

    def record_change_entry(self, changedesc, unused, diffset):
        """Record information on the changed values in a ChangeDescription.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the entry in.

            old_value (object):
                The old value of the field.

            new_value (object):
                The new value of the field.
        """
        review_request = self.review_request_details.get_review_request()

        url = local_site_reverse(
            'view-diff-revision',
            local_site=review_request.local_site,
            args=[review_request.display_id, diffset.revision])

        changedesc.fields_changed['diff'] = {
            'added': [(
                _('Diff r%s') % diffset.revision,
                url,
                diffset.pk
            )]
        }

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
        diffset_id = changedesc.fields_changed['diff']['added'][0][2]

        return {
            'added': DiffSet.objects.get(pk=diffset_id),
        }


class FileAttachmentCaptionsField(BaseCaptionsField):
    """Renders caption changes for file attachments.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """

    field_id = 'file_captions'
    label = _('File Captions')
    obj_map_attr = 'file_attachments_by_id'
    model = FileAttachment
    caption_object_field = 'file_attachment'


class FileAttachmentsField(ReviewRequestPageDataMixin, BuiltinFieldMixin,
                           BaseCommaEditableField):
    """Renders removed or added file attachments.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """

    field_id = 'files'
    label = _('Files')
    model = FileAttachment

    thumbnail_template = 'reviews/changedesc_file_attachment.html'

    def get_change_entry_sections_html(self, info):
        """Return sections of change entries with titles and rendered HTML.

        Args:
            info (dict):
                A dictionary describing how the field has changed. This is
                guaranteed to have ``new`` and ``old`` keys, but may also
                contain ``added`` and ``removed`` keys as well.

        Returns:
            list of dict:
            A list of the change entry sections.
        """
        sections = []

        if 'removed' in info:
            sections.append({
                'title': _('Removed Files'),
                'rendered_html': mark_safe(
                    self.render_change_entry_html(info['removed'])),
            })

        if 'added' in info:
            sections.append({
                'title': _('Added Files'),
                'rendered_html': mark_safe(
                    self.render_change_entry_html(info['added'])),
            })

        return sections

    def render_change_entry_html(self, values):
        """Render a change entry to HTML.

        This function is expected to return safe, valid HTML. Any values
        coming from a field or any other form of user input must be
        properly escaped.

        Args:
            info (list):
                A list of the changed file attachments. Each item is a 3-tuple
                containing the ``caption``, ``filename``, and the ``pk`` of the
                file attachment in the database.

        Returns:
            django.utils.safestring.SafeText:
            The HTML representation of the change entry.
        """
        # Fetch the template ourselves only once and render it for each item,
        # instead of calling render_to_string() in the loop, so we don't
        # have to locate and parse/fetch from cache for every item.

        template = get_template(self.thumbnail_template)
        review_request = self.review_request_details.get_review_request()

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        items = []

        for caption, filename, pk in values:
            if pk in self.data.file_attachments_by_id:
                attachment = self.data.file_attachments_by_id[pk]
            else:
                try:
                    attachment = FileAttachment.objects.get(pk=pk)
                except FileAttachment.DoesNotExist:
                    continue

            items.append(template.render({
                'model_attrs': self.get_attachment_js_model_attrs(attachment),
                'uuid': uuid.uuid4(),
            }))

        return mark_safe(''.join(items))

    def get_attachment_js_model_attrs(self, attachment, draft=False):
        """Return attributes for the RB.FileAttachment JavaScript model.

        This will determine the right attributes to pass to an instance
        of :js:class:`RB.FileAttachment`, based on the provided file
        attachment.

        Args:
            attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment to return attributes for.

            draft (bool, optional):
                Whether to return attributes for a draft version of the
                file attachment.

        Returns:
            dict:
            The resulting model attributes.
        """
        review_request = self.review_request_details.get_review_request()

        model_attrs = {
            'id': attachment.pk,
            'loaded': True,
            'downloadURL': attachment.get_absolute_url(),
            'filename': attachment.filename,
            'revision': attachment.attachment_revision,
            'thumbnailHTML': attachment.thumbnail,
        }

        if draft:
            caption = attachment.draft_caption
        else:
            caption = attachment.caption

        model_attrs['caption'] = caption

        if attachment.attachment_history_id:
            model_attrs['attachmentHistoryID'] = \
                attachment.attachment_history_id

        if self._has_usable_review_ui(review_request, attachment):
            model_attrs['reviewURL'] = local_site_reverse(
                'file-attachment',
                kwargs={
                    'file_attachment_id': attachment.pk,
                    'review_request_id': review_request.display_id,
                },
                request=self.request)

        return model_attrs

    def _has_usable_review_ui(self, review_request, file_attachment):
        """Return whether there's a usable review UI for a file attachment.

        This will check that a review UI exists for the file attachment and
        that it's enabled for the provided user and review request.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that the file attachment is on.

            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment that review UI would review.

        Returns:
            bool:
            ``True`` if a review UI exists and is usable. ``False`` if the
            review UI does not exist, cannot be used, or there's an error when
            checking.
        """
        review_ui = file_attachment.review_ui

        try:
            return (
                review_ui and
                review_ui.is_enabled_for(user=self.request.user,
                                         review_request=review_request,
                                         file_attachment=file_attachment))
        except Exception as e:
            logger.exception('Error when calling is_enabled_for with '
                             'FileAttachmentReviewUI %r: %s',
                             review_ui, e)
            return False


class ScreenshotCaptionsField(BaseCaptionsField):
    """Renders caption changes for screenshots.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """

    field_id = 'screenshot_captions'
    label = _('Screenshot Captions')
    obj_map_attr = 'screenshots_by_id'
    model = Screenshot
    caption_object_field = 'screenshot'


class ScreenshotsField(BaseCommaEditableField):
    """Renders removed or added screenshots.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """

    field_id = 'screenshots'
    label = _('Screenshots')
    model = Screenshot


class TargetGroupsField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Target Groups field on a review request."""

    field_id = 'target_groups'
    label = _('Groups')
    model = Group
    model_name_attr = 'name'

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.TargetGroupsFieldView'

    def render_item(self, group):
        """Render an item from the list.

        Args:
            item (object):
                The item to render.

        Returns:
            unicode:
            The rendered item.
        """
        return '<a href="%s">%s</a>' % (escape(group.get_absolute_url()),
                                        escape(group.name))


class TargetPeopleField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Target People field on a review request."""

    field_id = 'target_people'
    label = _('People')
    model = User
    model_name_attr = 'username'

    #: The class name for the JavaScript view representing this field.
    js_view_class = 'RB.ReviewRequestFields.TargetPeopleFieldView'

    def render_item(self, user):
        """Render an item from the list.

        Args:
            item (object):
                The item to render.

        Returns:
            unicode:
            The rendered item.
        """
        extra_classes = ['user']

        if not user.is_active:
            extra_classes.append('inactive')

        return format_html(
            '<a href="{0}" class="{1}">{2}</a>',
            local_site_reverse(
                'user',
                local_site=self.review_request_details.local_site,
                args=[user]),
            ' '.join(extra_classes),
            user.username)


class CommitListField(ReviewRequestPageDataMixin, BaseReviewRequestField):
    """The list of commits for a review request."""

    field_id = 'commit_list'
    label = _('Commits')

    is_editable = False

    js_view_class = 'RB.ReviewRequestFields.CommitListFieldView'

    @cached_property
    def review_request_created_with_history(self):
        """Whether the associated review request was created with history."""
        return (
            self.review_request_details
            .get_review_request()
            .created_with_history
        )

    @property
    def should_render(self):
        """Whether or not the field should be rendered.

        This field will only be rendered when the review request was created
        with history support. It is also hidden on the diff viewer page,
        because it substantially overlaps with the commit selector.
        """
        from reviewboard.urls import diffviewer_url_names
        url_name = self.request.resolver_match.url_name

        return (self.review_request_created_with_history and
                url_name not in diffviewer_url_names)

    @property
    def can_record_change_entry(self):
        """Whether or not the field can record a change entry.

        The field can only record a change entry when the review request has
        been created with history.
        """
        return self.review_request_created_with_history

    def load_value(self, review_request_details):
        """Load a value from the review request or draft.

        Args:
            review_request_details (review_request_details.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
            The DiffSet associated with the review request or draft.
        """
        return review_request_details.get_latest_diffset()

    def save_value(self, value):
        """Save a value to the review request.

        This is intentionally a no-op.

        Args:
            value (reviewboard.diffviewer.models.diffset.DiffSet, unused):
                The current DiffSet
        """
        pass

    def render_value(self, value):
        """Render the field for the given value.

        Args:
            value (int):
                The diffset primary key.

        returns:
            django.utils.safestring.SafeText:
            The rendered value.
        """
        if not value:
            return ''

        commits = list(
            DiffCommit.objects
            .filter(diffset_id=value)
            .order_by('id')
        )
        context = self._get_common_context(commits)
        context['commits'] = commits

        return render_to_string(
            template_name='reviews/commit_list_field.html',
            request=self.request,
            context=context)

    def has_value_changed(self, old_value, new_value):
        """Return whether or not the value has changed.

        Args:
            old_value (reviewboard.diffviewer.models.diffset.DiffSet):
                The primary key of the :py:class:`~reviewboard.diffviewer.
                models.diffset.DiffSet` from the review_request.

            new_value (reviewboard.diffviewer.models.diffset.DiffSet):
                The primary key of the :py:class:`~reviewboard.diffviewer.
                models.diffset.DiffSet` from the draft.

        Returns:
            bool:
            Whether or not the value has changed.
        """
        return new_value is not None

    def record_change_entry(self, changedesc, old_value, new_value):
        """Record the old and new values for this field into the changedesc.

        Args:
            changedesc (reviewboard.changedescs.models.ChangeDescription):
                The change description to record the change into.

            old_value (reviewboard.diffviewer.models.diffset.DiffSet):
                The previous :py:class:`~reviewboard.diffviewer.models.
                diffset.DiffSet` from the review request.

            new_value (reviewboard.diffviewer.models.diffset.DiffSet):
                The new :py:class:`~reviewboard.diffviewer.models.diffset.
                DiffSet` from the draft.
        """
        changedesc.fields_changed[self.field_id] = {
            'old': old_value.pk,
            'new': new_value.pk,
        }

    def render_change_entry_html(self, info):
        """Render the change entry HTML for this field.

        Args:
            info (dict):
                The change entry info for this field. See
                :py:meth:`record_change_entry` for the format.

        Returns:
            django.utils.safestring.SafeText:
            The rendered HTML.
        """
        commits = self.data.commits_by_diffset_id

        old_commits = commits[info['old']]
        new_commits = commits[info['new']]

        context = self._get_common_context(chain(old_commits, new_commits))
        context.update({
            'old_commits': old_commits,
            'new_commits': new_commits,
        })

        return render_to_string(
            template_name='reviews/changedesc_commit_list.html',
            request=self.request,
            context=context)

    def serialize_change_entry(self, changedesc):
        """Serialize the changed field entry for the web API.

        Args:
            changdesc (reviewboard.changedescs.models.ChangeDescription):
                The change description being serialized.

        Returns:
            dict:
            A JSON-serializable dictionary representing the change entry for
            this field.
        """
        info = changedesc.fields_changed[self.field_id]

        commits_by_diffset_id = DiffCommit.objects.by_diffset_ids(
            (info['old'], info['new']))

        return {
            key: [
                {
                    'author': commit.author_name,
                    'summary': commit.summary,
                }
                for commit in commits_by_diffset_id[info[key]]
            ]
            for key in ('old', 'new')
        }

    def _get_common_context(self, commits):
        """Return common context for rending both change entries and the field.

        Args:
            commits (iterable of reviewboard.diffviewer.models.diffcommit.
                     DiffCommit):
                The commits to generate context for.

        Returns:
            dict:
            A dictionary of context.
        """
        submitter_name = self.review_request_details.submitter.get_full_name()
        include_author_name = not submitter_name
        to_expand = set()

        for commit in commits:
            if commit.author_name != submitter_name:
                include_author_name = True

            if commit.summary.strip() != commit.commit_message.strip():
                to_expand.add(commit.pk)

        return {
            'include_author_name': include_author_name,
            'to_expand': to_expand,
        }


class MainFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = 'main'
    field_classes = [
        SummaryField,
        DescriptionField,
        TestingDoneField,
    ]


class ExtraFieldSet(BaseReviewRequestFieldSet):
    """A field set that is displayed after the main field set."""

    fieldset_id = 'extra'
    field_classes = [
        CommitListField,
    ]


class InformationFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = 'info'
    label = _('Information')
    field_classes = [
        OwnerField,
        RepositoryField,
        BranchField,
        BugsField,
        DependsOnField,
        BlocksField,
        ChangeField,
        CommitField,
    ]


class ReviewersFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = 'reviewers'
    label = _('Reviewers')
    show_required = True
    field_classes = [
        TargetGroupsField,
        TargetPeopleField,
    ]


class ChangeEntryOnlyFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = '_change_entries_only'
    field_classes = [
        DiffField,
        FileAttachmentCaptionsField,
        ScreenshotCaptionsField,
        FileAttachmentsField,
        ScreenshotsField,
        StatusField,
    ]


builtin_fieldsets = [
    MainFieldSet,
    ExtraFieldSet,
    InformationFieldSet,
    ReviewersFieldSet,
    ChangeEntryOnlyFieldSet,
]
