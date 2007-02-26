from datetime import datetime
import re

from django import newforms as forms
from django.contrib.auth.models import User, Group
from django.core.serializers import serialize
from django.db.models import Q, ManyToManyField
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.utils import simplejson
from django.views.generic.list_detail import object_list
from djblets.auth.util import login_required

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.diffviewer.views import view_diff, view_diff_fragment
from reviewboard.diffviewer.views import UserVisibleError, get_diff_files
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft, Quip
from reviewboard.reviews.models import Review, Comment
from reviewboard.reviews.forms import NewReviewRequestForm
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
        return HttpResponseRedirect('/reviews/new/')

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
    return HttpResponseRedirect('/reviews/new/')



@login_required
def revert_draft(request, object_id):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)
    try:
        draft = review_request.reviewrequestdraft_set.get()
        draft.delete()
    except ReviewRequestDraft.DoesNotExist:
        pass

    return HttpResponse("Draft reverted.")


@login_required
def save_draft(request, object_id):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)
    draft = get_object_or_404(ReviewRequestDraft, review_request=review_request)

    review_request.summary = draft.summary
    review_request.description = draft.description
    review_request.testing_done = draft.testing_done
    review_request.bugs_closed = draft.bugs_closed
    review_request.branch = draft.branch

    review_request.target_groups.clear()
    map(review_request.target_groups.add, draft.target_groups.all())

    review_request.target_people.clear()
    map(review_request.target_people.add, draft.target_people.all())

    if draft.diffset:
        draft.diffset.history = review_request.diffset_history
        draft.diffset.save()

    review_request.save()
    draft.delete()

    return HttpResponse("Draft saved.")


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
        'reviews': review_request.review_set.filter(public=True),
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
def dashboard(request, template_name):
    direct_list = ReviewRequest.objects.filter(
        public=True,
        target_people=request.user,
        status='P')[:50]

    group_list = ReviewRequest.objects.filter(
        public=True,
        status='P',
        target_groups__in=request.user.groups.all()).exclude(
            id__in=[x.id for x in direct_list]
        )[:50 - len(direct_list)]

    your_list = ReviewRequest.objects.filter(
        status='P',
        submitter=request.user)[:50]

    # The most important part
    quips = {}
    for variable, place_id in zip(['direct', 'group', 'empty', 'mine'],
                                  ['dn',     'dg',    'de',    'dm']):
        quips[variable] = Quip.objects.filter(place=place_id).order_by('?')[:1]

    return render_to_response(template_name, RequestContext(request, {
        'direct_list': direct_list,
        'group_list': group_list,
        'your_list': your_list,
        'quips': quips,
    }))


@login_required
def group(request, name, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            target_groups__name__exact=name, public=True, status='P'),
        template_name=template_name,
        extra_context={
            'source': name,
        })


@login_required
def submitter(request, username, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            submitter__username__exact=username, public=True, status='P'),
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
        query = query | Q(reviewrequestdraft=draft)
    except ReviewRequestDraft.DoesNotExist:
        pass

    if revision != None:
        query = query | Q(revision=revision)

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

    query = Q(history=review_request.diffset_history) | Q(revision=revision)

    try:
        draft = review_request.reviewrequestdraft_set.get()
        query = query | Q(reviewrequestdraft=draft)
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
        review_request.save()
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
        return HttpResponseRedirect('/reviews/')
    else:
        return HttpResponseRedirect(review_request.get_absolute_url())


