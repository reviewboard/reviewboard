# {{extension_name}} Extension for Review Board.

from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, include
from reviewboard.extensions.base import Extension


class {{class_name}}(Extension):
    metadata = {
        'Name': '{{extension_name}}',
        'Summary': 'Describe your extension here.',
    }

{%- if is_configurable %}
    is_configurable = True
{%- endif %}

    def initialize(self):
        # Your extension initialization is done here.
        pass
