from django import template
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = template.Library()

@register.inclusion_tag('diffviewer/sidebyside_diffline.html',
                        takes_context=True)
def sidebyside_diffline(context):
    lineclass = ""
    line = context['line']

    if line[0] != None:
        lineclass = "new_chunk "

    if line[1] != None:
        lineclass += line[1]

    oldline = line[2]
    if oldline == "":
        oldline = " "

    newline = line[3]
    if newline == "":
        newline = " "

    return {
        'class': lineclass,
        'oldline': oldline,
        'newline': newline,
    }
