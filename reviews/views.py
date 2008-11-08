from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, \
                        HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.generic.list_detail import object_list

from djblets.auth.util import login_required
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.misc import get_object_or_none

from reviewboard.accounts.decorators import check_login_required, \
                                            valid_prefs_required
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet
from reviewboard.diffviewer.views import view_diff, view_diff_fragment
from reviewboard.reviews.datagrids import DashboardDataGrid, \
                                          GroupDataGrid, \
                                          ReviewRequestDataGrid, \
                                          SubmitterDataGrid, \
                                          WatchedGroupDataGrid
from reviewboard.reviews.errors import PermissionError
from reviewboard.reviews.forms import NewReviewRequestForm, \
                                      UploadScreenshotForm
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft, \
                                       Review, Group, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.models import Repository


@login_required
def new_review_request(request,
                       template_name='reviews/new_review_request.html'):
    """
    Displays a New Review Request form and handles the creation of a
    review request based on either an existing changeset or the provided
    information.
    """
    if request.method == 'POST':
        form = NewReviewRequestForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                review_request = form.create(
                    user=request.user,
                    diff_file=request.FILES['diff_path'],
                    parent_diff_file=request.FILES.get('parent_diff_path'))
                return HttpResponseRedirect(review_request.get_absolute_url())
            except:
                # XXX - OwnershipError or ChangeSetError?
                #
                # We're preventing an exception from being thrown here so that
                # we can display the errors that form.create() sets in
                # a much nicer way in the template. Otherwise, the user would
                # see a useless backtrace.
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


fields_changed_name_map = {
    'summary': 'Summary',
    'description': 'Description',
    'testing_done': 'Testing Done',
    'bugs_closed': 'Bugs Closed',
    'branch': 'Branch',
    'target_groups': 'Reviewers (Groups)',
    'target_people': 'Reviewers (People)',
    'screenshots': 'Screenshots',
    'screenshot_captions': 'Screenshot Captions',
    'diff': 'Diff',
}

