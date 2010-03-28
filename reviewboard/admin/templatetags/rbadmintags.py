from django import template
from django.core.urlresolvers import reverse


register = template.Library()


@register.inclusion_tag('admin/subnav_item.html', takes_context=True)
def admin_subnav(context, url_name, name):
    """
    Returns a <li> containing a link to the desired setting tab.
    """
    request = context.get('request')
    url = reverse(url_name)

    return {
        'url': url,
        'name': name,
        'current': url == request.path,
     }