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
import reviewboard.reviews.db as reviews_db
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft, Quip
from reviewboard.reviews.models import Review, Comment, Group
from reviewboard.reviews.forms import NewReviewRequestForm
from reviewboard.reviews.email import mail_review_request, mail_review
from reviewboard import scmtools


@login_required
@require_POST
def new_from_changenum(request):
    try:
        review_request = reviews_db.create_review_request(
            request.user, request.POST.get('changenum', None))
        return HttpResponseRedirect(review_request.get_absolute_url())
    except reviews_db.InvalidChangeNumberException:
        # TODO Display an error page
        return HttpResponseRedirect('/r/')


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


def review_list(request, queryset, template_name, extra_context={}):
    return object_list(request,
        queryset=queryset.filter(Q(status='P') |
                                 Q(status='S')).order_by('-last_updated'),
        paginate_by=50,
        allow_empty=True,
        template_name=template_name,
        extra_context=dict(
            {'app_path': request.path},
            **extra_context
        ))


@login_required
def all_review_requests(request, template_name):
    return review_list(request,
        queryset=reviews_db.get_all_review_requests(request.user, status=None),
        template_name=template_name)


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
            reviews_db.get_review_requests_from_user(request.user.username,
                                                     request.user)
    elif view == 'to-me':
        review_requests = reviews_db.get_review_requests_to_user_directly(
            request.user.username, request.user)
    elif view == 'to-group':
        group = request.GET.get('group', None)

        if group != None:
            review_requests = reviews_db.get_review_requests_to_group(
                group, request.user)
        else:
            review_requests = reviews_db.get_review_requests_to_user_groups(
                request.user.username, request.user)
    else: # "incoming" or invalid
        review_requests = reviews_db.get_review_requests_to_user(
            request.user.username, request.user)

    review_requests = review_requests[:limit]

    return render_to_response(template_name, RequestContext(request, {
        'review_requests': review_requests,
    }))


@login_required
def group(request, name, template_name):
    return review_list(request,
        queryset=reviews_db.get_review_requests_to_group(name, status=None),
        template_name=template_name,
        extra_context={
            'source': name,
        })


@login_required
def submitter(request, username, template_name):
    return review_list(request,
        queryset=reviews_db.get_review_requests_to_user_directly(username,
                                                                 status=None),
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
def preview_review_request_email(
        request, review_request_id,
        template_name='reviews/review_request_email.txt'):

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
def preview_review_email(request, review_request_id, review_id,
                         template_name='reviews/review_email.txt'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'user': request.user,
            'domain': Site.objects.get(pk=settings.SITE_ID).domain,
        }),
    ), mimetype='text/plain')
    return response


@login_required
def preview_reply_email(request, review_request_id, review_id, reply_id,
                        template_name='reviews/reply_email.txt'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)
    reply = get_object_or_404(Review, pk=reply_id, base_reply_to=review)

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'reply': reply,
            'user': request.user,
            'domain': Site.objects.get(pk=settings.SITE_ID).domain,
        }),
    ), mimetype='text/plain')
    return response
