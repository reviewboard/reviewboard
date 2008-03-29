from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template.loader import render_to_string

from reviewboard.admin.checks import check_updates_required


def manual_updates_required(request,
                            template_name="admin/manual_updates_required.html"):
    updates = check_updates_required()

    return render_to_response(template_name, RequestContext(request, {
        'updates': [render_to_string(template_name,
                                     RequestContext(request, extra_context))
                    for (template_name, extra_context) in updates],
    }))
