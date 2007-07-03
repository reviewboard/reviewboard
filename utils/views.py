from django.views.generic.list_detail import object_list

from reviewboard.accounts.models import Profile


def sortable_object_list(request, queryset, default_sort="",
                         extra_context={}, *args, **kwargs):
    sort_list = None
    sort = request.GET.get('sort', default_sort)

    if sort:
        sort_list = sort.split(',')
        queryset = queryset.order_by(*sort_list)

    return object_list(request,
                       queryset=queryset,
                       paginate_by=50,
                       allow_empty=True,
                       extra_context=dict(
                           {'app_path': request.path,
                            'sort_list': sort_list},
                           **extra_context
                       ),
                       *args, **kwargs)
