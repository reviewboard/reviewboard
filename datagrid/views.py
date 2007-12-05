from django.views.generic.list_detail import object_list


def sortable_object_list(request, queryset, default_sort="",
                         paginate_by=50, extra_context={}, *args, **kwargs):
    """
    A sortable list of objects. The sorted fields can be manipulated
    using the sort parameter on the URL.
    """
    sort_list = None
    sort = request.GET.get('sort', default_sort)

    if sort:
        sort_list = sort.split(',')
        queryset = queryset.order_by(*sort_list)

    return object_list(request,
                       queryset=queryset,
                       paginate_by=paginate_by,
                       allow_empty=True,
                       extra_context=dict(
                           {'app_path': request.path,
                            'sort_list': sort_list},
                           **extra_context
                       ),
                       *args, **kwargs)