@login_required
def review_request_field(request, review_request_id, method, field_name=None):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.POST:
        if request.user != review_request.submitter:
            raise Http403()

        # XXX Should probably throw a real error here.
        if field_name == None:
            raise Http404()

        form_data = request.POST.copy()

        if not hasattr(review_request, field_name):
            raise Http404()

        draft, draft_is_new = \
            ReviewRequestDraft.objects.get_or_create(
                review_request=review_request,
                defaults={
                    'summary': review_request.summary,
                    'description': review_request.description,
                    'testing_done': review_request.testing_done,
                    'bugs_closed': review_request.bugs_closed,
                    'branch': review_request.branch,
                })

        if draft_is_new:
            map(draft.target_groups.add, review_request.target_groups.all())
            map(draft.target_people.add, review_request.target_people.all())

            if review_request.diffset_history.diffset_set.count() > 0:
                draft.diffset = \
                    review_request.diffset_history.diffset_set.latest()


        if field_name == "target_groups" or field_name == "target_people":
            values = re.split(r"[, ]+", form_data['value'])
            target = getattr(draft, field_name)
            target.clear()

            invalid_entries = []

            for value in values:
                try:
                    if field_name == "target_groups":
                        obj = Group.objects.get(name=value)
                    elif field_name == "target_people":
                        obj = User.objects.get(username=value)

                    target.add(obj)
                except:
                    invalid_entries.append(value)
        else:
            setattr(draft, field_name, form_data['value'])

        draft.save()
        obj = draft
    else:
        try:
            obj = review_request.reviewrequestdraft_set.get()
        except ReviewRequestDraft.DoesNotExist:
            obj = review_request

    if method == "xml" and field_name != None:
        if hasattr(obj, field_name):
            data = serialize(method, [obj], fields=[field_name])
        else:
            raise Http404() # XXX
    else:
        data = serialize(method, [obj])

    fieldobj = getattr(obj, field_name)

    if field_name == 'target_groups':
        value = ','.join([x.name for x in fieldobj.all()])
    elif field_name == 'target_people':
        value = ','.join([x.username for x in fieldobj.all()])
    else:
        value = fieldobj

    response = HttpResponse(value,
                            mimetype='application/%s' % method)
    if method == "json":
        response['X-JSON'] = data

    return response


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

            stripped_body = review.body.strip()
            if (stripped_body == "{{comments}}" or stripped_body == "") and \
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
                    'text': comment.text,
                })

    return render_to_response(template_name, RequestContext(request, {
        'comments': comments,
    }))


@login_required
def reply_save(request, review_request_id, revision, publish=False):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.POST:
        try:
            diffset = review_request.diffset_history.diffset_set.get(
                revision=revision)
        except DiffSet.DoesNotExist:
            raise Http404()

        review, review_is_new = Review.objects.get_or_create(
            user=request.user,
            review_request=review_request,
            public=False,
            reviewed_diffset=diffset)
        review.public = publish
        review.ship_it = request.POST.has_key('shipit')
        review.body = request.POST['body_top'] + "\n\n{{comments}}\n\n" + \
                      request.POST['body_bottom']
        review.save()

        if publish:
            return HttpResponse("Published")
        else:
            return HttpResponse("Saved")

    raise Http403()


@login_required
def reply_publish(request, review_request_id, revision):
    return reply_save(request, review_request_id, revision, True)


@login_required
def reply_delete(request, review_request_id, revision):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.POST:
        try:
            diffset = review_request.diffset_history.diffset_set.get(
                revision=revision)
        except DiffSet.DoesNotExist:
            raise Http404()

        try:
            review = Review.objects.get(user=request.user,
                                        review_request=review_request,
                                        public=False,
                                        reviewed_diffset=diffset)
            review.delete()
            return HttpResponse("Deleted")
        except Review.DoesNotExist:
            return HttpResponse("Not found")

    raise Http403()


@login_required
def reply_comments(request, review_request_id, revision,
                   template_name='reviews/inline_reply_comments.html'):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    try:
        diffset = review_request.diffset_history.diffset_set.get(
            revision=revision)
    except DiffSet.DoesNotExist:
        raise Http404()

    try:
        review = Review.objects.get(user=request.user,
                                    review_request=review_request,
                                    public=False,
                                    reviewed_diffset=diffset)
        comments = review.comments.all()
    except Review.DoesNotExist:
        comments = []

    return render_to_response(template_name, RequestContext(request, {
        'comments': comments,
    }))
