from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from reviewboard.reviews.models import Group, ReviewRequest


class ReviewRequestVisit(models.Model):
    """
    A recording of the last time a review request was visited by a user.

    Users have one ReviewRequestVisit entry in the database per review
    request they've visited. This is used to keep track of any updates
    to review requests they've already seen, so that we can intelligently
    inform them that new discussions have taken place.
    """
    user = models.ForeignKey(User, related_name="review_request_visits")
    review_request = models.ForeignKey(ReviewRequest, related_name="visits")
    timestamp = models.DateTimeField(_('last visited'), default=datetime.now)


class Profile(models.Model):
    """User profile.  Contains some basic configurable settings"""
    user = models.ForeignKey(User, unique=True)

    # This will redirect new users to the account settings page the first time
    # they log in (or immediately after creating an account).  This allows
    # people to fix their real name and join groups.
    first_time_setup_done = models.BooleanField(default=False,
        verbose_name=_("first time setup done"),
        help_text=_("Indicates whether the user has already gone through "
                    "the first time setup process by saving their user "
                    "preferences."))

    collapsed_diffs = models.BooleanField(default=True,
        verbose_name=_("collapsed diffs"),
        help_text=_("Indicates whether diffs should be shown in their "
                    "collapsed state by default."))
    wordwrapped_diffs = models.BooleanField(default=True,
        help_text=_("This field is unused and will be removed in a future "
                    "version."))
    syntax_highlighting = models.BooleanField(default=True,
        verbose_name=_("syntax highlighting"),
        help_text=_("Indicates whether the user wishes to see "
                    "syntax highlighting in the diffs."))

    # Indicate whether submitted review requests should appear in the
    # review request lists (excluding the dashboard).
    show_submitted = models.BooleanField(default=True)

    sort_review_request_columns = models.CharField(max_length=256, blank=True)
    sort_dashboard_columns = models.CharField(max_length=256, blank=True)
    sort_submitter_columns = models.CharField(max_length=256, blank=True)
    sort_group_columns = models.CharField(max_length=256, blank=True)

    review_request_columns = models.CharField(max_length=256, blank=True)
    dashboard_columns = models.CharField(max_length=256, blank=True)
    submitter_columns = models.CharField(max_length=256, blank=True)
    group_columns = models.CharField(max_length=256, blank=True)

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
