import datetime
import Image
import os

from django import template
from django.conf import settings
from django.template import Variable, VariableDoesNotExist
from django.template.loader import render_to_string
from djblets.util.decorators import blocktag


register = template.Library()


@register.tag
@blocktag
def box(context, nodelist, classname=None):
    """
    Displays a box container around content, with an optional class name.
    """
    return render_to_string('box.html', {
        'classname': classname or "",
        'content': nodelist.render(context)
    })


@register.tag
@blocktag
def errorbox(context, nodelist, box_id=None):
    """
    Displays an error box around content, with an optional ID.
    """
    return render_to_string('errorbox.html', {
        'box_id': box_id or "",
        'content': nodelist.render(context)
    })


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
