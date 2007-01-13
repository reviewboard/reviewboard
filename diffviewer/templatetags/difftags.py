from django import template
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = template.Library()

@register.inclusion_tag('diffviewer/sidebyside_diffline.html',
                        takes_context=True)
def sidebyside_diffline(context):
    lineclass = ""
    name = ""
    line = context['line']

    chunk_changed, chunk_id, change, oldline, newline = context['line']

    if chunk_changed:
        lineclass = "new_chunk "

    if chunk_id != None:
        name = "%s.%s" % (context['file']['id'], chunk_id)

    if change != None:
        lineclass += change

    if oldline == "":
        oldline = " "

    if newline == "":
        newline = " "

    return {
        'class': lineclass,
        'oldline': oldline,
        'newline': newline,
        'name': name,
    }
