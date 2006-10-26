from django.views.generic.list_detail import object_list
from django.views.generic.create_update import create_object
from reviewboard.reviews.models import ReviewRequest, Person, Group

def new_review_request(request, template_name):
    manipulator = ReviewRequest.AddManipulator()

    if request.POST:
        # XXX
        person, person_is_new = Person.objects.get_or_create(username='christian')
        if person_is_new:
            person.save()

        new_data = request.POST.copy()
        new_data['submitter'] = person.id
        errors = manipulator.get_validation_errors(new_data)

        if not errors:
            manipulator.do_html2python(new_data)

            try:
                new_reviewreq = manipulator.save(new_data)
                new_reviewreq.submitter = person
                new_reviewreq.save()

                # TODO: E-mail it out
            except:
                print errors

    return create_object(request,
        model=ReviewRequest,
        template_name=template_name,
        follow={'time_added': False,
                'last_updated': False,
                'submitter': False,
                'status': False,})


def group(request, name, template_name, paginate_by=25, allow_empty=True):
    return object_list(request,
        queryset=ReviewRequest.objects.filter(target_groups__name__exact=name),
        paginate_by=paginate_by,
        allow_empty=allow_empty,
        template_name=template_name,
        extra_context={
            'source': name,
        })

def review_list(request, queryset, template_name, extra_context={}):
    return object_list(request,
        queryset=queryset,
        paginate_by=50,
        allow_empty=True,
        template_name=template_name,
        extra_context=dict(
            {'app_path': request.path},
            **extra_context
        ))


def submitter(request, username, template_name):
    return review_list(request,
        queryset=ReviewRequest.objects.filter(
            submitter__username__exact=username),
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })


def submitter_list(request, template_name):
    return object_list(request,
        queryset=Person.objects.all(),
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
