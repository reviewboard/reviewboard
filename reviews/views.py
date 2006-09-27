from django.views.generic.list_detail import object_list
from reviewboard.reviews.models import ReviewRequest

def group(request, name, template_name, paginate_by=25, allow_empty=True):
    return object_list(request,
        queryset=ReviewRequest.objects.filter(target_groups__name__exact=name),
        paginate_by=paginate_by,
        allow_empty=allow_empty,
        template_name=template_name,
        extra_context={
            'source': name,
        })


def submitter(request, username, template_name, paginate_by=25, allow_empty=True):
    return object_list(request,
        queryset=ReviewRequest.objects.filter(
            submitter__username__exact=username),
        paginate_by=paginate_by,
        allow_empty=allow_empty,
        template_name=template_name,
        extra_context={
            'source': username + "'s",
        })