@check_login_required
@cache_control(no_cache=True, no_store=True, max_age=0, must_revalidate=True)
def review_detail(request, review_request_id,
                  template_name="reviews/review_detail.html"):
    """
    Main view for review requests. This covers the review request information
    and all the reviews on it.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    reviews = review_request.get_public_reviews()
    draft = review_request.get_draft(request.user)
    review = review_request.get_pending_review(request.user)

    if request.user.is_authenticated():
        # If the review request is public and pending review and if the user
        # is logged in, mark that they've visited this review request.
        if review_request.public and review_request.status == "P":
            visited, visited_is_new = ReviewRequestVisit.objects.get_or_create(
                user=request.user, review_request=review_request)
            visited.timestamp = datetime.now()
            visited.save()

    repository = review_request.repository
    changedescs = review_request.changedescs.filter(public=True)

    entries = []

    for temp_review in reviews:
        temp_review.ordered_comments = \
            temp_review.comments.order_by('filediff', 'first_line')

        entries.append({
            'review': temp_review,
            'timestamp': temp_review.timestamp,
        })

    for changedesc in changedescs:
        fields_changed = []

        for name, info in changedesc.fields_changed.items():
            if 'added' in info or 'removed' in info:
                change_type = 'add_remove'

                # We don't hard-code URLs in the bug info, since the
                # tracker may move, but we can do it here.
                if (name == "bugs_closed" and
                    review_request.repository.bug_tracker):
                    bug_url = review_request.repository.bug_tracker
                    for field in info:
                        for i, buginfo in enumerate(info[field]):
                            info[field][i] = (buginfo[0],
                                              bug_url % buginfo[0])

            elif 'old' in info or 'new' in info:
                change_type = 'changed'
            elif name == "screenshot_captions":
                change_type = 'screenshot_captions'
            else:
                # No clue what this is. Bail.
                continue

            fields_changed.append({
                'title': fields_changed_name_map.get(name, name),
                'info': info,
                'type': change_type,
            })

        entries.append({
            'changeinfo': fields_changed,
            'changedesc': changedesc,
            'timestamp': changedesc.timestamp,
        })

    entries.sort(key=lambda item: item['timestamp'])

    return render_to_response(template_name, RequestContext(request, {
        'draft': draft,
        'review_request': review_request,
        'review_request_details': draft or review_request,
        'entries': entries,
        'request': request,
        'upload_diff_form': UploadDiffForm(repository),
        'upload_screenshot_form': UploadScreenshotForm(),
        'scmtool': repository.get_scmtool(),
        'PRE_CREATION': PRE_CREATION,
    }))


@check_login_required
def all_review_requests(request, template_name='datagrid/datagrid.html'):
    """
    Displays a list of all review requests.
    """
    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.public(request.user, status=None),
        _("All review requests"))
    return datagrid.render_to_response(template_name)


@check_login_required
def submitter_list(request, template_name='datagrid/datagrid.html'):
    """
    Displays a list of all users.
    """
    return SubmitterDataGrid(request).render_to_response(template_name)


@check_login_required
def group_list(request, template_name='datagrid/datagrid.html'):
    """
    Displays a list of all review groups.
    """
    return GroupDataGrid(request).render_to_response(template_name)


@login_required
@valid_prefs_required
def dashboard(request, template_name='reviews/dashboard.html'):
    """
    The dashboard view, showing review requests organized by a variety of
    lists, depending on the 'view' parameter.

    Valid 'view' parameters are:

        * 'outgoing'
        * 'to-me'
        * 'to-group'
        * 'starred'
        * 'watched-groups'
        * 'incoming'
    """
    view = request.GET.get('view', None)

    if view == "watched-groups":
        # This is special. We want to return a list of groups, not
        # review requests.
        grid = WatchedGroupDataGrid(request)
    else:
        grid = DashboardDataGrid(request)

    return grid.render_to_response(template_name)


@check_login_required
def group(request, name, template_name='datagrid/datagrid.html'):
    """
    A list of review requests belonging to a particular group.
    """
    # Make sure the group exists
    get_object_or_404(Group, name=name)

    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.to_group(name, status=None),
        _("Review requests for %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
def group_members(request, name, template_name='datagrid/datagrid.html'):
    """
    A list of users registered for a particular group.
    """
    # Make sure the group exists
    get_object_or_404(Group, name=name)

    datagrid = SubmitterDataGrid(request,
        Group.objects.get(name=name).users.filter(is_active=True),
        _("Members of group %s") % name)

    return datagrid.render_to_response(template_name)


@check_login_required
def submitter(request, username, template_name='datagrid/datagrid.html'):
    """
    A list of review requests owned by a particular user.
    """
    # Make sure the user exists
    get_object_or_404(User, username=username)

    datagrid = ReviewRequestDataGrid(request,
        ReviewRequest.objects.from_user(username, status=None),
        _("%s's review requests") % username)

    return datagrid.render_to_response(template_name)


def _query_for_diff(review_request, user, revision, query_extra=None):
    """
    Queries for a diff based on several parameters.

    If the draft does not exist, this throws an Http404 exception.
    """

    # Normalize the revision, since it might come in as a string.
    if revision:
        revision = int(revision)

    # This will try to grab the diff associated with a draft if the review
    # request has an associated draft and is either the revision being
    # requested or no revision is being requested.
    draft = review_request.get_draft(user)
    if draft and draft.diffset and \
       (revision is None or draft.diffset.revision == revision):
        return draft.diffset

    query = Q(history=review_request.diffset_history)

    # Grab a revision if requested.
    if revision is not None:
        query = query & Q(revision=revision)

    # Anything else the caller wants.
    if query_extra:
        query = query & query_extra

    try:
        return DiffSet.objects.filter(query).latest()
    except DiffSet.DoesNotExist:
        raise Http404


@check_login_required
def diff(request, review_request_id, revision=None, interdiff_revision=None,
         template_name='diffviewer/view_diff.html'):
    """
    A wrapper around diffviewer.views.view_diff that handles querying for
    diffs owned by a review request,taking into account interdiffs and
    providing the user's current review of the diff if it exists.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    diffset = _query_for_diff(review_request, request.user, revision)

    interdiffset = None
    interdiffset_id = None
    review = None
    draft = None

    if interdiff_revision and interdiff_revision != revision:
        # An interdiff revision was specified. Try to find a matching
        # diffset.
        interdiffset = _query_for_diff(review_request, request.user,
                                       interdiff_revision)
        interdiffset_id = interdiffset.id

    # Try to find an existing pending review of this diff from the
    # current user.
    review = review_request.get_pending_review(request.user)
    draft = review_request.get_draft(request.user)

    repository = review_request.repository

    has_draft_diff = draft and draft.diffset
    is_draft_diff = has_draft_diff and draft.diffset == diffset
    is_draft_interdiff = has_draft_diff and interdiffset and \
                         draft.diffset == interdiffset

    num_diffs = review_request.diffset_history.diffsets.count()
    if draft and draft.diffset:
        num_diffs += 1

    return view_diff(request, diffset.id, interdiffset_id, {
        'review': review,
        'review_request': review_request,
        'review_request_details': draft or review_request,
        'draft': draft,
        'is_draft_diff': is_draft_diff,
        'is_draft_interdiff': is_draft_interdiff,
        'num_diffs': num_diffs,
        'upload_diff_form': UploadDiffForm(repository),
        'upload_screenshot_form': UploadScreenshotForm(),
        'scmtool': repository.get_scmtool(),
    }, template_name)


