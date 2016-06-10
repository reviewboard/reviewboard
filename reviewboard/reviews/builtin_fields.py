from __future__ import unicode_literals

import uuid

from django.contrib.auth.models import User
from django.core.urlresolvers import NoReverseMatch
from django.db import models
from django.template.loader import Context, get_template
from django.utils import six
from django.utils.html import escape, format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.diffutils import get_sorted_filediffs
from reviewboard.diffviewer.models import DiffSet
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


class BuiltinFieldMixin(object):
    """Mixin for built-in fields.

    This overrides some functions to work with native fields on a
    ReviewRequest or ReviewRequestDraft, rather than working with those
    stored in extra_data.
    """
    def __init__(self, *args, **kwargs):
        super(BuiltinFieldMixin, self).__init__(*args, **kwargs)

        if (not hasattr(self.review_request_details, self.field_id) and
            isinstance(self.review_request_details, ReviewRequestDraft)):
            # This field only exists in ReviewRequest, and not in
            # the draft, so we're going to work there instead.
            self.review_request_details = \
                self.review_request_details.get_review_request()

    def load_value(self, review_request_details):
        value = getattr(review_request_details, self.field_id)

        if isinstance(value, models.Manager):
            value = list(value.all())

        return value

    def save_value(self, value):
        setattr(self.review_request_details, self.field_id, value)


class BuiltinTextAreaFieldMixin(BuiltinFieldMixin):
    """Mixin for built-in text area fields.

    This will ensure that the text is always rendered in Markdown,
    no matter whether the source text is plain or Markdown. It will
    still escape the text if it's not in Markdown format before
    rendering.
    """
    def get_data_attributes(self):
        attrs = super(BuiltinTextAreaFieldMixin, self).get_data_attributes()

        # This is already available in the review request state fed to the
        # page, so we don't need it in the data attributes as well.
        attrs.pop('raw-value', None)

        return attrs


class BuiltinLocalsFieldMixin(BuiltinFieldMixin):
    """Mixin for internal fields needing access to local variables.

    These are used by fields that operate on state generated when
    creating the review request page. The view handling that page has
    a lot of cached variables, which the fields need access to for
    performance reasons.

    This should not be used by any classes outside this file.

    By default, this will not render or handle any value loading or change
    entry recording. Subclasses must implement those manually.
    """
    #: A list of variables needed from the review_detail view's locals().
    locals_vars = []

    def __init__(self, review_request_details, locals_vars={},
                 *args, **kwargs):
        super(BuiltinLocalsFieldMixin, self).__init__(
            review_request_details, *args, **kwargs)

        for var in self.locals_vars:
            setattr(self, var, locals_vars.get(var, None))

    def should_render(self, value):
        return False

    def load_value(self, review_request_details):
        return None

    def record_change_entry(self, changedesc, old_value, new_value):
        return None


class BaseCaptionsField(BuiltinLocalsFieldMixin, BaseReviewRequestField):
    """Base class for rendering captions for attachments.

    This serves as a base for FileAttachmentCaptionsField and
    ScreenshotCaptionsField. It provides the base rendering and
    for caption changes on file attachments or screenshots.
    """
    obj_map_attr = None
    caption_object_field = None

    change_entry_renders_inline = False

    def render_change_entry_html(self, info):
        render_item = super(BaseCaptionsField, self).render_change_entry_html
        obj_map = getattr(self, self.obj_map_attr)

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
        old_values = set([obj.pk for obj in old_value])
        new_values = set([obj.pk for obj in new_value])

        return old_values.symmetric_difference(new_values)

    def record_change_entry(self, changedesc, old_value, new_value):
        changedesc.record_field_change(self.field_id, old_value, new_value,
                                       self.model_name_attr)

    def render_change_entry_item_html(self, info, item):
        label, url, pk = item

        if url:
            return '<a href="%s">%s</a>' % (escape(url), escape(label))
        else:
            return escape(label)

    def save_value(self, value):
        setattr(self, self.field_id, value)


class StatusField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Status field on a review request."""

    field_id = 'status'
    label = _('Status')
    is_required = True

    def should_render(self, status):
        """Return whether this field should be rendered.

        This field is "rendered" by displaying the publish and close banners,
        and doesn't have a real field within the fieldsets.
        """
        return False

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

    def should_render(self, summary):
        # This field is rendered separately in the template, and isn't
        # included with other fields in the "main" group, so just don't
        # render it there.
        return False


class DescriptionField(BuiltinTextAreaFieldMixin, BaseTextAreaField):
    """The Description field on a review request."""
    field_id = 'description'
    label = _('Description')
    is_required = True

    def is_text_markdown(self, value):
        return self.review_request_details.description_rich_text


class TestingDoneField(BuiltinTextAreaFieldMixin, BaseTextAreaField):
    """The Testing Done field on a review request."""
    field_id = 'testing_done'
    label = _('Testing Done')

    def is_text_markdown(self, value):
        return self.review_request_details.testing_done_rich_text


class SubmitterField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Submitter field on a review request."""
    field_id = 'submitter'
    label = _('Submitter')
    model = User

    def render_value(self, user):
        return format_html(
            '<a class="user" href="{0}">{1}</a>',
            local_site_reverse(
                'user',
                local_site=self.review_request_details.local_site,
                args=[user]),
            user.get_full_name() or user.username)


