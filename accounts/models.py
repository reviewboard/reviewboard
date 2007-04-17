from django.db import models
from django.contrib.auth.models import User
from reviewboard.reviews.models import ReviewRequest


class Profile(models.Model):
    """User profile.  Contains some basic configurable settings"""
    user = models.ForeignKey(User, unique=True)

    collapsed_diffs = models.BooleanField(default=True)
    wordwrapped_diffs = models.BooleanField(default=True)

    starred_review_requests = models.ManyToManyField(ReviewRequest, core=False,
                                                     blank=True)
