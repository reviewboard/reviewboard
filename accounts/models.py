from datetime import datetime

from django.db import models
from django.contrib.auth.models import User

from reviewboard.reviews.models import Group, ReviewRequest


class ReviewRequestVisit(models.Model):
    """A review request visit."""
    user = models.ForeignKey(User, related_name="review_request_visits")
    review_request = models.ForeignKey(ReviewRequest, related_name="visits")
    timestamp = models.DateTimeField("Last Visited", default=datetime.now)


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

    # Indicate whether submitted review requests should appear in the
    # review request lists (excluding the dashboard).
    show_submitted = models.BooleanField(default=True)

    sort_review_request_columns = models.CharField(maxlength=128, blank=True)
    sort_submitter_columns = models.CharField(maxlength=128, blank=True)
    sort_group_columns = models.CharField(maxlength=128, blank=True)

    #review_request_columns = models.CharField(maxlength=128, blank=True)
    #submitter_columns = models.CharField(maxlength=128, blank=True)
    #group_columns = models.CharField(maxlength=128, blank=True)

    # A list of starred review requests. This allows users to monitor a
    # review request and receive e-mails on updates without actually being
    # on the reviewer list or commenting on the review. This is similar to
    # adding yourself to a CC list.
    starred_review_requests = models.ManyToManyField(
        ReviewRequest, core=False, blank=True,
        filter_interface=models.HORIZONTAL,
        related_name="starred_by")

    # A list of watched groups. This is so that users can monitor groups
    # without actually joining them, preventing e-mails being sent to the
    # user and review requests from entering the Incoming Reviews list.
    starred_groups = models.ManyToManyField(
        Group, core=False, blank=True, filter_interface=models.HORIZONTAL,
        related_name="starred_by")

    def __unicode__(self):
        return self.user.username

    class Admin:
        list_display = ('__unicode__', 'first_time_setup_done')
