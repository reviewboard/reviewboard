# {{extension_name}} Extension for Review Board.
from django.conf import settings
from django.conf.urls.defaults import patterns, include
from reviewboard.extensions.base import Extension
{%- if dashboard_link is not none %}
from reviewboard.extensions.hooks import DashboardHook, URLHook
{% endif %}

{%- if dashboard_link is not none %}
class {{class_name}}URLHook(URLHook):
    def __init__(self, extension, *args, **kwargs):
        pattern = patterns('', (r'^{{package_name}}/',
                            include('{{package_name}}.urls')))
        super({{class_name}}URLHook, self).__init__(extension, pattern)


class {{class_name}}DashboardHook(DashboardHook):
    def __init__(self, extension, *args, **kwargs):
        entries = [{
            'label': '{{dashboard_link}}',
            'url': settings.SITE_ROOT + '{{package_name}}/',
        }]
        super({{class_name}}DashboardHook, self).__init__(extension,
                entries=entries, *args, **kwargs)
{%- endif %}

class {{class_name}}(Extension):
{%- if is_configurable %}
    is_configurable = True

{%- endif %}
    def __init__(self, *args, **kwargs):
        super({{class_name}}, self).__init__()
{%- if dashboard_link is not none %}
        self.url_hook = {{class_name}}URLHook(self)
        self.dashboard_hook = {{class_name}}DashboardHook(self)
{%- endif %}

