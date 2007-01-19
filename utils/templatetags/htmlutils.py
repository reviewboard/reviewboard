from django import template
from django.template import resolve_variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from django.template.defaultfilters import capfirst
import datetime, time

register = template.Library()

class BoxNode(template.Node):
    def __init__(self, nodelist, tagid):
        self.nodelist = nodelist
        self.tagid = tagid

    def render(self, context):
        output = "<div class=\"box\""
        if self.tagid:
            output += " id=\"%s\"" % self.tagid

        output += ">\n"
        output += self.render_title_area(context)
        output += "<div class=\"top\"><div class=\"top-left\">&nbsp;" + \
                  "</div>&nbsp;</div>\n"

        output += "<div class=\"body\">\n"
        output += "<div class=\"content\">\n"
        output += self.nodelist.render(context)
        output += "</div>\n"
        output += "</div>\n"

        output += "<div class=\"bottom\"><div class=\"bottom-left\">&nbsp;" + \
                  "</div>&nbsp;</div>\n"
        output += "</div>\n"
        return output

    def render_title_area(self, context):
        return ""

@register.tag
def box(parser, token):
    bits = token.contents.split()
    tagname = bits[0]

    if len(bits) > 2:
        raise TemplateSyntaxError, \
            "%r tag takes zero or one arguments." % tagname

    if len(bits) == 2:
        tagid = bits[1]
    else:
        tagid = None

    nodelist = parser.parse(('end' + tagname,))
    parser.delete_first_token()
    return BoxNode(nodelist, tagid)


class TitleBoxNode(BoxNode):
    def __init__(self, nodelist, tagid, title):
        BoxNode.__init__(self, nodelist, tagid)
        self.title = title

    def render_title_area(self, context):
        if self.title:
            try:
                title = resolve_variable(self.title, context)
            except VariableDoesNotExist:
                title = self.title

            return "<div class=\"title\">%s</div>" % title

        return ""

@register.tag
def titlebox(parser, token):
    bits = token.split_contents()
    tagname = bits[0]

    if len(bits) != 2 and len(bits) != 3:
        raise TemplateSyntaxError, \
              "%r tag takes up to two arguments." % tagname

    title = bits[1]
    if title[0] == '"':
        title = title[1:-1]

    if len(bits) == 3:
        tagid = bits[2]
    else:
        tagid = None

    nodelist = parser.parse(('end' + tagname,))
    parser.delete_first_token()
    return TitleBoxNode(nodelist, tagid, title)


class TabBoxNode(BoxNode):
    def __init__(self, nodelist, tagid, tabs):
        BoxNode.__init__(self, nodelist, tagid)
        self.tabs = tabs

    def render_title_area(self, context):
        s = "<ul class=\"tablist\">\n"

        for url, title in self.tabs:
            try:
                new_url = resolve_variable(url, context)
                url = new_url
            except VariableDoesNotExist:
                pass

            if url == ".":
                attrs = " class=\"active\""
            else:
                attrs = ""

            s += "<li%s><a href=\"%s\">%s</a></li>\n" % (attrs, url, title)

        s += "</ul>\n"

        return s

@register.tag
def tabbox(parser, token):
    bits = list(token.split_contents())
    tagname = bits[0]

    if len(bits) <= 2:
        raise TemplateSyntaxError, \
            "%r takes a tag ID and pairs of id, title arguments" % tagname
    elif len(bits) % 2 == 1:
        raise TemplateSyntaxError, \
            "%r received unbalanced id, title pairs" % tagname

    tagid = bits[1]
    tabs = ()

    i = 2
    while i < len(bits):
        title = bits[i + 1]
        if title[0] == '"':
            title = title[1:-1]

        tabs += (bits[i], title),
        i += 2

    nodelist = parser.parse(('end' + tagname,))
    parser.delete_first_token()
    return TabBoxNode(nodelist, tagid, tabs)


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


class FormField(template.Node):
    def __init__(self, elementid):
        self.elementid = elementid

    def render(self, context):
        formelement = "form.%s" % self.elementid
        try:
            field_str = resolve_variable(formelement, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid element ID %s passed to formfield tag." % formelement

        label = capfirst(self.elementid.replace('_', ' '))

        try:
            error_list = resolve_variable("%s.html_error_list" % formelement,
                                          context)
        except VariableDoesNotExist:
            error_list = ""

        output  = "  <tr>\n"
        output += "   <td class=\"label\"><label for=\"id_%s\">%s:" \
                  "</label></td>\n" % (self.elementid, label)
        output += "   <td class=\"field\">%s</td>\n" % field_str
        output += "   <td>%s</td>\n" % error_list
        output += "  </tr>\n"
        return output

@register.tag
def formfield(parser, token):
    try:
        tag_name, elementid = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires an element ID and a string label"

    return FormField(elementid)


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
