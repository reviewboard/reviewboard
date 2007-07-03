from urllib import quote

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, \
                        HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.views.generic.list_detail import object_list
from djblets.auth.util import login_required
from djblets.util.decorators import simple_decorator
from djblets.util.misc import get_object_or_none

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import view_diff, view_diff_fragment
from reviewboard.diffviewer.forms import EmptyDiffError
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft, \
                                       Review, Group, Screenshot, \
                                       ScreenshotComment
from reviewboard.reviews.forms import NewReviewRequestForm, \
                                      UploadScreenshotForm, \
                                      OwnershipError
from reviewboard.reviews.email import mail_review_request, \
                                      mail_diff_update
from reviewboard.scmtools.models import Repository
from reviewboard.utils.views import sortable_object_list
import reviewboard.reviews.db as reviews_db


@simple_decorator
def valid_prefs_required(view_func):
    def _check_valid_prefs(request, *args, **kwargs):
        try:
            profile = request.user.get_profile()
            if profile.first_time_setup_done:
                return view_func(request, *args, **kwargs)
        except Profile.DoesNotExist:
            pass

        return HttpResponseRedirect("/account/preferences/?%s=%s" %
                                    (REDIRECT_FIELD_NAME,
                                     quote(request.get_full_path())))

    return _check_valid_prefs


@login_required
def new_review_request(request,
                       template_name='reviews/new_review_request.html'):
    if request.method == 'POST':
        form_data = request.POST.copy()
        form_data.update(request.FILES)
        form = NewReviewRequestForm(form_data)

        if form.is_valid():
            try:
                review_request = form.create(request.user,
                                             request.FILES['diff_path'])
                return HttpResponseRedirect(review_request.get_absolute_url())
            except OwnershipError:
                pass
            except EmptyDiffError:
                pass
    else:
        form = NewReviewRequestForm()

    # Repository ID : visible fields mapping.  This is so we can dynamically
    # show/hide the relevant fields with javascript.
    fields = {}
    for repo in Repository.objects.all():
        fields[repo.id] = repo.get_scmtool().get_fields()

    # Turn the selected index back into an int so we can compare it properly.
    if 'repository' in form.data:
        form.data['repository'] = int(form.data['repository'])

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'fields': simplejson.dumps(fields),
    }))

@login_required
def review_detail(request, object_id, template_name):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    draft = get_object_or_none(review_request.reviewrequestdraft_set)
    reviews = review_request.review_set.filter(public=True,
                                               base_reply_to__isnull=True)
    for review in reviews:
        review.ordered_comments = \
            review.comments.order_by('filediff', 'first_line')

    return render_to_response(template_name, RequestContext(request, {
        'draft': draft,
        'review_request': review_request,
        'review_request_details': draft or review_request,
        'reviews': reviews,
        'request': request,
    }))


def review_list(request, queryset, template_name, default_filter=True,
                extra_context={}, **kwargs):
    profile, profile_is_new = \
        Profile.objects.get_or_create(user=request.user)

    if default_filter:
        queryset = queryset.filter(Q(status='P') |
                                   Q(status='S')).order_by('-last_updated')

    sort = request.GET.get('sort', profile.sort_review_request_columns)
    response = sortable_object_list(request,
        queryset=queryset,
        default_sort=profile.sort_review_request_columns,
        template_name=template_name,
        extra_context=extra_context,
        **kwargs)

    if profile.sort_review_request_columns != sort:
        profile.sort_review_request_columns = sort
        profile.save()

    return response


@login_required
def all_review_requests(request, template_name='reviews/review_list.html'):
    return review_list(request,
        queryset=reviews_db.get_all_review_requests(request.user, status=None),
        template_name=template_name)


