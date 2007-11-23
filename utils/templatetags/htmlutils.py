import datetime
import Image
import os

from django import template
from django.conf import settings
from django.template import Variable, VariableDoesNotExist
from djblets.util.decorators import blocktag


register = template.Library()


class ColumnHeader(template.Node):
    def __init__(self, field_name, text):
        self.field_name = field_name
        self.text = text

    def render(self, context):
        try:
            temp = Variable('sort_list').resolve(context)

            if temp:
                sort_list = list(temp)
            else:
                sort_list = None
        except VariableDoesNotExist:
            sort_list = None

        sort_text = ""
        sort_img = ""

        if sort_list:
            rev_field_name = "-%s" % self.field_name
            new_field_name = self.field_name

            try:
                i = sort_list.index(self.field_name)
                sort_text = "(Ascending)"

                if i == 0:
                    sort_img = "sort_asc_primary.png"
                    new_field_name = rev_field_name
                else:
                    sort_img = "sort_asc_secondary.png"
                    new_field_name = self.field_name
            except ValueError:
                try:
                    i = sort_list.index(rev_field_name)
                    sort_text = "(Descending)"

                    if i == 0:
                        sort_img = "sort_desc_primary.png"
                        new_field_name = self.field_name
                    else:
                        sort_img = "sort_desc_secondary.png"
                        new_field_name = rev_field_name
                except ValueError:
                    i = -1

            if i != -1:
                del(sort_list[i])
            else:
                sort_list = sort_list[:2]

            sort_list.insert(0, new_field_name)
        else:
            sort_list = [self.field_name]

        request = context['request']
        url_prefix = "?"

        for key in request.GET:
            url_prefix += "%s=%s&" % (key, request.GET[key])

        # XXX I'm not too excited about this function hard-coding
        #     image filenames and HTML. This should probably move out to
        #     an included template at some point.
        url = "%ssort=%s" % (url_prefix, ','.join(sort_list))
        s  = '<th onclick="javascript:window.location = \'%s\'">' % url
        s += '<a href="%s">%s' % (url, self.text)

        if sort_text:
            s += ' <img src="/images/%s" alt="%s"' % (sort_img, sort_text)
            s += ' width="9" height="5" border="0" /></a>'
            s += (' <a class="unsort" href="%ssort=%s">' +
                  '<img src="/images/unsort.png" width="7" height="7" ' +
                  'border="0" alt="Unsort" />') % \
                 (url_prefix, ','.join(sort_list[1:]))

        s += '</a></th>'

        return s


@register.tag
def column_header(parser, token):
    """
    Displays a sortable column header.

    The column header will include the current sort indicator, if it belongs
    in the sort list. It will also be made clickable in order to modify
    the sort order appropriately.
    """
    try:
        tag_name, field_name, text = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag required a field name and column text"

    return ColumnHeader(field_name.strip('"'), text.strip('"'))


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    """
    Displays a box container around content, with an optional class name.
    """
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
    """
    Displays an error box around content, with an optional ID.
    """
    output = "<div class=\"errorbox\""
    if div_id:
        output += " id=\"%s\"" % div_id

    output += ">\n"
    output += nodelist.render(context)
    output += "</div>"
    return output


@register.simple_tag
def ageid(timestamp):
    """
    Returns an ID based on the difference between a timestamp and the
    current time.

    The ID is returned based on the following differences in days:

      ========== ====
      Difference ID
      ========== ====
      0          age1
      1          age2
      2          age3
      3          age4
      4 or more  age5
      ========== ====
    """

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


@register.simple_tag
def crop_image(file, x, y, width, height):
    """
    Crops an image at the specified coordinates and dimensions, returning the
    resulting URL of the cropped image.
    """
    if file.find(".") != -1:
        basename, format = file.rsplit('.', 1)
        new_name = '%s_%s_%s_%s_%s.%s' % (basename, x, y, width, height, format)
    else:
        basename = file
        new_name = '%s_%s_%s_%s_%s' % (basename, x, y, width, height)

    new_path = os.path.join(settings.MEDIA_ROOT, new_name)
    new_url = os.path.join(settings.MEDIA_URL, new_name)

    if not os.path.exists(new_path):
        try:
            image = Image.open(os.path.join(settings.MEDIA_ROOT, file))
            image = image.crop((x, y, x + width, y + height))
            image.save(new_path, image.format)
        except (IOError, KeyError):
            return ""

    return new_url


