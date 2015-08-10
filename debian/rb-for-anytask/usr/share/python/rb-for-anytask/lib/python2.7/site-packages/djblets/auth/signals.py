from __future__ import unicode_literals

from django.dispatch import Signal


user_registered = Signal(providing_args=["user"])
