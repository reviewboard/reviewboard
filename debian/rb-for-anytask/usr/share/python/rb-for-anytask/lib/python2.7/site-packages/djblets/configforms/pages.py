from __future__ import unicode_literals

from django.template.context import RequestContext
from django.template.loader import render_to_string


class ConfigPage(object):
    """Base class for a page of configuration forms.

    Each ConfigPage is represented in the main page by an entry in the
    navigation sidebar. When the user has navigated to that page, any
    forms owned by the ConfigPage will be displayed.
    """
    page_id = None
    page_title = None
    form_classes = None
    template_name = 'configforms/config_page.html'

    def __init__(self, config_view, request, user):
        self.config_view = config_view
        self.request = request
        self.forms = [
            form_cls(self, request, user)
            for form_cls in self.form_classes
        ]

    def is_visible(self):
        """Returns whether the page should be visible.

        Visible pages are shown in the sidebar and can be navigated to.

        By default, a page is visible if at least one of its forms are
        also visible.
        """
        for form in self.forms:
            if form.is_visible():
                return True

        return False

    def render(self):
        """Renders the page as HTML."""
        return render_to_string(
            self.template_name,
            RequestContext(self.request, {
                'page': self,
                'forms': self.forms,
            }))