@login_required
def submitter_list(request, template_name='reviews/submitter_list.html'):
    return object_list(request,
        queryset=User.objects.filter(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


@login_required
def group_list(request, template_name='reviews/group_list.html'):
    return object_list(request,
        queryset=Group.objects.all(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


@login_required
@valid_prefs_required
def dashboard(request, template_name='reviews/dashboard.html'):
    view = request.GET.get('view', 'incoming')
    group = request.GET.get('group', "")

    if view == 'outgoing':
        review_requests = \
            reviews_db.get_review_requests_from_user(request.user.username,
                                                     request.user)
        title = "All Outgoing Review Requests"
    elif view == 'to-me':
        review_requests = reviews_db.get_review_requests_to_user_directly(
            request.user.username, request.user)
        title = "Incoming Review Requests to Me"
    elif view == 'to-group':
        if group != "":
            review_requests = reviews_db.get_review_requests_to_group(
                group, request.user)
            title = "Incoming Review Requests to %s" % group
        else:
            review_requests = reviews_db.get_review_requests_to_user_groups(
                request.user.username, request.user)
            title = "All Incoming Review Requests to My Groups"
    else: # "incoming" or invalid
        review_requests = reviews_db.get_review_requests_to_user(
            request.user.username, request.user)
        title = "All Incoming Review Requests"

    class BogusQuerySet:
        """
        Simple class to fool the object_list generic view into thinking a
        list is a QuerySet.
        """
        def __init__(self, list):
            self.list = list

        def order_by(self, *field_names):
            return BogusQuerySet(sorted(self.list,
                lambda a,b: self._sort_func(a, b, field_names)))

        def _sort_func(self, a, b, field_list):
            for field in field_list:
                if field[0] == "-":
                    reverse = True
                    field = field[1:]
                else:
                    reverse = False

                try:
                    a_value = str(getattr(a, field))
                    b_value = str(getattr(b, field))

                    if reverse:
                        i = cmp(b_value, a_value)
                    else:
                        i = cmp(a_value, b_value)

                    if i != 0:
                        return i
                except AttributeError:
                    # The field doesn't exist, so just ignore it.
                    pass

            # They're equal, so compare the objects themselves to "sort" it out.
            return cmp(a, b)

        def _clone(self):
            return self.list

    if isinstance(review_requests, list):
        queryset = BogusQuerySet(review_requests)
    else:
        queryset = review_requests

    return review_list(request,
        queryset=queryset,
        template_name=template_name,
        default_filter=False,
        template_object_name='review_request',
        extra_context={
            'title': title,
            'view': view,
            'group': group,
        })


@login_required
def group(request, name, template_name='reviews/review_list.html'):
    return review_list(request,
        queryset=reviews_db.get_review_requests_to_group(name, status=None),
        template_name=template_name,
        extra_context={
            'source': name,
        })


@login_required
def submitter(request, username, template_name='reviews/review_list.html'):
    return review_list(request,
        queryset=reviews_db.get_review_requests_from_user(username,
                                                          status=None),
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })


def _query_for_diff(review_request, revision, query_extra=None):
    # Either the diff is part of a draft, or part of the history
    query = None
    draft = get_object_or_none(review_request.reviewrequestdraft_set)

    if draft:
        query = Q(reviewrequestdraft=draft)

    if revision or not query:
        query = Q(history=review_request.diffset_history)

    if revision:
        query = query & Q(revision=revision)

    if query_extra:
        query = query & query_extra

    try:
        return DiffSet.objects.filter(query).latest()
    except DiffSet.DoesNotExist:
        raise Http404


@login_required
def diff(request, review_request_id, revision=None, interdiff_revision=None):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    diffset = _query_for_diff(review_request, revision)

    if interdiff_revision:
        interdiffset = _query_for_diff(review_request, interdiff_revision)
        interdiffset_id = interdiffset.id
    else:
        interdiffset_id = None

    review = get_object_or_none(Review,
                                user=request.user,
                                review_request=review_request,
                                public=False,
                                base_reply_to__isnull=True,
                                reviewed_diffset=diffset)
    draft = get_object_or_none(review_request.reviewrequestdraft_set)

    return view_diff(request, diffset.id, interdiffset_id, {
        'review': review,
        'review_request': review_request,
        'review_request_details': draft or review_request,
    })


@login_required
def raw_diff(request, review_request_id, revision=None):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    diffset = _query_for_diff(review_request, revision)

    data = ""
    for filediff in diffset.files.all():
        data += filediff.diff

    resp = HttpResponse(data, mimetype='text/x-patch')
    resp['Content-Disposition'] = 'inline; filename=%s' % diffset.name
    return resp


@login_required
def diff_fragment(request, object_id, revision, filediff_id,
                  interdiffset_id=None, chunkindex=None,
                  template_name='diffviewer/diff_file_fragment.html'):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    try:
        draft = review_request.reviewrequestdraft_set.get()
        query_extra = Q(reviewrequestdraft=draft)
    except ReviewRequestDraft.DoesNotExist:
        query_extra = None

    diffset = _query_for_diff(review_request, revision, query_extra)

    return view_diff_fragment(request, diffset.id, filediff_id,
                              interdiffset_id, chunkindex, template_name)


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

        # Only e-mail this if not in a draft.
        if settings.SEND_REVIEW_MAIL:
            mail_diff_update(request.user, review_request)

    return HttpResponseRedirect(review_request.get_absolute_url())


@login_required
def publish(request, review_request_id):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    # If a draft exists, save it before publishing.  Without this, further
    # updates to the review request will get saved to the wrong draft and appear
    # not to work.
    try:
        draft = review_request.reviewrequestdraft_set.get()
        draft.save_draft()
        draft.delete()
    except ReviewRequestDraft.DoesNotExist:
        pass

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
        raise HttpResponseForbidden() # XXX Error out


@login_required
def setstatus(request, review_request_id, action):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.user != review_request.submitter and \
       not request.user.has_perm("reviews.can_change_status"):
        raise HttpResponseForbidden()

    try:
        if review_request.status == "D" and action == "reopen":
            review_request.public = False

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
            'domain_method': settings.DOMAIN_METHOD,
        }),
    ), mimetype='text/plain')


