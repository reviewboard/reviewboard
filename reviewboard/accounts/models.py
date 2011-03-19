from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from djblets.util.db import ConcurrencyManager
from djblets.util.fields import CounterField

from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.site.models import LocalSite


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

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    def __unicode__(self):
        return u"Review request visit"

    class Meta:
        unique_together = ("user", "review_request")


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
    starred_review_requests = models.ManyToManyField(ReviewRequest, blank=True,
                                                     related_name="starred_by")

    # A list of watched groups. This is so that users can monitor groups
    # without actually joining them, preventing e-mails being sent to the
    # user and review requests from entering the Incoming Reviews list.
    starred_groups = models.ManyToManyField(Group, blank=True,
                                            related_name="starred_by")

    def star_review_request(self, review_request):
        """Marks a review request as starred.

        This will mark a review request as starred for this user and
        immediately save to the database.
        """
        self.starred_review_requests.add(review_request)

        if (review_request.public and
            review_request.status == ReviewRequest.PENDING_REVIEW):
            q = self.starred_review_requests.filter(pk=review_request.pk)

            site_profile, is_new = LocalSiteProfile.objects.get_or_create(
                user=self.user,
                local_site=review_request.local_site,
                profile=self.user.get_profile())

            if is_new:
                site_profile.save()

            site_profile.increment_starred_public_request_count()

    def unstar_review_request(self, review_request):
        """Marks a review request as unstarred.

        This will mark a review request as starred for this user and
        immediately save to the database.
        """
        site_profile, is_new = LocalSiteProfile.objects.get_or_create(
            user=self.user,
            local_site=review_request.local_site,
            profile=self.user.get_profile())

        if is_new:
            site_profile.save()

        site_profile.decrement_starred_public_request_count()

        if (review_request.public and
            review_request.status == ReviewRequest.PENDING_REVIEW):
            q = self.starred_review_requests.filter(pk=review_request.pk)

            if q.count() > 0:
                self.starred_review_requests.remove(review_request)

    def star_review_group(self, review_group):
        """Marks a review group as starred.

        This will mark a review group as starred for this user and
        immediately save to the database.
        """
        if self.starred_groups.filter(pk=review_group.pk).count() == 0:
            self.starred_groups.add(review_group)

    def unstar_review_group(self, review_group):
        """Marks a review group as unstarred.

        This will mark a review group as starred for this user and
        immediately save to the database.
        """
        if self.starred_groups.filter(pk=review_group.pk).count() > 0:
            self.starred_groups.remove(review_group)

    def __unicode__(self):
        return self.user.username


class LocalSiteProfile(models.Model):
    """User profile information specific to a LocalSite."""
    user = models.ForeignKey(User, related_name='site_profiles')
    profile = models.ForeignKey(Profile, related_name='site_profiles')
    local_site = models.ForeignKey(LocalSite, null=True, blank=True,
                                   related_name='site_profiles')

    # Counts for quickly knowing how many review requests are incoming
    # (both directly and total), outgoing (pending and total ever made),
    # and starred (public).
    direct_incoming_request_count = CounterField(
        _('direct incoming review request count'),
        initializer=
            lambda p: ReviewRequest.objects.to_user_directly(
                p.user, local_site=p.local_site).count())
    total_incoming_request_count = CounterField(
        _('total incoming review request count'),
        initializer=
            lambda p: ReviewRequest.objects.to_user(
                p.user, local_site=p.local_site).count())
    pending_outgoing_request_count = CounterField(
        _('pending outgoing review request count'),
        initializer=
            lambda p: ReviewRequest.objects.from_user(
                p.user, p.user, local_site=p.local_site).count())
    total_outgoing_request_count = CounterField(
        _('total outgoing review request count'),
        initializer=
            lambda p: ReviewRequest.objects.from_user(
                p.user, p.user, None, local_site=p.local_site).count())
    starred_public_request_count = CounterField(
        _('starred public review request count'),
        initializer=lambda p: \
            p.pk and
            (p.profile.starred_review_requests.public(
                p.user, local_site=p.local_site).count() or 0))

    class Meta:
        unique_together = (('user', 'local_site'),
                           ('profile', 'local_site'))

    def __unicode__(self):
        return '%s (%s)' % (self.user.username, self.local_site)
