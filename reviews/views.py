from datetime import datetime
import re

from django import newforms as forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.serializers import serialize
from django.db.models import Q, ManyToManyField
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.views.generic.list_detail import object_list
from django.views.decorators.http import require_GET, require_POST
from djblets.auth.util import login_required

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.diffviewer.views import view_diff, view_diff_fragment
from reviewboard.diffviewer.views import UserVisibleError, get_diff_files
from reviewboard.reviews.db import \
    get_all_review_requests, get_review_requests_to_group, \
    get_review_requests_to_user_directly, get_review_requests_to_user, \
    get_review_requests_from_user
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft, Quip
from reviewboard.reviews.models import Review, Comment, Group
from reviewboard.reviews.forms import NewReviewRequestForm
from reviewboard.reviews.email import mail_review_request, mail_review
from reviewboard import scmtools


@login_required
def new_review_request(request, template_name='reviews/review_detail.html'):
    if request.POST:
        form = NewReviewRequestForm(request.POST.copy())

        if form.is_valid():
            form.clean_data['submitter'] = request.user
            form.clean_data['status'] = 'P'
            form.clean_data['public'] = True
            new_reviewreq = form.create()

            return HttpResponseRedirect(new_reviewreq.get_absolute_url())
    else:
        form = NewReviewRequestForm(initial={'submitter': request.user})

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
    }))


@login_required
def new_from_changenum(request):
    if not request.POST or 'changenum' not in request.POST:
        # XXX Display an error page
        return HttpResponseRedirect('/r/new/')

    changenum = request.POST['changenum']

    diffset_history = DiffSetHistory()
    diffset_history.save()

    review_request = ReviewRequest()
    changeset = scmtools.get_tool().get_changeset(changenum)

    if changeset:
        review_request.summary = changeset.summary
        review_request.description = changeset.description
        review_request.testing_done = changeset.testing_done
        review_request.branch = changeset.branch
        review_request.bugs_closed = ','.join(changeset.bugs_closed)
        review_request.diffset_history = diffset_history
        review_request.submitter = request.user
        review_request.status = 'P'
        review_request.public = False
        review_request.save()

        return HttpResponseRedirect(review_request.get_absolute_url())

    diffset_history.delete()
    # XXX Display an error page
    return HttpResponseRedirect('/r/new/')


@login_required
def review_detail(request, object_id, template_name):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    try:
        draft = review_request.reviewrequestdraft_set.get()
    except ReviewRequestDraft.DoesNotExist:
        draft = None

    return render_to_response(template_name, RequestContext(request, {
        'draft': draft,
        'object': review_request,
        'details': draft or review_request,
        'reviews': review_request.review_set.filter(public=True,
                                                    base_reply_to__isnull=True),
        'request': request,
    }))


@login_required
def review_list(request, queryset, template_name, extra_context={}):
    return object_list(request,
        queryset=queryset.order_by('-last_updated'),
        paginate_by=50,
        allow_empty=True,
        template_name=template_name,
        extra_context=dict(
            {'app_path': request.path},
            **extra_context
        ))


