import re

from django import template
from django.template import resolve_variable
from django.template import NodeList, VariableDoesNotExist
from django.utils.html import escape
from reviewboard.diffviewer.views import get_diff_files

register = template.Library()

class ForChunksWithLines(template.Node):
    def __init__(self, filediff, first_line, num_lines, nodelist_loop):
        self.filediff = filediff
        self.first_line = first_line
        self.num_lines = num_lines
        self.nodelist_loop = nodelist_loop

    def get_variable(self, var, context):
        try:
            return resolve_variable(var, context)
        except VariableDoesNotExist:
            raise template.TemplateSyntaxError, \
                "Invalid variable '%s' passed to 'forchunkswithlines' tag." % \
                var

    def render(self, context):
        filediff = self.get_variable(self.filediff, context)
        files = get_diff_files(filediff.diffset)

        for file in files:
            if file["filediff"].id == filediff.id:
                return self.render_file(file, context)

        return "Missing lines"

    def render_file(self, file, context):
        first_line = int(self.get_variable(self.first_line, context))
        num_lines = int(self.get_variable(self.num_lines, context))

        nodelist = NodeList()
        context.push()

        for chunk in file['chunks']:
            lines = chunk['lines']
            if first_line >= lines[0][0] and \
               first_line <= lines[-1][0]:
                start_index = first_line - lines[0][0]

                if first_line + num_lines <= lines[-1][0]:
                    last_index = start_index + num_lines
                else:
                    last_index = len(lines)

                new_chunk = {
                    'lines': chunk['lines'][start_index:last_index],
                    'numlines': last_index - start_index,
                    'change': chunk['change'],
                }

                context['chunk'] = new_chunk

                for node in self.nodelist_loop:
                    nodelist.append(node.render(context))

                first_line += new_chunk['numlines']
                num_lines -= new_chunk['numlines']

                assert num_lines >= 0
                if num_lines == 0:
                    break

        context.pop()
        return nodelist.render(context)


@register.tag
def forchunkswithlines(parser, token):
    try:
        tag_name, filediff, first_line, num_lines = token.contents.split()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a filediff, first line and number of lines"

    nodelist_loop = parser.parse(('endforchunkswithlines'),)
    parser.delete_first_token()

    return ForChunksWithLines(filediff, first_line, num_lines,
                              nodelist_loop)


@register.filter
def highlightregion(value, r):
    if r == None:
        return escape(value)
    else:
        prev = 0
        s = ""

        for i, j in r:
            s += "%s<span class=\"hl\">%s</span>" % \
                 (escape(value[prev:i]), escape(value[i:j]))
            prev = j

        s += escape(value[prev:])

        return s


extraWhitespace = re.compile(r'(\s+$| +\t)')

@register.filter
def showextrawhitespace(value):
    return extraWhitespace.sub(
        lambda m: "<span class=\"ew\">%s</span>" % m.group(0),
        value)