@check_login_required
def raw_diff(request, review_request_id, revision=None):
    """
    Displays a raw diff of all the filediffs in a diffset for the
    given review request.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    diffset = _query_for_diff(review_request, request.user, revision)

    data = ''.join([filediff.diff for filediff in diffset.files.all()])

    resp = HttpResponse(data, mimetype='text/x-patch')
    resp['Content-Disposition'] = 'inline; filename=%s' % diffset.name
    return resp


@check_login_required
def diff_fragment(request, review_request_id, revision, filediff_id,
                  interdiff_revision=None,
                  chunkindex=None, collapseall=False,
                  template_name='diffviewer/diff_file_fragment.html'):
    """
    Wrapper around diffviewer.views.view_diff_fragment that takes a review
    request.

    Displays just a fragment of a diff or interdiff owned by the given
    review request. The fragment is identified by the chunk index in the
    diff.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    draft = review_request.get_draft(request.user)

    if draft:
        query_extra = Q(reviewrequestdraft=draft)
    else:
        query_extra = None

    if interdiff_revision is not None:
        interdiffset = _query_for_diff(review_request, request.user,
                                       interdiff_revision, query_extra)
        interdiffset_id = interdiffset.id
        # Only the interdiff should have an extra query for the draft.
        # It's going to be the most recent diff (generally). We should be
        # smarter and check.
        query_extra = None
    else:
        interdiffset_id = None

    diffset = _query_for_diff(review_request, request.user, revision,
                              query_extra)

    return view_diff_fragment(request, diffset.id, filediff_id,
                              interdiffset_id, chunkindex, collapseall,
                              template_name)


@login_required
def publish(request, review_request_id):
    """
    Publishes a new review request or the changes on a draft for a review
    request.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        if not review_request.target_groups and \
           not review_request.target_people:
            pass # FIXME show an error

        if not review_request.can_publish():
            return HttpResponseForbidden()

        review_request.publish(request.user)

        return HttpResponseRedirect(review_request.get_absolute_url())
    except PermissionError:
        return HttpResponseForbidden() # XXX Error out


@login_required
def setstatus(request, review_request_id, action):
    """
    Sets the status of the review request based on the specified action.

    Valid actions are:

        * 'discard'
        * 'submitted'
        * 'reopen'

    If a review request was discarded and action is 'reopen', this will
    reset the review request's public state to False.

    If the user is not the owner of this review request and does not have
    the 'reviews.can_change_status' permission, they will get an
    HTTP Forbidden error.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if not review_request.is_mutable_by(request.user) and \
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
        return HttpResponseRedirect(reverse("dashboard"))
    else:
        return HttpResponseRedirect(review_request.get_absolute_url())


