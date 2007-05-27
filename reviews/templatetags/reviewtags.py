import re

from django import template
from django.conf import settings
from django.db.models import Q
from django.template import loader, resolve_variable
from django.template import NodeList, TemplateSyntaxError, VariableDoesNotExist
from django.template.loader import render_to_string
from django.utils import simplejson

from reviewboard.reviews.db import get_all_review_requests, \
                                   get_review_requests_from_user, \
                                   get_review_requests_to_user, \
                                   get_review_requests_to_user_directly, \
                                   get_review_requests_to_group
from reviewboard.reviews.models import ReviewRequestDraft, ScreenshotComment
from reviewboard.utils.templatetags.htmlutils import humanize_list

register = template.Library()

class ReviewSummary(template.Node):
    def __init__(self, review_request):
        self.review_request = review_request

    def render(self, context):
        try:
            review_request = resolve_variable(self.review_request, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to reviewsummary tag." % \
                self.review_request

        if review_request.submitter == context.get('user', None):
            try:
                draft = review_request.reviewrequestdraft_set.get()
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       draft.summary
            except ReviewRequestDraft.DoesNotExist:
                pass

            if not review_request.public:
                # XXX Do we want to say "Draft?"
                return "<span class=\"draftlabel\">[Draft]</span> " + \
                       review_request.summary

        if review_request.status == 'S':
            return "<span class=\"draftlabel\">[Submitted]</span> " + \
                   review_request.summary

        return review_request.summary


@register.tag
def reviewsummary(parser, token):
    try:
        tag_name, review_request = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a timestamp"

    return ReviewSummary(review_request)


class PendingReviewCount(template.Node):
    def __init__(self, obj):
        self.obj = obj

    def render(self, context):
        try:
            obj = resolve_variable(self.obj, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to pendingreviewcount tag." % \
                self.obj

        return str(obj.reviewrequest_set.filter(public=True,
                                                status='P').count())


@register.tag
def pendingreviewcount(parser, token):
    try:
        tag_name, obj = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a user or group object"

    return PendingReviewCount(obj)


class ReviewRequestCount(template.Node):
    def __init__(self, listtype, param):
        self.listtype = listtype
        self.param = param

    def render(self, context):
        if self.param != None:
            try:
                param = resolve_variable(self.param, context)
            except VariableDoesNotExist:
                raise template.TemplateSyntaxError, \
                    "Invalid variable %s passed to 'reviewrequestcount' tag." \
                    % self.param

        user = context.get('user', None)

        if self.listtype == 'all':
            review_requests = get_all_review_requests(user)
        elif self.listtype == 'outgoing':
            review_requests = get_review_requests_from_user(user.username, user)
        elif self.listtype == 'incoming':
            review_requests = get_review_requests_to_user(user.username, user)
        elif self.listtype == 'incoming-directly':
            review_requests = \
                get_review_requests_to_user_directly(user.username, user)
        elif self.listtype == 'to-group':
            review_requests = get_review_requests_to_group(param, user)
        else:
            raise template.TemplateSyntaxError, \
                "Invalid list type '%s' passed to 'reviewrequestcount' tag." \
                % self.listtype

        return str(review_requests.count())


@register.tag
def reviewrequestcount(parser, token):
    bits = token.contents.split()
    del(bits[0])

    if len(bits) == 0 or len(bits) > 2:
        raise TemplateSyntaxError, "incorrect number of arguments passed " + \
                                   "'reviewrequestcount'"

    listtype = bits[0]

    if len(bits) == 2:
        param = bits[1]
    else:
        param = None

    return ReviewRequestCount(listtype, param)


class ForComment(template.Node):
    def __init__(self, filediff, review, nodelist_loop):
        self.filediff = filediff
        self.review = review
        self.nodelist_loop = nodelist_loop

    def render(self, context):
        try:
            filediff = resolve_variable(self.filediff, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to 'forcomment' tag." % \
                self.filediff

        if self.review == None:
            review = None
        else:
            try:
                review = resolve_variable(self.review, context)
            except VariableDoesNotExist:
                raise template.TemplateSyntaxError, \
                    "Invalid variable %s passed to 'forcomment' tag." % \
                    self.review

        nodelist = NodeList()
        context.push()

        if review == None:
            comments = filediff.comment_set.all()
        else:
            comments = filediff.comment_set.filter(review=review)

        for comment in comments:
            context['comment'] = comment

            for node in self.nodelist_loop:
                nodelist.append(node.render(context))

        context.pop()
        return nodelist.render(context)


@register.tag
def forcomment(parser, token):
    bits = token.contents.split()
    del(bits[0])

    if len(bits) == 0 or len(bits) > 2:
        raise TemplateSyntaxError, "too many arguments passed to 'forcomment'"

    filediff = bits[0]

    if len(bits) == 2:
        review = bits[1]
    else:
        review = None

    nodelist_loop = parser.parse(('endforcomment',))
    parser.delete_first_token()

    return ForComment(filediff, review, nodelist_loop)


class CommentCounts(template.Node):
    def __init__(self, filediff):
        self.filediff = filediff

    def render(self, context):
        try:
            filediff = resolve_variable(self.filediff, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable %s passed to commentcounts tag." % \
                self.filediff

        comments = {}
        user = context.get('user', None)

        for comment in filediff.comment_set.all():
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
    try:
        tag_name, filediff = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a filediff"

    return CommentCounts(filediff)


class ScreenshotCommentCounts(template.Node):
    def __init__(self, screenshot):
        self.screenshot = screenshot

    def render(self, context):
        try:
            screenshot = resolve_variable(self.screenshot, context)
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
    try:
        tag_name, screenshot = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a screenshot"

    return ScreenshotCommentCounts(screenshot)


class ReplyList(template.Node):
    def __init__(self, review, comment, context_type, context_id):
        self.review = review
        self.comment = comment
        self.context_type = context_type
        self.context_id = context_id

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

        if self.review != "":
            review = resolve_variable(self.review, context)

        if self.comment != "":
            comment = resolve_variable(self.comment, context)

        context_type = resolve_variable(self.context_type, context)
        context_id = resolve_variable(self.context_id, context)

        user = context.get('user', None)

        s = ""

        if context_type == "comment":
            for reply_comment in comment.public_replies(user):
                s += generate_reply_html(reply_comment.review_set.get(),
                                         reply_comment.timestamp,
                                         reply_comment.text)
        elif context_type == "screenshot_comment":
            for reply_comment in comment.public_replies(user):
                s += generate_reply_html(reply_comment.review_set.get(),
                                         reply_comment.timestamp,
                                         reply_comment.text)
        elif context_type == "body_top":
            for reply in review.body_top_replies.filter(Q(public=True) |
                                                        Q(user=user)):
                s += generate_reply_html(reply, reply.timestamp,
                                         reply.body_top)
        elif context_type == "body_bottom":
            for reply in review.body_bottom_replies.filter(Q(public=True) |
                                                           Q(user=user)):
                s += generate_reply_html(reply, reply.timestamp,
                                         reply.body_bottom)
        else:
            raise TemplateSyntaxError, "Invalid context type passed"

        return s


@register.tag
def reply_list(parser, token):
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


@register.simple_tag
def reviewer_list(review_request):
    return humanize_list([group.display_name or group.name \
                          for group in review_request.target_groups.all()] + \
                         [user.get_full_name() or user.username \
                          for user  in review_request.target_people.all()])


@register.filter
def bug_url(bug_id, review_request):
    if review_request.repository.bug_tracker:
        return review_request.repository.bug_tracker % bug_id

    return None
