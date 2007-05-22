import datetime
import Image
import os
import time

from django.conf import settings
from django import template
from django.template import resolve_variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from django.template.defaultfilters import capfirst

register = template.Library()

class BoxNode(template.Node):
    def __init__(self, nodelist, classname):
        self.nodelist = nodelist
        self.classname = classname

    def render(self, context):
        output = "<div class=\"box-container\">"
        output += "<div class=\"box"
        if self.classname:
            output += " " + self.classname

        output += "\">\n"
        output += "<div class=\"box-inner\">"
        output += self.nodelist.render(context)

        output += "</div>"
        output += "</div>"
        output += "</div>\n"
        return output

    def render_title_area(self, context):
        return ""

@register.tag
def box(parser, token):
    classname = None

    if len(token.contents.split()) > 1:
        try:
            tag_name, classname = token.split_contents()
        except ValueError:
            raise template.TemplateSyntaxError, \
                "%r tag requires a class name" % tagname

    nodelist = parser.parse(('endbox'),)
    parser.delete_first_token()
    return BoxNode(nodelist, classname)


class ErrorBoxNode(template.Node):
    def __init__(self, nodelist, tagid):
        self.nodelist = nodelist
        self.tagid = tagid

    def render(self, context):
        output = "<div class=\"errorbox\""
        if self.tagid:
            output += " id=\"%s\"" % self.tagid

        output += ">\n"
        output += self.nodelist.render(context)
        output += "</div>"
        return output

@register.tag
def errorbox(parser, token):
    bits = token.contents.split()
    tagname = bits[0]

    if len(bits) > 1:
        raise TemplateSyntaxError, \
            "%r tag takes zero or one arguments." % tagname

    if len(bits) == 2:
        tagid = bits[1]
    else:
        tagid = None

    nodelist = parser.parse(('end' + tagname,))
    parser.delete_first_token()
    return ErrorBoxNode(nodelist, tagid)


class AgeId(template.Node):
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def render(self, context):
        try:
            timestamp = resolve_variable(self.timestamp, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid element ID %s passed to ageid tag." % self.timestamp

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
def ageid(parser, token):
    try:
        tag_name, timestamp = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a timestamp"

    return AgeId(timestamp)


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

    return s + " and " + value[-1]


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
        image = Image.open(os.path.join(settings.MEDIA_ROOT, file))
        image.thumbnail([x, y], Image.ANTIALIAS)
        image.save(miniature_filename, image.format)
    return miniature_url

@register.filter
def basename(value):
    return os.path.basename(value)