@register.tag
@blocktag
def ifuserorperm(context, nodelist, user, perm):
    """
    Renders content depending on whether the logged in user is the specified
    user or has the specified permission.

    This is useful when you want to restrict some code to the owner of a
    review request or to a privileged user that has the abilities of the
    owner.

    Example::

        {% ifuserorperm myobject.user "myobject.can_change_status" %}
        Owner-specific content here...
        {% endifuserorperm %}
    """
    req_user = context.get('user', None)
    if user == req_user or req_user.has_perm(perm):
        return nodelist.render(context)

    return ''


@register.tag
@blocktag
def attr(context, nodelist, attrname):
    """
    Sets an HTML attribute to a value if the value is not an empty string.
    """
    content = nodelist.render(context)

    if content.strip() == "":
        return ""

    return ' %s="%s"' % (attrname, content)


# Heavily based on paginator by insin
# http://www.djangosnippets.org/snippets/73/
@register.inclusion_tag('paginator.html', takes_context=True)
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


@register.filter
def escapespaces(value):
    """
    HTML-escapes all spaces with ``&nbsp;`` and newlines with ``<br />``.
    """
    return value.replace('  ', '&nbsp; ').replace('\n', '<br />')


@register.filter
def humanize_list(value):
    """
    Humanizes a list of values, inserting commands and "and" where appropriate.

      ========================= ======================
      Example List              Resulting string
      ========================= ======================
      ``["a"]``                 ``"a"``
      ``["a", "b"]``            ``"a and b"``
      ``["a", "b", "c"]``       ``"a, b and c"``
      ``["a", "b", "c", "d"]``  ``"a, b, c, and d"``
      ========================= ======================
    """
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
    """
    Indents a string by the specified number of spaces.
    """
    indent_str = " " * numspaces
    return indent_str + value.replace("\n", "\n" + indent_str)


# From http://www.djangosnippets.org/snippets/192
@register.filter
def thumbnail(file, size='400x100'):
    """
    Creates a thumbnail of an image with the specified size, returning
    the URL of the thumbnail.
    """
    x, y = [int(x) for x in size.split('x')]

    if file.find(".") != -1:
        basename, format = file.rsplit('.', 1)
        miniature = '%s_%s.%s' % (basename, size, format)
    else:
        basename = file
        miniature = '%s_%s' % (basename, size)

    miniature_filename = os.path.join(settings.MEDIA_ROOT, miniature)
    miniature_url = os.path.join(settings.MEDIA_URL, miniature)

    if not os.path.exists(miniature_filename):
        try:
            image = Image.open(os.path.join(settings.MEDIA_ROOT, file))
            image.thumbnail([x, y], Image.ANTIALIAS)
            image.save(miniature_filename, image.format)
        except IOError:
            return ""
        except KeyError:
            return ""

    return miniature_url


@register.filter
def basename(value):
    """
    Returns the basename of a path.
    """
    return os.path.basename(value)


@register.filter
def realname(user):
    """
    Returns the real name of a user, if available, or the username.

    If the user has a full name set, this will return the full name.
    Otherwise, this returns the username.
    """
    full_name = user.get_full_name()
    if full_name == '':
        return user.username
    else:
        return full_name


@register.simple_tag
def form_dialog_fields(form):
    """
    Translates a Django Form object into a JavaScript list of fields.
    The resulting list of fields can be used to represent the form
    dynamically.
    """
    s = ''

    for field in form:
        s += "{ name: '%s', " % field.name

        if field.is_hidden:
            s += "hidden: true, "
        else:
            s += "label: '%s', " % field.label_tag(field.label + ":")

        s += "widget: '%s' }," % unicode(field)

    # Chop off the last ','
    return "[ %s ]" % s[:-1]
