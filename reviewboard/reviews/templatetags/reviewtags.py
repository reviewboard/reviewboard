from __future__ import unicode_literals

import json
import logging

from django import template
from django.db.models import Q
from django.template import TemplateSyntaxError
from django.template.defaultfilters import escapejs, stringfilter
from django.template.loader import render_to_string
from django.utils import six
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.decorators import basictag, blocktag
from djblets.util.humanize import humanize_list

from reviewboard.accounts.models import Profile, Trophy
from reviewboard.diffviewer.diffutils import get_displayed_diff_line_ranges
from reviewboard.reviews.fields import (get_review_request_fieldset,
                                        get_review_request_fieldsets)
from reviewboard.reviews.markdown_utils import (is_rich_text_default_for_user,
                                                render_markdown,
                                                normalize_text_for_edit)
from reviewboard.reviews.models import (BaseComment, Group,
                                        ReviewRequest, ScreenshotComment,
                                        FileAttachmentComment)
from reviewboard.reviews.ui.base import FileAttachmentReviewUI


register = template.Library()


@register.tag
@basictag(takes_context=False)
def display_review_request_trophies(review_request):
    """Returns the HTML for the trophies awarded to a review request."""
    trophy_models = Trophy.objects.get_trophies(review_request)

    if not trophy_models:
        return ''

    trophies = []
    for trophy_model in trophy_models:
        try:
            trophy_type_cls = trophy_model.trophy_type
            trophy_type = trophy_type_cls()
            trophies.append({
                'image_url': trophy_type.image_url,
                'image_width': trophy_type.image_width,
                'image_height': trophy_type.image_height,
                'text': trophy_type.get_display_text(trophy_model),
            })
        except Exception as e:
            logging.error('Error when rendering trophy %r (%r): %s',
                          trophy_model.pk, trophy_type_cls, e,
                          exc_info=1)

    return render_to_string('reviews/trophy_box.html', {'trophies': trophies})


@register.tag
@blocktag
def ifneatnumber(context, nodelist, rid):
    """
    Returns whether or not the specified number is a "neat" number.
    This is a number with a special property, such as being a
    palindrome or having trailing zeroes.

    If the number is a neat number, the contained content is rendered,
    and two variables, ``milestone`` and ``palindrome`` are defined.
    """
    if rid is None or rid < 1000:
        return ""

    ridstr = six.text_type(rid)
    interesting = False

    context.push()
    context['milestone'] = False
    context['palindrome'] = False

    if rid >= 1000:
        trailing = ridstr[1:]
        if trailing == "0" * len(trailing):
            context['milestone'] = True
            interesting = True

    if not interesting:
        if ridstr == ''.join(reversed(ridstr)):
            context['palindrome'] = True
            interesting = True

    if not interesting:
        context.pop()
        return ""

    s = nodelist.render(context)
    context.pop()
    return s


@register.tag
@basictag(takes_context=True)
def file_attachment_comments(context, file_attachment):
    """Returns a JSON array of current comments for a file attachment."""
    review_ui = file_attachment.review_ui

    if not review_ui:
        # For the purposes of serialization, we'll create a dummy ReviewUI.
        review_ui = FileAttachmentReviewUI(file_attachment.review_request,
                                           file_attachment)

    # NOTE: We're setting this here because file attachments serialization
    #       requires this to be set, but we don't necessarily have it set
    #       by this time. We should rethink parts of this down the road, but
    #       it requires dealing with some compatibility issues for subclasses.
    review_ui.request = context['request']

    return json.dumps(review_ui.serialize_comments(
        file_attachment.get_comments()))


