from __future__ import unicode_literals

from django import template


# This will add the localsite tags as built-in tags, and override the existing
# {% url %} tag in Django.
template.add_to_builtins(__name__ + '.localsite')
