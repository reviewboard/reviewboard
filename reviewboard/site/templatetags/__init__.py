from __future__ import unicode_literals

from django.template.base import add_to_builtins


# This will add the localsite tags as built-in tags, and override the existing
# {% url %} tag in Django.
add_to_builtins(__name__ + '.localsite')
