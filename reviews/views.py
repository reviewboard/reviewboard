from django import newforms as forms
from djblets.auth.util import login_required
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.views.generic.list_detail import object_list
from djblets.auth.util import login_required
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory
from reviewboard.diffviewer.views import view_diff
from reviewboard.reviews.models import ReviewRequest, ReviewRequestDraft
from reviewboard.reviews.forms import NewReviewRequestForm
import re

def parse_change_desc(changedesc, review_request):
    summary = ""
    description = ""
    files = []

    changedesc_keys = {
        'QA Notes': "",
        'Testing Done': "",
        'Documentation Notes': "",
        'Bug Number': "",
        'Reviewed by': "",
        'Approved by': "",
        'Breaks vmcore compatibility': "",
        'Breaks vmkernel compatibility': "",
        'Breaks vmkdrivers compatibility': "",
        'Mailto': "",
    }

    process_summary = False
    process_description = False
    process_files = False

    cur_key = None

    for line in changedesc.split("\n"):
        if line == "Description:":
            process_summary = True
            continue
        elif line == "Files:":
            process_files = True
            cur_key = None
            continue
        elif line == "" or line == "\t":
            if process_summary:
                process_summary = False
                process_description = True
                continue

            line = ""
        elif line.startswith("\t"):
            line = line[1:]

            if process_files:
                files.append(line)
                continue
            elif line.find(':') != -1:
                key, value = line.split(':', 2)

                if changedesc_keys.has_key(key):
                    process_description = False
                    cur_key = key

                    changedesc_keys[key] = value.lstrip() + "\n"
                    continue

        line += "\n"

        if process_summary:
            summary += line
        elif process_description:
            description += line
        elif cur_key != None:
            changedesc_keys[cur_key] += line

    review_request.summary = summary.strip()
    review_request.description = description.strip()
    review_request.testing_done = changedesc_keys['Testing Done'].strip()

    review_request.bugs_closed = \
        ", ".join(re.split(r"[, ]+", changedesc_keys['Bug Number'])).strip()

    # This is gross.
    if len(files) > 0:
        parts = files[0].split('/')

        if parts[2] == "depot":
            review_request.branch = parts[4]


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
    changedesc = "\
Description:\n\
	This is my summary.\n\
	\n\
	This is a body of text, which can\n\
	wrap to the next line.\n\
\n\
	And skip lines.\n\
	\n\
\n\
	QA Notes:\n\
	Testing Done: I ate a hamburger and thought, \"Wow, that was rad.\"\n\
	Note how it carries to the next line, since some people do that.\n\
	Bug Number: 456123, 12873  1298371\n\
\n\
Files:\n\
	//depot/bora/foo/apps/lib/foo.c\n\
	//depot/bora/foo/apps/lib/bar.c\n\
"

    if request.POST:
        if request.POST.has_key('changenum'):
            changenum = request.POST['changenum']

            diffset_history = DiffSetHistory()
            diffset_history.save()

            review_request = ReviewRequest()
            parse_change_desc(changedesc, review_request)

            review_request.diffset_history = diffset_history
            review_request.submitter = request.user
            review_request.status = 'P'
            review_request.public = True
            review_request.save()

            return HttpResponseRedirect(review_request.get_absolute_url())
    else:
        # XXX Display an error page
        return HttpResponseRedirect('/reviews/new/')


def field(request, review_request_id, field_name):
    review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

    if request.POST:
        if request.user != review_request.submitter:
            raise Http403()

        form_data = request.POST.copy()

        if hasattr(review_request, field_name) and form_data['value']:
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
                for group in review_request.target_groups.all():
                    draft.target_groups.add(group)

                for person in review_request.target_people.all():
                    draft.target_people.add(person)

                if review_request.diffset_history.diffsets.count() > 0:
                    draft.diffset = \
                        review_request.diffset_history.diffsets.latest()


            setattr(draft, field_name, form_data['value'])
            draft.save()

            return HttpResponse(getattr(draft, field_name))
    else:
        try:
            obj = ReviewRequestDraft.objects.get(review_request=review_request)
        except ReviewRequestDraft.DoesNotExist:
            obj = review_request

        if field_name != None:
            if hasattr(obj, field_name):
                return HttpResponse(getattr(obj, field_name))

    raise Http404()


def revert_draft(request, object_id):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)
    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
        draft.delete()
    except ReviewRequestDraft.DoesNotExist:
        pass

    return HttpResponse("Draft reverted.")


def save_draft(request, object_id):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)
    draft = get_object_or_404(ReviewRequestDraft, review_request=review_request)

    review_request.summary = draft.summary
    review_request.description = draft.description
    review_request.testing_done = draft.testing_done
    review_request.bugs_closed = draft.bugs_closed
    review_request.branch = draft.branch

    review_request.target_groups.clear()
    for group in draft.target_groups.all():
        review_request.target_groups.add(group)

    review_request.target_people.clear()
    for person in draft.target_people.all():
        review_request.target_people.add(person)

    if draft.diffset:
        review_request.diffset_history.diffsets.add(draft.diffset)

    review_request.save()
    draft.delete()

    return HttpResponse("Draft saved.")


def review_detail(request, object_id, template_name):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
    except ReviewRequestDraft.DoesNotExist:
        draft = None

    return render_to_response(template_name, RequestContext(request, {
        'draft': draft,
        'object': review_request,
        'details': draft or review_request,
        'request': request,
    }))


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


def submitter_list(request, template_name):
    return object_list(request,
        queryset=User.objects.all(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


def group_list(request, template_name):
    return object_list(request,
        queryset=Group.objects.all(),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


def group(request, name, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            Q(target_groups__name__exact=name), Q(public=True)),
        template_name=template_name,
        extra_context={
            'source': name,
        })


def submitter(request, username, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            Q(submitter__username__exact=username), Q(public=True)),
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })


def diff(request, object_id, revision=None):
    review_request = get_object_or_404(ReviewRequest, pk=object_id)

    query = Q(diffsethistory=review_request.diffset_history)

    try:
        draft = ReviewRequestDraft.objects.get(review_request=review_request)
        query = query | Q(reviewrequestdraft=draft)
    except ReviewRequestDraft.DoesNotExist:
        pass

    if revision != None:
        query = query | Q(revision=revision)

    diffset = get_object_or_404(DiffSet, query)
    return view_diff(request, diffset.id)
