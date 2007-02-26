from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """User profile.  Contains some basic configurable settings"""
    user = models.ForeignKey(User, unique=True)

    collapsed_diffs = models.BooleanField(default=True)
    wordwrapped_diffs = models.BooleanField(default=True)
