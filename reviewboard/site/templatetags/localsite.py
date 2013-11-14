from __future__ import unicode_literals

from django import template
from django.core.urlresolvers import NoReverseMatch, ViewDoesNotExist
from django.template.defaulttags import url as django_url


register = template.Library()


class LocalSiteURLNode(template.Node):
    def __init__(self, url_node):
        self.url_node = url_node
        self.args = list(url_node.args)
        self.kwargs = url_node.kwargs.copy()

    def render(self, context):
        # We're going to try two versions of the URL: one with the local
        # site name, and one without. Of course, we only try with the
        # name if that's provided in the context.
        #
        # We will be plugging in a set of arguments to url_node before
        # rendering, based on the backed up values in LocalSiteURLNode's
        # constructor.
        #
        # Since {% url %} can't mix positional and keyword argumetns, we
        # must figure out whether we want to use args or kwargs.

        local_site_name = context.get('local_site_name', None)

        if local_site_name:
            local_site_var = template.Variable('local_site_name')

            if self.args:
                self.url_node.args = [local_site_var] + self.args
            else:
                self.url_node.kwargs['local_site_name'] = local_site_var

            try:
                return self.url_node.render(context)
            except (NoReverseMatch, ViewDoesNotExist):
                # We'll try it again without those arguments.
                pass

        self.url_node.args = list(self.args)
        self.url_node.kwargs = self.kwargs.copy()

        return self.url_node.render(context)


@register.tag
def url(parser, token):
    return LocalSiteURLNode(django_url(parser, token))