@register.tag
@basictag(takes_context=True)
def reply_list(context, entry, comment, context_type, context_id):
    """
    Renders a list of comments of a specified type.

    This is a complex, confusing function accepts lots of inputs in order
    to display replies to a type of object. In each case, the replies will
    be rendered using the template :template:`reviews/review_reply.html`.

    If ``context_type`` is ``"diff_comments"``, ``"screenshot_comments"``
    or ``"file_attachment_comments"``, the generated list of replies are to
    ``comment``.

    If ``context_type`` is ``"body_top"`` or ```"body_bottom"``,
    the generated list of replies are to ``review``. Depending on the
    ``context_type``, these will either be replies to the top of the
    review body or to the bottom.

    The ``context_id`` parameter has to do with the internal IDs used by
    the JavaScript code for storing and categorizing the comments.
    """
    def generate_reply_html(reply, timestamp, text, rich_text,
                            use_gravatars, comment_id=None):
        context.push()
        context.update({
            'context_id': context_id,
            'id': reply.id,
            'review': review,
            'timestamp': timestamp,
            'text': text,
            'reply_user': reply.user,
            'draft': not reply.public,
            'comment_id': comment_id,
            'rich_text': rich_text,
            'use_gravatars': use_gravatars,
        })

        result = render_to_string('reviews/review_reply.html', context)
        context.pop()

        return result

    def process_body_replies(queryset, attrname, user):
        if user.is_anonymous():
            queryset = queryset.filter(public=True)
        else:
            queryset = queryset.filter(Q(public=True) | Q(user=user))

        s = ""
        for reply_comment in queryset:
            s += generate_reply_html(reply, reply.timestamp,
                                     getattr(reply, attrname))

        return s

    siteconfig = SiteConfiguration.objects.get_current()
    use_gravatars = siteconfig.get('integration_gravatars')

    review = entry['review']

    user = context.get('user', None)
    if user.is_anonymous():
        user = None

    s = ""

    if context_type in ('diff_comments', 'screenshot_comments',
                        'file_attachment_comments'):
        for reply_comment in comment.public_replies(user):
            s += generate_reply_html(reply_comment.get_review(),
                                     reply_comment.timestamp,
                                     reply_comment.text,
                                     reply_comment.rich_text,
                                     use_gravatars,
                                     reply_comment.pk)
    elif context_type == "body_top" or context_type == "body_bottom":
        replies = getattr(review, "public_%s_replies" % context_type)()

        for reply in replies:
            s += generate_reply_html(
                reply,
                reply.timestamp,
                getattr(reply, context_type),
                getattr(reply, '%s_rich_text' % context_type),
                use_gravatars)

        return s
    else:
        raise TemplateSyntaxError("Invalid context type passed")

    return s


@register.inclusion_tag('reviews/review_reply_section.html',
                        takes_context=True)
def reply_section(context, entry, comment, context_type, context_id,
                  reply_to_text=''):
    """
    Renders a template for displaying a reply.

    This takes the same parameters as :tag:`reply_list`. The template
    rendered by this function, :template:`reviews/review_reply_section.html`,
    is responsible for invoking :tag:`reply_list` and as such passes these
    variables through. It does not make use of them itself.
    """
    if comment != "":
        if type(comment) is ScreenshotComment:
            context_id += 's'
        elif type(comment) is FileAttachmentComment:
            context_id += 'f'

        context_id += six.text_type(comment.id)

    return {
        'entry': entry,
        'comment': comment,
        'context_type': context_type,
        'context_id': context_id,
        'user': context.get('user', None),
        'local_site_name': context.get('local_site_name'),
        'reply_to_is_empty': reply_to_text == '',
        'request': context['request'],
    }