class RepositoryField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Repository field on a review request."""
    field_id = 'repository'
    label = _('Repository')
    model = Repository

    def should_render(self, value):
        review_request = self.review_request_details.get_review_request()

        return review_request.repository_id is not None


class BranchField(BuiltinFieldMixin, BaseEditableField):
    """The Branch field on a review request."""
    field_id = 'branch'
    label = _('Branch')


class BugsField(BuiltinFieldMixin, BaseCommaEditableField):
    """The Bugs field on a review request."""
    field_id = 'bugs_closed'
    label = _('Bugs')

    one_line_per_change_entry = False

    def load_value(self, review_request_details):
        return review_request_details.get_bug_list()

    def save_value(self, value):
        setattr(self.review_request_details, self.field_id, ', '.join(value))

    def render_item(self, bug_id):
        bug_url = self._get_bug_url(bug_id)

        if bug_url:
            return format_html('<a class="bug" href="{url}">{id}</a>',
                               url=bug_url, id=bug_id)
        else:
            return escape(bug_id)

    def render_change_entry_item_html(self, info, item):
        return self.render_item(item[0])

    def _get_bug_url(self, bug_id):
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

    def render_change_entry_item_html(self, info, item):
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
        rendered_item = format_html(
            '<a href="{url}" title="{summary}">{id}</a>',
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
        return review_request_details.get_review_request().get_blocks()

    def should_render(self, blocks):
        return len(blocks) > 0

    def render_value(self, blocks):
        return format_html_join(
            ', ',
            '<a href="{0}">{1}</a>',
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
        return review_request_details.get_review_request().changenum

    def should_render(self, changenum):
        return bool(changenum)

    def render_value(self, changenum):
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

    def should_render(self, commit_id):
        return (bool(commit_id) and
                not self.review_request_details.get_review_request().changenum)

    def render_value(self, commit_id):
        # Abbreviate SHA-1s
        if len(commit_id) == 40:
            abbrev_commit_id = commit_id[:7] + '...'

            return '<span title="%s">%s</span>' % (escape(commit_id),
                                                   escape(abbrev_commit_id))
        else:
            return escape(commit_id)


class DiffField(BuiltinLocalsFieldMixin, BaseReviewRequestField):
    """Represents a newly uploaded diff on a review request.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription population
    and processing steps.
    """
    field_id = 'diff'
    label = _('Diff')
    locals_vars = ['diffsets_by_id']

    can_record_change_entry = True

    MAX_FILES_PREVIEW = 8

    def render_change_entry_html(self, info):
        added_diff_info = info['added'][0]
        review_request = self.review_request_details.get_review_request()

        try:
            diffset = self.diffsets_by_id[added_diff_info[2]]
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
            count=_('%d files') % diffset.file_count,
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

        if diffset.file_count > 0:
            # Begin displaying the list of files modified in this diff.
            # It will be capped at a fixed number (MAX_FILES_PREVIEW).
            s += [
                '<div class="diff-index">',
                ' <table>',
            ]

            # We want a sorted list of filediffs, but tagged with the order in
            # which they come from the database, so that we can properly link
            # to the respective files in the diff viewer.
            files = get_sorted_filediffs(enumerate(diffset.files.all()),
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

            num_remaining = diffset.file_count - self.MAX_FILES_PREVIEW

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
        # If there's a new diffset at all (in new_value), then it passes
        # the test.
        return new_value is not None

    def load_value(self, review_request_details):
        # This will be None for a ReviewRequest, and may have a value for
        # ReviewRequestDraft if a new diff was attached.
        return getattr(review_request_details, 'diffset', None)

    def record_change_entry(self, changedesc, unused, diffset):
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
    obj_map_attr = 'file_attachment_id_map'
    locals_vars = [obj_map_attr]
    model = FileAttachment
    caption_object_field = 'file_attachment'


class FileAttachmentsField(BuiltinLocalsFieldMixin, BaseCommaEditableField):
    """Renders removed or added file attachments.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """
    field_id = 'files'
    label = _('Files')
    locals_vars = ['file_attachment_id_map']
    model = FileAttachment

    thumbnail_template = 'reviews/changedesc_file_attachment.html'

    def get_change_entry_sections_html(self, info):
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
            if pk in self.file_attachment_id_map:
                attachment = self.file_attachment_id_map[pk]
            else:
                try:
                    attachment = FileAttachment.objects.get(pk=pk)
                except FileAttachment.DoesNotExist:
                    continue

            items.append(template.render(Context({
                'file': attachment,
                'review_request': review_request,
                'local_site_name': local_site_name,
                'request': self.request,
                'uuid': uuid.uuid4(),
            })))

        return ''.join(items)


class ScreenshotCaptionsField(BaseCaptionsField):
    """Renders caption changes for screenshots.

    This is not shown as an actual displayable field on the review request
    itself. Instead, it is used only during the ChangeDescription rendering
    stage. It is not, however, used for populating entries in
    ChangeDescription.
    """
    field_id = 'screenshot_captions'
    label = _('Screenshot Captions')
    obj_map_attr = 'screenshot_id_map'
    locals_vars = [obj_map_attr]
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

    def render_item(self, group):
        return '<a href="%s">%s</a>' % (escape(group.get_absolute_url()),
                                        escape(group.name))


class TargetPeopleField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Target People field on a review request."""
    field_id = 'target_people'
    label = _('People')
    model = User
    model_name_attr = 'username'

    def render_item(self, user):
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


class MainFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = 'main'
    field_classes = [
        SummaryField,
        DescriptionField,
        TestingDoneField,
    ]


class InformationFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = 'info'
    label = _('Information')
    field_classes = [
        SubmitterField,
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
    InformationFieldSet,
    ReviewersFieldSet,
    ChangeEntryOnlyFieldSet,
]