@login_required
def preview_review_email(request, review_request_id, review_id,
                         template_name='reviews/review_email.txt'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'user': request.user,
            'domain': Site.objects.get(pk=settings.SITE_ID).domain,
            'domain_method': settings.DOMAIN_METHOD,
        }),
    ), mimetype='text/plain')


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
            'domain_method': settings.DOMAIN_METHOD,
        }),
    ), mimetype='text/plain')

@login_required
def upload_screenshot(request, review_request_id,
                      template_name='reviews/upload_screenshot.html'):
    error = None

    if request.method == 'POST':
        form_data = request.POST.copy()
        form_data.update(request.FILES)
        form = UploadScreenshotForm(form_data)

        if form.is_valid():
            r = get_object_or_404(ReviewRequest, pk=review_request_id)

            try:
                screenshot = form.create(request.FILES['path'], r)
                return HttpResponseRedirect(r.get_absolute_url())
            except Exception, e:
                error = str(e)
    else:
        form = UploadScreenshotForm()

    return render_to_response(template_name, RequestContext(request, {
        'error': error,
        'form': form,
    }))

@login_required
def delete_screenshot(request, review_request_id, screenshot_id):
    request = get_object_or_404(ReviewRequest, pk=review_request_id)

    s = Screenshot.objects.get(id=screenshot_id)

    draft = ReviewRequestDraft.create(request)
    draft.screenshots.remove(s)
    draft.inactive_screenshots.add(s)
    draft.save()

    return HttpResponseRedirect(request.get_absolute_url())

def view_screenshot(request, review_request_id, screenshot_id,
                    template_name='reviews/screenshot_detail.html'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)

    query = Q(history=review_request.diffset_history)

    draft = get_object_or_none(review_request.reviewrequestdraft_set)
    if draft:
        query = query & Q(reviewrequestdraft=draft)

    try:
        diffset = DiffSet.objects.filter(query).latest()
    except DiffSet.DoesNotExist:
        diffset = None

    try:
        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
    except ScreenshotComment.DoesNotExist:
        comments = []

    return render_to_response(template_name, RequestContext(request, {
        'draft': draft,
        'review': review_request,
        'details': draft or review_request,
        'screenshot': screenshot,
        'request': request,
        'diffset': diffset,
        'comments': comments,
    }))