@register.inclusion_tag('datagrids/dashboard_entry.html', takes_context=True)
def dashboard_entry(context, level, text, view, param=None):
    """
    Renders an entry in the dashboard sidebar.

    This includes the name of the entry and the list of review requests
    associated with it. The entry is rendered by the template
    :template:`datagrids/dashboard_entry.html`.
    """
    user = context.get('user', None)
    sidebar_counts = context.get('sidebar_counts', None)
    starred = False
    show_count = True
    count = 0
    url = None
    group_name = None

    if view == 'to-group':
        group_name = param
        count = sidebar_counts['groups'].get(
            group_name,
            sidebar_counts['starred_groups'].get(group_name, 0))
    elif view == 'watched-groups':
        starred = True
        show_count = False
    elif view in sidebar_counts:
        count = sidebar_counts[view]

        if view == 'starred':
            starred = True
    elif view == "url":
        url = param
        show_count = False
    else:
        raise template.TemplateSyntaxError(
            "Invalid view type '%s' passed to 'dashboard_entry' tag." % view)

    return {
        'level': level,
        'text': text,
        'view': view,
        'group_name': group_name,
        'url': url,
        'count': count,
        'show_count': show_count,
        'user': user,
        'starred': starred,
        'selected': (context.get('view', None) == view and
                     (not group_name or
                      context.get('group', None) == group_name)),
        'local_site_name': context.get('local_site_name'),
    }


@register.simple_tag
def reviewer_list(review_request):
    """
    Returns a humanized list of target reviewers in a review request.
    """
    return humanize_list([group.display_name or group.name
                          for group in review_request.target_groups.all()] +
                         [user.get_full_name() or user.username
                          for user in review_request.target_people.all()])


@register.tag
@blocktag(end_prefix='end_')
def for_review_request_field(context, nodelist, review_request_details,
                             fieldset):
    """Loops through all fields in a fieldset.

    This can take a fieldset instance or a fieldset ID.
    """
    s = []

    request = context.get('request')

    if isinstance(fieldset, six.text_type):
        fieldset = get_review_request_fieldset(fieldset)

    for field_cls in fieldset.field_classes:
        try:
            field = field_cls(review_request_details, request=request)
        except Exception as e:
            logging.exception('Error instantiating field %r: %s',
                              field_cls, e)
            continue

        try:
            if field.should_render(field.value):
                context.push()
                context['field'] = field
                s.append(nodelist.render(context))
                context.pop()
        except Exception as e:
            logging.exception(
                'Error running should_render for field %r: %s',
                field_cls, e)

    return ''.join(s)


@register.tag
@blocktag(end_prefix='end_')
def for_review_request_fieldset(context, nodelist, review_request_details):
    """Loops through all fieldsets.

    This skips the "main" fieldset, as that's handled separately by the
    template.
    """
    s = []
    is_first = True
    review_request = review_request_details.get_review_request()
    user = context['request'].user
    fieldset_classes = get_review_request_fieldsets(include_main=False)

    for fieldset_cls in fieldset_classes:
        try:
            if not fieldset_cls.is_empty():
                try:
                    fieldset = fieldset_cls(review_request_details)
                except Exception as e:
                    logging.error('Error instantiating ReviewRequestFieldset '
                                  '%r: %s', fieldset_cls, e, exc_info=1)

                context.push()
                context.update({
                    'fieldset': fieldset,
                    'show_fieldset_required': (
                        fieldset.show_required and
                        review_request.status ==
                            ReviewRequest.PENDING_REVIEW and
                        review_request.is_mutable_by(user)),
                    'forloop': {
                        'first': is_first,
                    }
                })
                s.append(nodelist.render(context))
                context.pop()

                is_first = False
        except Exception as e:
            logging.error('Error running is_empty for ReviewRequestFieldset '
                          '%r: %s', fieldset_cls, e, exc_info=1)

    return ''.join(s)


@register.assignment_tag
def has_usable_review_ui(user, review_request, file_attachment):
    """Returns whether a review UI is set and can be used."""
    review_ui = file_attachment.review_ui

    try:
        return (review_ui and
                review_ui.is_enabled_for(user=user,
                                         review_request=review_request,
                                         file_attachment=file_attachment))
    except Exception as e:
        logging.error('Error when calling is_enabled_for '
                      'FileAttachmentReviewUI %r: %s',
                      review_ui, e, exc_info=1)
        return False


