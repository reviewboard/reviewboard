from django import template
from django.db.models import Q
from django.db.models.query import QuerySet
from django.template import NodeList, TemplateSyntaxError, Variable, \
                            VariableDoesNotExist
from django.template.loader import render_to_string
from django.template.defaultfilters import escape
from django.utils import simplejson
from django.utils.html import conditional_escape
from djblets.util.decorators import blocktag
from djblets.util.misc import get_object_or_none

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Comment, Group, ReviewRequest, \
                                       ReviewRequestDraft, ScreenshotComment
from reviewboard.utils.templatetags.htmlutils import humanize_list

register = template.Library()


class ReviewSummary(template.Node):
    def __init__(self, review_request):
        self.review_request = Variable(review_request)

    def render(self, context):
        try:
            review_request = self.review_request.resolve(context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to reviewsummary tag." % \
                self.review_request

        summary = conditional_escape(review_request.summary)

        if review_request.submitter == context.get('user', None):
            try:
                draft = review_request.reviewrequestdraft_set.get()
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       summary
            except ReviewRequestDraft.DoesNotExist:
                pass

            if not review_request.public:
                # XXX Do we want to say "Draft?"
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       summary

        if review_request.status == 'S':
            return "<span class=\"draftlabel\">[Submitted]</span> " + \
                   summary

        return summary


@register.tag
def reviewsummary(parser, token):
    """
    Returns the summary of a review, showing draft or submitted labels
    if need be.
    """
    try:
        tag_name, review_request = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a timestamp"

    return ReviewSummary(review_request)


@register.simple_tag
def pendingreviewcount(obj):
    """
    Returns the pending review count in a list of review requests belonging
    to the specified object.
    """
    return str(obj.reviewrequest_set.filter(public=True, status='P').count())


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
        comments = filediff.comment_set.all()
    else:
        comments = filediff.comment_set.filter(review=review)

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
@blocktag
def ifnewreviews(context, nodelist, review_request):
    """
    Renders content if a review request has new reviews that the current
    user has not seen.
    """
    if review_request.get_new_reviews(context["user"]).count() > 0:
        return nodelist.render(context)

    return ""


class CommentCounts(template.Node):
    def __init__(self, filediff, interfilediff):
        self.filediff = Variable(filediff)
        self.interfilediff = Variable(interfilediff)

    def render(self, context):
        try:
            filediff = self.filediff.resolve(context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to commentcounts tag." % \
                self.filediff

        try:
            interfilediff = self.interfilediff.resolve(context)
        except VariableDoesNotExist:
            interfilediff = None

        comments = {}
        user = context.get('user', None)

        if interfilediff:
            query = Comment.objects.filter(filediff=filediff,
                                           interfilediff=interfilediff)
        else:
            query = Comment.objects.filter(filediff=filediff,
                                           interfilediff__isnull=True)

        for comment in query:
            if comment.review_set.count() > 0:
                review = comment.review_set.get()
                if review.public or review.user == user:
                    line = comment.first_line

                    if not comments.has_key(line):
                        comments[line] = []

                    comments[line].append({
                        'text': comment.text,
                        'localdraft': review.user == user and \
                                      not review.public,
                    })

        return simplejson.dumps(comments)


@register.tag
def commentcounts(parser, token):
    """
    Returns a JSON array of current comments for a filediff.

    Each entry in the array has a dictionary containing the following keys:

      =========== ==================================================
      Key         Description
      =========== ==================================================
      text        The text of the comment
      localdraft  True if this is the current user's draft comment
      =========== ==================================================
    """
    try:
        tag_name, filediff, interfilediff = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a filediff and interfilediff"

    return CommentCounts(filediff, interfilediff)


class ScreenshotCommentCounts(template.Node):
    def __init__(self, screenshot):
        self.screenshot = Variable(screenshot)

    def render(self, context):
        try:
            screenshot = self.screenshot.resolve(context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to screenshotcommentcounts tag." % \
                self.screenshot

        comments = {}
        user = context.get('user', None)

        for comment in screenshot.screenshotcomment_set.all():
            if comment.review_set.count() > 0:
                review = comment.review_set.get()
                if review.public or review.user == user:
                    position = '%dx%d+%d+%d' % (comment.w, comment.h, \
                                                comment.x, comment.y)

                    if not comments.has_key(position):
                        comments[position] = []

                    comments[position].append({
                        'text': comment.text,
                        'localdraft' : review.user == user and \
                                       not review.public,
                        'x' : comment.x,
                        'y' : comment.y,
                        'w' : comment.w,
                        'h' : comment.h,
                    })

        return simplejson.dumps(comments)


@register.tag
def screenshotcommentcounts(parser, token):
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
    try:
        tag_name, screenshot = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a screenshot"

    return ScreenshotCommentCounts(screenshot)


class ReplyList(template.Node):
    def __init__(self, review, comment, context_type, context_id):
        self.review = Variable(review)
        self.comment = Variable(comment)
        self.context_type = Variable(context_type)
        self.context_id = Variable(context_id)

    def render(self, context):
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
                queryset = queryset.filter(Q(public=True))
            else:
                queryset = queryset.filter(Q(public=True) | Q(user=user))

            s = ""
            for reply_comment in queryset:
                s += generate_reply_html(reply, reply.timestamp,
                                         getattr(reply, attrname))

            return s

        if self.review != "":
            review = self.review.resolve(context)

        if self.comment != "":
            comment = self.comment.resolve(context)

        context_type = self.context_type.resolve(context)
        context_id = self.context_id.resolve(context)

        user = context.get('user', None)
        if user.is_anonymous():
            user = None

        s = ""

        if context_type == "comment" or context_type == "screenshot_comment":
            for reply_comment in comment.public_replies(user):
                s += generate_reply_html(reply_comment.review_set.get(),
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


@register.tag
def reply_list(parser, token):
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

    try:
        tag_name, review, comment, context_type, context_id = \
            token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag is missing one or more parameters"

    return ReplyList(review, comment, context_type, context_id)


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
    starred = False
    show_count = True
    count = 0

    if view == 'all':
        review_requests = ReviewRequest.objects.public(user)
    elif view == 'outgoing':
        review_requests = ReviewRequest.objects.from_user(user.username, user)
    elif view == 'incoming':
        review_requests = ReviewRequest.objects.to_user(user.username, user)
    elif view == 'to-me':
        review_requests = ReviewRequest.objects.to_user_directly(user.username,
                                                                 user)
    elif view == 'to-group':
        review_requests = ReviewRequest.objects.to_group(group.name, user)
    elif view == 'starred':
        review_requests = \
            user.get_profile().starred_review_requests.public(user)
        starred = True
    elif view == 'watched-groups':
        starred = True
        show_count = False
    else:
        raise template.TemplateSyntaxError, \
            "Invalid view type '%s' passed to 'dashboard_entry' tag." % view

    if show_count:
        if type(review_requests) == QuerySet:
            count = review_requests.count()
        else:
            count = len(review_requests)

    return {
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
    if review_request.repository.bug_tracker:
        return review_request.repository.bug_tracker % bug_id

    return None


@register.filter
def diffsets_with_comments(review, current_pair):
    """
    Returns a list of diffsets in the review that contain draft comments.
    """
    diffsets = DiffSet.objects.filter(
        files__comment__review=review,
        files__comment__interfilediff__isnull=True).distinct()

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
    diffsets = DiffSet.objects.filter(
        files__comment__review=review,
        files__comment__interfilediff__isnull=False).distinct()

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
    current_diffset, interdiff = diffset_pair

    # See if there are any diffsets with comments on them in this review.
    q = DiffSet.objects.filter(
        files__comment__review=review,
        files__comment__interfilediff__isnull=True).distinct()

    if not interdiff:
        # The user is browsing a standard diffset, so filter it out.
        q = q.exclude(pk=current_diffset.id)

    if q.count() > 0:
        return True

    # See if there are any interdiffs with comments on them in this review.
    q = DiffSet.objects.filter(
        files__comment__review=review,
        files__comment__interfilediff__isnull=False)

    if interdiff:
        # The user is browsing an interdiff, so filter it out.
        q = q.exclude(pk=current_diffset.id,
                      files__comment__interfilediff__diffset=interdiff)

    return q.count() > 0


@register.inclusion_tag('reviews/star.html', takes_context=True)
def star(context, obj):
    """
    Renders the code for displaying a star used for starring items.

    The rendered code should handle click events so that the user can
    toggle the star. The star is rendered by the template
    :template:`reviews/star.html`.

    The passed object must be either a :model:`reviews.ReviewRequest` or
    a :model:`reviews.Group`.
    """
    user = context.get('user', None)

    if user.is_anonymous():
        return None

    try:
        profile = user.get_profile()
    except Profile.DoesNotExist:
        return None

    if isinstance(obj, ReviewRequest):
        obj_info = {
            'type': 'reviewrequests',
            'id': obj.id
        }

        starred = bool(get_object_or_none(profile.starred_review_requests,
                                          pk=obj.id))
    elif isinstance(obj, Group):
        obj_info = {
            'type': 'groups',
            'id': obj.name
        }

        starred = bool(get_object_or_none(profile.starred_groups, pk=obj.id))
    else:
        raise template.TemplateSyntaxError, \
            "star tag received an incompatible object type (%s)" % type(obj)

    return {
        'object': obj_info,
        'starred': int(starred),
        'user': user,
    }
