from django import template
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = template.Library()

@register.inclusion_tag('diffviewer/sidebyside_diffline.html',
                        takes_context=True)
def sidebyside_diffline(context):
    cls = ""
    name = ""
    chunk_id, change, oldtext, newtext = context['chunk']

    if chunk_id != None:
        name = "%s.%s" % (context['file']['index'], chunk_id)

    if change != None:
        cls += change

    if oldtext == "":
        oldtext = " "

    if newtext == "":
        newtext = " "

    return {
        'class': cls,
        'oldtext': oldtext,
        'newtext': newtext,
        'name': name,
    }