@register.filter
def bug_url(bug_id, review_request):
    """
    Returns the URL based on a bug number on the specified review request.

    If the repository the review request belongs to doesn't have an
    associated bug tracker, this returns None.
    """
    if (review_request.repository and
        review_request.repository.bug_tracker and
        '%s' in review_request.repository.bug_tracker):
        try:
            return review_request.repository.bug_tracker % bug_id
        except TypeError:
            logging.error("Error creating bug URL. The bug tracker URL '%s' "
                          "is likely invalid." %
                          review_request.repository.bug_tracker)

    return None


@register.tag
@basictag(takes_context=True)
def star(context, obj):
    """
    Renders the code for displaying a star used for starring items.

    The rendered code should handle click events so that the user can
    toggle the star. The star is rendered by the template
    :template:`reviews/star.html`.

    The passed object must be either a :model:`reviews.ReviewRequest` or
    a :model:`reviews.Group`.
    """
    return render_star(context.get('user', None), obj)


def render_star(user, obj):
    """
    Does the actual work of rendering the star. The star tag is a wrapper
    around this.
    """
    if user.is_anonymous():
        return ""

    profile = None

    if not hasattr(obj, 'starred'):
        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            return ""

    if isinstance(obj, ReviewRequest):
        obj_info = {
            'type': 'reviewrequests',
            'id': obj.display_id
        }

        if hasattr(obj, 'starred'):
            starred = obj.starred
        else:
            starred = \
                profile.starred_review_requests.filter(pk=obj.id).count() > 0
    elif isinstance(obj, Group):
        obj_info = {
            'type': 'groups',
            'id': obj.name
        }

        if hasattr(obj, 'starred'):
            starred = obj.starred
        else:
            starred = \
                profile.starred_groups.filter(pk=obj.id).count() > 0
    else:
        raise template.TemplateSyntaxError(
            "star tag received an incompatible object type (%s)" %
            type(obj))

    if starred:
        image_alt = _("Starred")
    else:
        image_alt = _("Click to star")

    return render_to_string('reviews/star.html', {
        'object': obj_info,
        'starred': int(starred),
        'alt': image_alt,
        'user': user,
    })


@register.inclusion_tag('reviews/comment_issue.html',
                        takes_context=True)
def comment_issue(context, review_request, comment, comment_type):
    """
    Renders the code responsible for handling comment issue statuses.
    """

    issue_status = BaseComment.issue_status_to_string(comment.issue_status)
    user = context.get('user', None)

    return {
        'comment': comment,
        'comment_type': comment_type,
        'issue_status': issue_status,
        'review': comment.get_review(),
        'interactive': comment.can_change_issue_status(user),
    }


@register.filter
@stringfilter
def pretty_print_issue_status(status):
    """Turns an issue status code into a human-readable status string."""
    return BaseComment.issue_status_to_string(status)


@register.filter
@stringfilter
def issue_status_icon(status):
    """Return an icon name for the issue status.

    Args:
        status (unicode):
            The stored issue status for the comment.

    Returns:
        unicode: The icon name for the issue status.
    """
    if status == BaseComment.OPEN:
        return 'rb-icon-issue-open'
    elif status == BaseComment.RESOLVED:
        return 'rb-icon-issue-resolved'
    elif status == BaseComment.DROPPED:
        return 'rb-icon-issue-dropped'
    else:
        raise ValueError('Unknown comment issue status "%s"' % status)


@register.filter('render_markdown')
def _render_markdown(text, is_rich_text):
    if is_rich_text:
        return mark_safe(render_markdown(text))
    else:
        return text


