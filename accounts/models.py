from django.db import models
from django.contrib.auth.models import User
from reviewboard.reviews.models import ReviewRequest


class Profile(models.Model):
    """User profile.  Contains some basic configurable settings"""
    user = models.ForeignKey(User, unique=True)

    # This will redirect new users to the account settings page the first time
    # they log in (or immediately after creating an account).  This allows
    # people to fix their real name and join groups.
    first_time_setup_done = models.BooleanField(default=False)

    collapsed_diffs = models.BooleanField(default=True)
    wordwrapped_diffs = models.BooleanField(default=True)
    syntax_highlighting = models.BooleanField(default=True)

    starred_review_requests = models.ManyToManyField(ReviewRequest, core=False,
                                                     blank=True)

    def __str__(self):
        return self.user.username

    class Admin:
        list_display = ('__str__', 'first_time_setup_done')
