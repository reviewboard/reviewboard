from django import template
from django.conf import settings
from django.db.models import Q
from django.template import NodeList, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from djblets.util.decorators import basictag, blocktag
from djblets.util.misc import get_object_or_none
from djblets.util.templatetags.djblets_utils import humanize_list

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Comment, Group, ReviewRequest, \
                                       ScreenshotComment


register = template.Library()


@register.tag
@blocktag
def forcomment(context, nodelist, filediff, review=None):
    """
    Loops over a list of comments beloning to a filediff.

    This will populate a special ``comment`` variable for use in the content.
    This is of the type :model:`reviews.Comment`.
    """
    new_nodelist = NodeList()
    context.push()

    if not review:
        comments = filediff.comments.all()
    else:
        comments = filediff.comments.filter(review=review)

    for comment in comments:
        context['comment'] = comment

        for node in nodelist:
            new_nodelist.append(node.render(context))

    context.pop()
    return new_nodelist.render(context)


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
    if rid == None or rid < 1000:
        return ""

    ridstr = str(rid)
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
def commentcounts(context, filediff, interfilediff=None):
    """
    Returns a JSON array of current comments for a filediff, sorted by
    line number.

    Each entry in the array has a dictionary containing the following keys:

      =========== ==================================================
      Key         Description
      =========== ==================================================
      comment_id  The ID of the comment
      text        The text of the comment
      line        The first line number
      num_lines   The number of lines this comment spans
      user        A dictionary containing "username" and "name" keys
                  for the user
      url         The URL to the comment
      localdraft  True if this is the current user's draft comment
      =========== ==================================================
    """
    comment_dict = {}
    user = context.get('user', None)

    if interfilediff:
        query = Comment.objects.filter(filediff=filediff,
                                       interfilediff=interfilediff)
    else:
        query = Comment.objects.filter(filediff=filediff,
                                       interfilediff__isnull=True)

    for comment in query:
        review = get_object_or_none(comment.review)

        if review and (review.public or review.user == user):
            key = (comment.first_line, comment.num_lines)

            comment_dict.setdefault(key, []).append({
                'comment_id': comment.id,
                'text': comment.text,
                'line': comment.first_line,
                'num_lines': comment.num_lines,
                'user': {
                    'username': review.user.username,
                    'name': review.user.get_full_name() or review.user.username,
                },
                #'timestamp': comment.timestamp,
                'url': comment.get_review_url(),
                'localdraft': review.user == user and \
                              not review.public,
            })

    comments_array = []

    for key, value in comment_dict.iteritems():
        comments_array.append({
            'linenum': key[0],
            'num_lines': key[1],
            'comments': value,
        })

    comments_array.sort(cmp=lambda x, y: cmp(x['linenum'], y['linenum'] or
                                         cmp(x['num_lines'], y['num_lines'])))

    return simplejson.dumps(comments_array)


@register.tag
@basictag(takes_context=True)
def screenshotcommentcounts(context, screenshot):
    """
    Returns a JSON array of current comments for a screenshot.

    Each entry in the array has a dictionary containing the following keys:

      =========== ==================================================
      Key         Description
      =========== ==================================================
      text        The text of the comment
      localdraft  True if this is the current user's draft comment
      x           The X location of the comment's region
      y           The Y location of the comment's region
      w           The width of the comment's region
      h           The height of the comment's region
      =========== ==================================================
    """
    comments = {}
    user = context.get('user', None)

    for comment in screenshot.comments.all():
        review = get_object_or_none(comment.review)

        if review and (review.public or review.user == user):
            position = '%dx%d+%d+%d' % (comment.w, comment.h, \
                                        comment.x, comment.y)

            comments.setdefault(position, []).append({
                'id': comment.id,
                'text': comment.text,
                'user': {
                    'username': review.user.username,
                    'name': review.user.get_full_name() or review.user.username,
                },
                'url': comment.get_review_url(),
                'localdraft' : review.user == user and \
                               not review.public,
                'x' : comment.x,
                'y' : comment.y,
                'w' : comment.w,
                'h' : comment.h,
            })

    return simplejson.dumps(comments)


@register.tag
@basictag(takes_context=True)
def reply_list(context, review, comment, context_type, context_id):
    """
    Renders a list of comments of a specified type.

    This is a complex, confusing function accepts lots of inputs in order
    to display replies to a type of object. In each case, the replies will
    be rendered using the template :template:`reviews/review_reply.html`.

    If ``context_type`` is ``"comment"`` or ``"screenshot_comment"``,
    the generated list of replies are to ``comment``.

    If ``context_type`` is ``"body_top"`` or ```"body_bottom"``,
    the generated list of replies are to ``review``. Depending on the
    ``context_type``, these will either be replies to the top of the
    review body or to the bottom.

    The ``context_id`` parameter has to do with the internal IDs used by
    the JavaScript code for storing and categorizing the comments.
    """
    def generate_reply_html(reply, timestamp, text):
        return render_to_string('reviews/review_reply.html', {
            'context_id': context_id,
            'id': reply.id,
            'review': review,
            'timestamp': timestamp,
            'text': text,
            'reply_user': reply.user,
            'draft': not reply.public
        })

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

    user = context.get('user', None)
    if user.is_anonymous():
        user = None

    s = ""

    if context_type == "comment" or context_type == "screenshot_comment":
        for reply_comment in comment.public_replies(user):
            s += generate_reply_html(reply_comment.review.get(),
                                     reply_comment.timestamp,
                                     reply_comment.text)
    elif context_type == "body_top" or context_type == "body_bottom":
        q = Q(public=True)

        if user:
            q = q | Q(user=user)

        replies = getattr(review, "%s_replies" % context_type).filter(q)

        for reply in replies:
            s += generate_reply_html(reply, reply.timestamp,
                                     getattr(reply, context_type))

        return s
    else:
        raise TemplateSyntaxError, "Invalid context type passed"

    return s