@login_required
def submitter_list(request, template_name):
    return object_list(request,
        queryset=User.objects.filter(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


@login_required
def group_list(request, template_name):
    return object_list(request,
        queryset=Group.objects.all(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


@login_required
def dashboard(request, limit=50, template_name='reviews/dashboard.html'):
    view = request.GET.get('view', 'incoming')

    if view == 'outgoing':
        review_requests = \
            get_review_requests_from_user(request.user.username, request.user)
    elif view == 'to-me':
        review_requests = \
            get_review_requests_to_user_directly(request.user.username,
                                                 request.user)
    elif view == 'to-group':
        group = request.GET.get('group', None)

        if group != None:
            review_requests = get_review_requests_to_group(group, request.user)
        else:
            review_requests = \
                get_review_requests_to_user_groups(request.user.username,
                                                   request.user)
    else: # "incoming" or invalid
        review_requests = get_review_requests_to_user(request.user.username,
                                                      request.user)

    review_requests = review_requests[:limit]

    return render_to_response(template_name, RequestContext(request, {
        'review_requests': review_requests,
    }))


@login_required
def group(request, name, template_name):
    return review_list(request,
        queryset=get_review_requests_to_group(name),
        template_name=template_name,
        extra_context={
            'source': name,
        })


@login_required
def submitter(request, username, template_name):
    return review_list(request,
        queryset=get_review_requests_to_user_directly(username),
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })


@login_required
def diff(request, object_id, revision=None):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    query = Q(history=review_request.diffset_history)

    try:
        draft = review_request.reviewrequestdraft_set.get()
        query = query & Q(reviewrequestdraft=draft)
    except ReviewRequestDraft.DoesNotExist:
        pass

    if revision != None:
        query = query & Q(revision=revision)

    try:
        diffset = DiffSet.objects.filter(query).latest()
    except:
        raise Http404

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    reviewed_diffset=diffset)
    except Review.DoesNotExist:
        review = None

    return view_diff(request, diffset.id, {'review': review})


@login_required
def diff_fragment(request, object_id, revision, filediff_id,
                  template_name='diffviewer/diff_file_fragment.html'):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    query = Q(history=review_request.diffset_history) & Q(revision=revision)

    try:
        draft = review_request.reviewrequestdraft_set.get()
        query = query & Q(reviewrequestdraft=draft)
    except ReviewRequestDraft.DoesNotExist:
        pass

    try:
        diffset = DiffSet.objects.filter(query).latest()
    except:
        raise Http404

    return view_diff_fragment(request, diffset.id, filediff_id, template_name)


@login_required
def upload_diff_done(request, review_request_id, diffset_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    diffset = get_object_or_404(DiffSet, pk=diffset_id)

    try:
        draft = review_request.reviewrequestdraft_set.get()

        if draft.diffset and draft.diffset != diffset:
            draft.diffset.delete()

        draft.diffset = diffset
        draft.save()
    except ReviewRequestDraft.DoesNotExist:
        diffset.history = review_request.diffset_history
        diffset.save()

    return HttpResponseRedirect(review_request.get_absolute_url())


@login_required
def publish(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if review_request.submitter == request.user:
        review_request.public = True

        if not review_request.target_groups and \
           not review_request.target_people:
            pass # FIXME show an error

        review_request.save()

        if settings.SEND_REVIEW_MAIL:
            mail_review_request(request.user, review_request)

        return HttpResponseRedirect(review_request.get_absolute_url())
    else:
        raise Http403() # XXX Error out


@login_required
def setstatus(request, review_request_id, action):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.user != review_request.submitter:
        raise Http403()

    try:
        review_request.status = {
            'discard':   'D',
            'submitted': 'S',
            'reopen':    'P',
        }[action]
    except KeyError:
        # This should never happen under normal circumstances
        raise Exception('Error when setting review status: unknown status code')

    review_request.save()
    if action == 'discard':
        return HttpResponseRedirect('/dashboard/')
    else:
        return HttpResponseRedirect(review_request.get_absolute_url())


@login_required
def comments(request, review_request_id, filediff_id, line, revision=None,
             template_name='reviews/line_comments.html'):
    line = int(line)

    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    filediff = get_object_or_404(FileDiff, pk=filediff_id)

    if request.POST:
        text = request.POST['text']
        num_lines = request.POST['num_lines']

        # TODO: Sanity check the fields
        if filediff.diffset.history != review_request.diffset_history:
            raise Http403();

        if request.POST['action'] == "set":
            review, review_is_new = Review.objects.get_or_create(
                review_request=review_request,
                user=request.user,
                public=False,
                reviewed_diffset=filediff.diffset)

            if review_is_new:
                review.save()

            comment, comment_is_new = review.comments.get_or_create(
                filediff=filediff,
                first_line=line)

            comment.text = request.POST['text']
            comment.num_lines = num_lines
            comment.timestamp = datetime.now()
            comment.save()

            if comment_is_new:
                review.comments.add(comment)
                review.save()
        elif request.POST['action'] == "delete":
            review = get_object_or_404(Review,
                review_request=review_request,
                user=request.user,
                public=False,
                reviewed_diffset=filediff.diffset)

            try:
                comment = review.comments.get(filediff=filediff,
                                              first_line=line)
                comment.delete()
            except Comment.DoesNotExist:
                pass

            if review.body_top.strip() == "" and \
               review.body_bottom.strip() == "" and \
               review.comments.count() == 0:
                review.delete()
        else:
            raise Http403()

    comments = []
    for comment in filediff.comment_set.all():
        if comment.review_set.count() > 0 and comment.first_line == line:
            review = comment.review_set.get()
            if review.public or review.user == request.user:
                comments.append({
                    'user': review.user,
                    'draft': not review.public and review.user == request.user,
                    'timestamp': comment.timestamp,
                    'first_line': comment.first_line,
                    'num_lines': comment.num_lines,
                    'last_line': comment.last_line(),
                    'text': comment.text,
                })

    return render_to_response(template_name, RequestContext(request, {
        'comments': comments,
    }))


@login_required
def preview_review_request_email(
        request, review_request_id,
        template_name='reviews/review_request_email.html'):

    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'user': request.user,
            'domain': Site.objects.get(pk=settings.SITE_ID).domain,
        }),
    ), mimetype='text/plain')
    return response


@login_required
def preview_reply_email(request, review_request_id, review_id,
                        template_name='reviews/review_email.html'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id)

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'user': request.user,
            'domain': Site.objects.get(pk=settings.SITE_ID).domain,
        }),
    ), mimetype='text/plain')
    return response