@check_login_required
def preview_review_request_email(
        request, review_request_id,
        template_name='reviews/review_request_email.txt'):
    """
    Previews the e-mail message that would be sent for an initial
    review request or an update.

    This is mainly used for debugging.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    siteconfig = SiteConfiguration.objects.get_current()

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'user': request.user,
            'domain': Site.objects.get_current().domain,
            'domain_method': siteconfig.get("site_domain_method"),
        }),
    ), mimetype='text/plain')


@check_login_required
def preview_review_email(request, review_request_id, review_id,
                         template_name='reviews/review_email.txt'):
    """
    Previews the e-mail message that would be sent for a review of a
    review request.

    This is mainly used for debugging.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)
    siteconfig = SiteConfiguration.objects.get_current()

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'user': request.user,
            'domain': Site.objects.get_current().domain,
            'domain_method': siteconfig.get("site_domain_method"),
        }),
    ), mimetype='text/plain')


@check_login_required
def preview_reply_email(request, review_request_id, review_id, reply_id,
                        template_name='reviews/reply_email.txt'):
    """
    Previews the e-mail message that would be sent for a reply to a
    review of a review request.

    This is mainly used for debugging.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    review = get_object_or_404(Review, pk=review_id,
                               review_request=review_request)
    reply = get_object_or_404(Review, pk=reply_id, base_reply_to=review)
    siteconfig = SiteConfiguration.objects.get_current()

    return HttpResponse(render_to_string(template_name,
        RequestContext(request, {
            'review_request': review_request,
            'review': review,
            'reply': reply,
            'user': request.user,
            'domain': Site.objects.get_current().domain,
            'domain_method': siteconfig.get("site_domain_method"),
        }),
    ), mimetype='text/plain')


@login_required
def delete_screenshot(request, review_request_id, screenshot_id):
    """
    Deletes a screenshot from a review request and redirects back to the
    review request page.
    """
    request = get_object_or_404(ReviewRequest, pk=review_request_id)

    s = Screenshot.objects.get(id=screenshot_id)

    draft = ReviewRequestDraft.create(request)
    draft.screenshots.remove(s)
    draft.inactive_screenshots.add(s)
    draft.save()

    return HttpResponseRedirect(request.get_absolute_url())


@check_login_required
def view_screenshot(request, review_request_id, screenshot_id,
                    template_name='reviews/screenshot_detail.html'):
    """
    Displays a screenshot, along with any comments that were made on it.
    """
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)
    screenshot = get_object_or_404(Screenshot, pk=screenshot_id)
    review = review_request.get_pending_review(request.user)
    draft = review_request.get_draft(request.user)

    query = Q(history=review_request.diffset_history)

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
        'review_request': review_request,
        'details': draft or review_request,
        'screenshot': screenshot,
        'request': request,
        'diffset': diffset,
        'comments': comments,
    }))


def search(request, template_name='reviews/search.html'):
    """
    Searches review requests on Review Board based on a query string.
    """
    query = request.GET.get('q', '')
    siteconfig = SiteConfiguration.objects.get_current()

    if not siteconfig.get("search_enable"):
        # FIXME: show something useful
        raise Http404

    if not query:
        # FIXME: I'm not super thrilled with this
        return HttpResponseRedirect(reverse("root"))

    import lucene

    # We may have already initialized lucene
    try:
        lucene.initVM(lucene.CLASSPATH)
    except ValueError:
        pass

    index_file = siteconfig.get("search_index_file")
    store = lucene.FSDirectory.getDirectory(index_file, False)
    try:
        searcher = lucene.IndexSearcher(store)
    except lucene.JavaError, e:
        # FIXME: show a useful error
        raise e

    parser = lucene.QueryParser('text', lucene.StandardAnalyzer())
    result_ids = [int(lucene.Hit.cast_(hit).getDocument().get('id')) \
                  for hit in searcher.search(parser.parse(query))]

    searcher.close()

    results = ReviewRequest.objects.filter(id__in=result_ids)

    return object_list(request=request,
                       queryset=results,
                       paginate_by=10,
                       template_name=template_name,
                       extra_context={'query': query,
                                      'extra_query': 'q=%s' % query,
                                     })