@register.tag
@basictag(takes_context=True)
def expand_fragment_link(context, expanding, tooltip,
                         expand_above, expand_below, text=None):
    """Renders a diff comment fragment expansion link.

    This link will expand the context by the supplied `expanding_above` and
    `expanding_below` values.

    `expanding` is expected to be one of 'above', 'below', or 'line'."""

    lines_of_context = context['lines_of_context']

    image_class = 'rb-icon-diff-expand-%s' % expanding
    expand_pos = (lines_of_context[0] + expand_above,
                  lines_of_context[1] + expand_below)

    return render_to_string('reviews/expand_link.html', {
        'tooltip': tooltip,
        'text': text,
        'comment_id': context['comment'].id,
        'expand_pos': expand_pos,
        'image_class': image_class,
    })


@register.tag
@basictag(takes_context=True)
def expand_fragment_header_link(context, header):
    """Render a diff comment fragment header expansion link.

    This link expands the context to contain the given line number.
    """
    lines_of_context = context['lines_of_context']
    offset = context['first_line'] - header['line']

    return render_to_string('reviews/expand_link.html', {
        'tooltip': _('Expand to header'),
        'text': format_html('<code>{0}</code>', header['text']),
        'comment_id': context['comment'].id,
        'expand_pos': (lines_of_context[0] + offset,
                       lines_of_context[1]),
        'image_class': 'rb-icon-diff-expand-header',
    })


@register.tag('normalize_text_for_edit')
@basictag(takes_context=True)
def _normalize_text_for_edit(context, text, rich_text, escape_js=False):
    text = normalize_text_for_edit(context['request'].user, text, rich_text,
                                   escape_html=not escape_js)

    if escape_js:
        text = escapejs(text)

    return text


@register.tag
@basictag(takes_context=True)
def rich_text_classname(context, rich_text):
    if rich_text or is_rich_text_default_for_user(context['request'].user):
        return 'rich-text'

    return ''


@register.tag
@basictag(takes_context=True)
def diff_comment_line_numbers(context, chunks, comment):
    """Render the changed line number ranges for a diff, for use in e-mail.

    This will display the original and patched line ranges covered by a
    comment, transforming the comment's stored virtual line ranges into
    human-readable ranges. It's intended for use in e-mail.

    The template tag's output will list the original line ranges only if
    there are ranges to show, and same with the patched line ranges.

    Args:
        context (django.template.Context):
            The template context.

        chunks (list):
            The list of chunks for the diff.

        comment (reviewboard.reviews.models.diff_comment.Comment):
            The comment containing the line ranges.

    Returns:
        unicode:
        A string representing the line ranges for the comment.
    """
    if comment.first_line is None:
        # Comments without a line number represent the entire file.
        return ''

    orig_range_info, patched_range_info = get_displayed_diff_line_ranges(
        chunks, comment.first_line, comment.last_line)

    if orig_range_info:
        orig_start_linenum, orig_end_linenum = \
            orig_range_info['display_range']

        if orig_start_linenum == orig_end_linenum:
            orig_lines_str = '%s' % orig_start_linenum
            orig_lines_prefix = 'Line'
        else:
            orig_lines_str = '%s-%s' % (orig_start_linenum, orig_end_linenum)
            orig_lines_prefix = 'Lines'
    else:
        orig_lines_str = None
        orig_lines_prefix = None

    if patched_range_info:
        patched_start_linenum, patched_end_linenum = \
            patched_range_info['display_range']

        if patched_start_linenum == patched_end_linenum:
            patched_lines_str = '%s' % patched_start_linenum
            patched_lines_prefix = 'Lines'
        else:
            patched_lines_str = '%s-%s' % (patched_start_linenum,
                                           patched_end_linenum)
            patched_lines_prefix = 'Lines'
    else:
        patched_lines_str = None
        patched_lines_prefix = None

    if orig_lines_str and patched_lines_str:
        return '%s %s (original), %s (patched)' % (
            orig_lines_prefix, orig_lines_str, patched_lines_str)
    elif orig_lines_str:
        return '%s %s (original)' % (orig_lines_prefix, orig_lines_str)
    elif patched_lines_str:
        return '%s %s (patched)' % (patched_lines_prefix, patched_lines_str)
    else:
        return ''