@register.inclusion_tag('reviews/review_reply_section.html',
                        takes_context=True)
def reply_section(context, review, comment, context_type, context_id):
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
        context_id += str(comment.id)

    return {
        'review': review,
        'comment': comment,
        'context_type': context_type,
        'context_id': context_id,
        'user': context.get('user', None)
    }


@register.inclusion_tag('reviews/dashboard_entry.html', takes_context=True)
def dashboard_entry(context, level, text, view, group=None):
    """
    Renders an entry in the dashboard sidebar.

    This includes the name of the entry and the list of review requests
    associated with it. The entry is rendered by the template
    :template:`reviews/dashboard_entry.html`.
    """
    user = context.get('user', None)
    datagrid = context.get('datagrid', None)
    starred = False
    show_count = True
    count = 0

    if view == 'to-group':
        count = datagrid.counts['groups'].get(group.name, 0)
    elif view == 'watched-groups':
        starred = True
        show_count = False
    elif view in datagrid.counts:
        count = datagrid.counts[view]

        if view == 'starred':
            starred = True
    else:
        raise template.TemplateSyntaxError, \
            "Invalid view type '%s' passed to 'dashboard_entry' tag." % view

    return {
        'MEDIA_URL': settings.MEDIA_URL,
        'MEDIA_SERIAL': settings.MEDIA_SERIAL,
        'level': level,
        'text': text,
        'view': view,
        'group': group,
        'count': count,
        'show_count': show_count,
        'user': user,
        'starred': starred,
        'selected': context.get('view', None) == view and \
                    (not group or context.get('group', None) == group.name),
    }


@register.simple_tag
def reviewer_list(review_request):
    """
    Returns a humanized list of target reviewers in a review request.
    """
    return humanize_list([group.display_name or group.name \
                          for group in review_request.target_groups.all()] + \
                         [user.get_full_name() or user.username \
                          for user  in review_request.target_people.all()])


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


@register.filter
def diffsets_with_comments(review, current_pair):
    """
    Returns a list of diffsets in the review that contain draft comments.
    """
    if not review:
        return

    diffsets = DiffSet.objects.filter(files__comments__review=review)
    diffsets = diffsets.filter(files__comments__interfilediff__isnull=True)
    diffsets = diffsets.distinct()

    for diffset in diffsets:
        yield {
            'diffset': diffset,
            'is_current': current_pair[0] == diffset and
                          current_pair[1] == None,
        }


@register.filter
def interdiffs_with_comments(review, current_pair):
    """
    Returns a list of interdiffs in the review that contain draft comments.
    """
    if not review:
        return

    diffsets = DiffSet.objects.filter(files__comments__review=review)
    diffsets = diffsets.filter(files__comments__interfilediff__isnull=False)
    diffsets = diffsets.distinct()

    for diffset in diffsets:
        interdiffs = DiffSet.objects.filter(
            files__interdiff_comments__filediff__diffset=diffset).distinct()

        for interdiff in interdiffs:
            yield {
                'diffset': diffset,
                'interdiff': interdiff,
                'is_current': current_pair[0] == diffset and
                              current_pair[1] == interdiff,
            }


@register.filter
def has_comments_in_diffsets_excluding(review, diffset_pair):
    """
    Returns whether or not the specified review has any comments that
    aren't in the specified diffset or interdiff.
    """
    if not review:
        return False

    current_diffset, interdiff = diffset_pair

    # See if there are any diffsets with comments on them in this review.
    q = DiffSet.objects.filter(files__comments__review=review)
    q = q.filter(files__comments__interfilediff__isnull=True).distinct()

    if not interdiff:
        # The user is browsing a standard diffset, so filter it out.
        q = q.exclude(pk=current_diffset.id)

    if q.count() > 0:
        return True

    # See if there are any interdiffs with comments on them in this review.
    q = DiffSet.objects.filter(files__comments__review=review)
    q = q.filter(files__comments__interfilediff__isnull=False)

    if interdiff:
        # The user is browsing an interdiff, so filter it out.
        q = q.exclude(pk=current_diffset.id,
                      files__comments__interfilediff__diffset=interdiff)

    return q.count() > 0


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
            'id': obj.id
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
        raise template.TemplateSyntaxError, \
            "star tag received an incompatible object type (%s)" % \
            type(obj)

    if starred:
        image_alt = _("Starred")
    else:
        image_alt = _("Click to star")

    return render_to_string('reviews/star.html', {
        'object': obj_info,
        'starred': int(starred),
        'alt': image_alt,
        'user': user,
        'MEDIA_URL': settings.MEDIA_URL,
    })
