from django import template
from django.template import Variable, VariableDoesNotExist


register = template.Library()


@register.inclusion_tag('datagrid/column_header.html', takes_context=True)
def column_header(context, field_name, text):
    """
    Displays a sortable column header.

    The column header will include the current sort indicator, if it belongs
    in the sort list. It will also be made clickable in order to modify
    the sort order appropriately.
    """
    sort_list = None

    try:
        temp = Variable('sort_list').resolve(context)

        if temp:
            # Make a copy of the list so that we don't modify the one in
            # the context.
            sort_list = list(temp)
    except VariableDoesNotExist:
        pass

    in_sort = False
    sort_ascending = False
    sort_primary = False

    if sort_list:
        rev_field_name = "-%s" % field_name
        new_field_name = field_name
        cur_field_name = ""

        if field_name in sort_list:
            # This column is currently being sorted in ascending order.
            sort_ascending = True
            cur_field_name = field_name
            new_field_name = rev_field_name
        elif rev_field_name in sort_list:
            # This column is currently being sorted in descending order.
            sort_ascending = False
            cur_field_name = rev_field_name
            new_field_name = field_name

        if cur_field_name:
            in_sort = True
            sort_primary = (sort_list[0] == cur_field_name)

            if not sort_primary:
                # If this is not the primary column, we want to keep the
                # sort order intact.
                new_field_name = cur_field_name

            # Remove this column from the current location in the list
            # so we can move it to the front of the list.
            sort_list.remove(cur_field_name)

        # Insert the column name into the beginning of the sort list.
        sort_list.insert(0, new_field_name)
    else:
        # There's no sort list to begin with. Make this column the only
        # entry.
        sort_list = [field_name]

    # We can only support two entries in the sort list, so truncate this.
    del(sort_list[2:])

    request = context['request']
    url_prefix = "?"

    for key in request.GET:
        if key != "sort":
            url_prefix += "%s=%s&" % (key, request.GET[key])

    url_prefix += "sort="

    unsort_url = url_prefix + ','.join(sort_list[1:])
    sort_url   = url_prefix + ','.join(sort_list)

    return {
        'column_text': text,
        'in_sort': in_sort,
        'sort_ascending': sort_ascending,
        'sort_primary': sort_primary,
        'sort_url': sort_url,
        'unsort_url': unsort_url,
    }


# Heavily based on paginator by insin
# http://www.djangosnippets.org/snippets/73/
@register.inclusion_tag('datagrid/paginator.html', takes_context=True)
def paginator(context, adjacent_pages=3):
    """
    Renders a paginator used for jumping between pages of results.
    """
    page_nums = range(max(1, context['page'] - adjacent_pages),
                      min(context['pages'], context['page'] + adjacent_pages)
                      + 1)

    return {
        'hits': context['hits'],
        'results_per_page': context['results_per_page'],
        'page': context['page'],
        'pages': context['pages'],
        'page_numbers': page_nums,
        'next': context['next'],
        'previous': context['previous'],
        'has_next': context['has_next'],
        'has_previous': context['has_previous'],
        'show_first': 1 not in page_nums,
        'show_last': context['pages'] not in page_nums,
    }


