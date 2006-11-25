from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.list_detail import object_list
from django.views.generic.create_update import create_object
from reviewboard.reviews.models import ReviewRequest, Person, Group

def new_from_changenum(request):
    return HttpResponseRedirect('/')

def new_review_request(request, template_name,
                       changenum_path='changenum'):
    manipulator = ReviewRequest.AddManipulator()

    if request.POST:
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
            new_reviewreq.save()

            return HttpResponseRedirect('/reviews/%s/edit/' % new_reviewreq.id)
    else:
        errors = form_data = {}

    return create_object(request,
        model=ReviewRequest,
        template_name=template_name,
        extra_context={
            'changenum_path': changenum_path,
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
