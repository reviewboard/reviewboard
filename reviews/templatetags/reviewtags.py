from django import template
from django.template import loader, resolve_variable
from django.template import NodeList, TemplateSyntaxError, VariableDoesNotExist
from django.utils import simplejson
from reviewboard.reviews.models import ReviewRequestDraft
from reviewboard.utils.templatetags.htmlutils import humanize_list
import re

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
            "%r tag requires a timestamp"

    return CommentCounts(filediff)


@register.filter
def embedcomments(value, review):
    value = re.sub("{#.*?#}", "", value)

    if value.find("{{comments}}") == -1:
        return value

    s = loader.render_to_string('reviews/comment.html', {'review': review})
    return re.sub("(\n\n)?{{comments}}(\n\n)?", s, value)


@register.simple_tag
def reviewer_list(review_request):
    names  = [group.name    for group in review_request.target_groups.all()]
    names += [user.username for user  in review_request.target_people.all()]
    return humanize_list(names)
