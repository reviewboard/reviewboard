from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views.generic.list_detail import object_list
from django.views.generic.create_update import create_object
from reviewboard.reviews.models import ReviewRequest, Person, Group
from reviewboard.reviews.forms import AddReviewRequestManipulator
import re


def parse_change_desc(changedesc, result_dict):
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

    result_dict['summary'] = summary
    result_dict['description'] = description
    result_dict['testing_done'] = changedesc_keys['Testing Done']

    result_dict['bugs_closed'] = \
        ", ".join(re.split(r"[, ]+", changedesc_keys['Bug Number'])).strip()

    result_dict['target_groups'] = 'hosted-ui, foo-group'
    result_dict['target_people'] = 'davidt, christian'

    # This is gross.
    if len(files) > 0:
        parts = files[0].split('/')

        if parts[2] == "depot":
            result_dict['branch'] = parts[4]


def new_review_request(request, template_name='reviews/new.html',
                       changenum_path='changenum'):
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

    manipulator = AddReviewRequestManipulator()
    new_data = {}
    errors = {}

    if request.POST:
        if request.POST.has_key('changenum'):
            changenum = request.POST['changenum']
            parse_change_desc(changedesc, new_data)
        else:
            # XXX
            person, person_is_new = \
                Person.objects.get_or_create(username='christian')

            if person_is_new:
                person.save()

            new_data = request.POST.copy()
            new_data['submitter'] = person.id
            new_data['status'] = 'P'
            errors = manipulator.get_validation_errors(new_data)

            if not errors:
                manipulator.do_html2python(new_data)

                new_reviewreq = manipulator.save(new_data)
                new_reviewreq.submitter = person
                new_reviewreq.public = True
                new_reviewreq.save()

                return HttpResponseRedirect('/reviews/%s/edit/' %
                                            new_reviewreq.id)

    form = forms.FormWrapper(manipulator, new_data, errors)
    return render_to_response(template_name, {
        'form': form,
    })


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
        queryset=Person.objects.all().order_by('name'),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


def group_list(request, template_name):
    return object_list(request,
        queryset=Group.objects.all().order_by('name'),
        template_name=template_name,
        paginate_by=50,
        allow_empty=True,
        extra_context={
            'app_path': request.path,
        })


def group(request, name, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            target_groups__name__exact=name),
        template_name=template_name,
        extra_context={
            'source': name,
        })


def submitter(request, username, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            submitter__username__exact=username),
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })
