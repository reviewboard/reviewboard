import datetime
import Image
import os

from django.conf import settings
from django import template
from djblets.util.decorators import blocktag


register = template.Library()


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    output = "<div class=\"box-container\">"
    output += "<div class=\"box"
    if classname:
        output += " " + classname

    output += "\">\n"
    output += "<div class=\"box-inner\">"
    output += nodelist.render(context)

    output += "</div>"
    output += "</div>"
    output += "</div>\n"
    return output


@register.tag
@blocktag
def errorbox(context, nodelist, div_id=None):
    output = "<div class=\"errorbox\""
    if div_id:
        output += " id=\"%s\"" % div_id

    output += ">\n"
    output += nodelist.render(context)
    output += "</div>"
    return output


@register.simple_tag
def ageid(timestamp):
    # Convert datetime.date into datetime.datetime
    if timestamp.__class__ is not datetime.datetime:
        timestamp = datetime.datetime(timestamp.year, timestamp.month,
                                      timestamp.day)


    now = datetime.datetime.now()
    delta = now - (timestamp -
                   datetime.timedelta(0, 0, timestamp.microsecond))

    if delta.days == 0:
        return "age1"
    elif delta.days == 1:
        return "age2"
    elif delta.days == 2:
        return "age3"
    elif delta.days == 3:
        return "age4"
    else:
        return "age5"


@register.tag
@blocktag
def ifuserorperm(context, nodelist, user, perm):
    req_user = context.get('user', None)
    if user == req_user or req_user.has_perm(perm):
        return nodelist.render(context)

    return ''


# Heavily based on paginator by insin
# http://www.djangosnippets.org/snippets/73/
@register.inclusion_tag('paginator.html', takes_context=True)
def paginator(context, adjacent_pages=3):
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


@register.filter
def escapespaces(value):
    return value.replace('  ', '&nbsp; ').replace('\n', '<br />')


@register.filter
def humanize_list(value):
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return "%s and %s" % (s, value[-1])


@register.filter
def indent(value, numspaces=4):
    indent_str = " " * numspaces
    return indent_str + value.replace("\n", "\n" + indent_str)


# From http://www.djangosnippets.com/snippets/192
@register.filter
def thumbnail(file, size='400x100'):
    x, y = [int(x) for x in size.split('x')]
    basename, format = file.rsplit('.', 1)
    miniature = '%s_%s.%s' % (basename, size, format)
    miniature_filename = os.path.join(settings.MEDIA_ROOT, miniature)
    miniature_url = os.path.join(settings.MEDIA_URL, miniature)

    if not os.path.exists(miniature_filename):
        try:
            image = Image.open(os.path.join(settings.MEDIA_ROOT, file))
            image.thumbnail([x, y], Image.ANTIALIAS)
            image.save(miniature_filename, image.format)
        except IOError:
            return ""

    return miniature_url


@register.filter
def basename(value):
    return os.path.basename(value)
