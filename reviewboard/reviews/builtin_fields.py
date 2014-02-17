from __future__ import unicode_literals

import logging

from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _

from reviewboard.reviews.fields import (BaseCommaEditableField,
                                        BaseEditableField,
                                        BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        BaseTextAreaField)
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
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
    always_render_markdown = True

    def is_text_markdown(self, value):
        return self.review_request_details.rich_text


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


class TestingDoneField(BuiltinTextAreaFieldMixin, BaseTextAreaField):
    """The Testing Done field on a review request."""
    field_id = 'testing_done'
    label = _('Testing Done')


class SubmitterField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Submitter field on a review request."""
    field_id = 'submitter'
    label = _('Submitter')

    def render_value(self, user):
        return ('<a class="user" href="%s">%s</a>'
                % (escape(user.get_absolute_url()),
                   escape(user.get_full_name() or user.username)))


class RepositoryField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Repository field on a review request."""
    field_id = 'repository'
    label = _('Repository')

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

    def load_value(self, review_request_details):
        return review_request_details.get_bug_list()

    def save_value(self, value):
        setattr(self.review_request_details, self.field_id, ', '.join(value))

    def render_item(self, bug_id):
        bug_url = self._get_bug_url(bug_id)

        if bug_url:
            return '<a href="%s">%s</a>' % (escape(bug_url), escape(bug_id))
        else:
            return escape(bug_id)

    def render_change_entry_item_html(self, info, item):
        return self.render_item(item[0])

    def _get_bug_url(self, bug_id):
        repository = self.review_request_details.repository

        if (repository and
            repository.bug_tracker and
            '%s' in repository.bug_tracker):
            try:
                return repository.bug_tracker % bug_id
            except TypeError:
                logging.error("Error creating bug URL. The bug tracker "
                              "URL '%s' is likely invalid.",
                              repository.bug_tracker)

        return None


class DependsOnField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Depends On field on a review request."""
    field_id = 'depends_on'
    label = _('Depends On')
    model_name_attr = 'summary'

    def render_change_entry_item_html(self, info, item):
        return self.render_item(ReviewRequest.objects.get(pk=item[2]))

    def render_item(self, item):
        rendered_item = (
            '<a href="%s">%s</a>'
            % (escape(item.get_absolute_url()), escape(item.display_id)))

        if item.status == ReviewRequest.SUBMITTED:
            return '<s>%s</s>' % rendered_item
        else:
            return rendered_item


class BlocksField(BuiltinFieldMixin, BaseReviewRequestField):
    """The Blocks field on a review request."""
    field_id = 'blocks'
    label = _('Blocks')

    def load_value(self, review_request_details):
        return review_request_details.get_review_request().get_blocks()

    def should_render(self, blocks):
        return len(blocks) > 0

    def render_value(self, blocks):
        return ', '.join([
            '<a href="%s">%s</a>' % (escape(item.get_absolute_url()),
                                     escape(item.display_id))
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

        if review_request.changeset_is_pending():
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
    locals_vars = ['diffset_versions']

    can_record_change_entry = True

    def render_change_entry_html(self, info):
        added_diff_info = info['added'][0]
        review_request = self.review_request_details.get_review_request()

        diff_revision = self.diffset_versions[added_diff_info[2]]
        past_revision = diff_revision - 1
        diff_url = added_diff_info[1]

        s = '<a href="%s">%s</a>' % (diff_url, added_diff_info[0])

        if past_revision != 0:
            interdiff_url = local_site_reverse('view-interdiff', args=[
                review_request.display_id,
                past_revision,
                diff_revision,
            ])

            s += ' - <a href="%s">%s</a>' % (interdiff_url, _('Show changes'))

        return '\n'.join([
            '<ul>',
            ' <li>%s</li>' % _('added %s' % s),
            '</ul>',
        ])

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

        if review_request.local_site:
            local_site_name = review_request.local_site_name
        else:
            local_site_name = None

        url = local_site_reverse(
            'view-diff-revision',
            local_site_name=local_site_name,
            args=[review_request.display_id, diffset.revision])

        changedesc.fields_changed['diff'] = {
            'added': [(
                _('Diff r%s') % diffset.revision,
                url,
                diffset.pk
            )]
        }


class TargetGroupsField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Target Groups field on a review request."""
    field_id = 'target_groups'
    label = _('Groups')
    model_name_attr = 'name'

    def render_item(self, group):
        return '<a href="%s">%s</a>' % (escape(group.get_absolute_url()),
                                        escape(group.name))


class TargetPeopleField(BuiltinFieldMixin, BaseModelListEditableField):
    """The Target People field on a review request."""
    field_id = 'target_people'
    label = _('People')
    model_name_attr = 'username'

    def render_item(self, user):
        extra_classes = ['user']

        if not user.is_active:
            extra_classes.append('inactive')

        return ('<a href="%s" class="%s">%s</a>'
                % (escape(user.get_absolute_url()),
                   ' '.join(extra_classes),
                   escape(user.username)))


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
    field_classes =[
        TargetGroupsField,
        TargetPeopleField,
    ]


class ChangeEntryOnlyFieldSet(BaseReviewRequestFieldSet):
    fieldset_id = '_change_entries_only'
    field_classes = [
        DiffField,
    ]


builtin_fieldsets = [
    MainFieldSet,
    InformationFieldSet,
    ReviewersFieldSet,
    ChangeEntryOnlyFieldSet,
]
