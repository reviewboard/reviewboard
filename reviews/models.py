import os
import re
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, permalink
from djblets.util.misc import get_object_or_none

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.scmtools.models import Repository
from reviewboard.utils.fields import ModificationTimestampField
from utils.templatetags.htmlutils import crop_image, thumbnail


class InvalidChangeNumberError(Exception):
    def __init__(self):
        Exception.__init__(self, None)


class ChangeNumberInUseError(Exception):
    def __init__(self, review_request=None):
        Exception.__init__(self, None)
        self.review_request = review_request


class Group(models.Model):
    name = models.SlugField(maxlength=64)
    display_name = models.CharField(maxlength=64)
    mailing_list = models.EmailField(blank=True)
    users = models.ManyToManyField(User, core=False, blank=True,
                                   filter_interface=models.HORIZONTAL)

    def __unicode__(self):
        return self.name

    @permalink
    def get_absolute_url(self):
        return ('reviewboard.reviews.views.group', None, {'name': self.name})

    class Admin:
        list_display = ('name', 'display_name', 'mailing_list')

    class Meta:
        verbose_name = "review group"
        ordering = ['name']


class Screenshot(models.Model):
    caption = models.CharField(maxlength=256, blank=True)
    draft_caption = models.CharField(maxlength=256, blank=True)
    image = models.ImageField(upload_to=os.path.join('images', 'uploaded'))

    def thumb(self):
        url = thumbnail(self.image)
        return '<img src="%s" alt="%s" />' % (url, self.caption)
    thumb.allow_tags = True

    def __unicode__(self):
        return "%s (%s)" % (self.caption, self.image)

    @permalink
    def get_absolute_url(self):
        try:
            review = self.review_request.all()[0]
        except IndexError:
            review = self.inactive_review_request.all()[0]

        return ('reviewboard.reviews.views.view_screenshot', None, {
            'review_request_id': review.id,
            'screenshot_id': self.id
        })

    class Admin:
        list_display = ('thumb', 'caption', 'image')
        list_display_links = ('thumb', 'caption')


class ReviewRequestManager(models.Manager):
    """
    A manager for review requests. Provides specialized queries to retrieve
    review requests with specific targets or origins, and to create review
    requests based on certain data.
    """

    def create(self, user, repository, changenum=None):
        """
        Creates a new review request, optionally filling in fields based off
        a change number.
        """
        if changenum:
            try:
                review_request = self.get(changenum=changenum,
                                          repository=repository)
                raise ChangeNumberInUseError(review_request)
            except ReviewRequest.DoesNotExist:
                pass

        review_request = ReviewRequest(repository=repository)

        if changenum:
            review_request.update_from_changenum(changenum)

        diffset_history = DiffSetHistory()
        diffset_history.save()

        review_request.diffset_history = diffset_history
        review_request.submitter = user
        review_request.status = 'P'
        review_request.public = False
        review_request.save()

        return review_request

    def public(self, user=None, status='P'):
        return self._query(user, status)

    def to_group(self, group_name, user=None, status='P'):
        return self._query(user, status, Q(target_groups__name=group_name))

    def to_user_groups(self, username, user=None, status='P'):
        return self._query(user, status,
                           Q(target_groups__users__username=username))

    def to_user_directly(self, username, user=None, status='P'):
        return self._query(user, status, Q(target_people__username=username))

    def to_user(self, username, user=None, status='P'):
        # Using an OR query inside the extra_query field like this:
        # Q(target_people__username=username) |
        #     Q(target_groups__users__username=username))
        # does not work.  I haven't exactly figured out why.

        # This is disgusting, but it actually works =P
        # FIXME: it might be useful to cache this and invalidate the cache every
        #        time the status on a review request changes.
        results = []
        def add_if_unique(requests):
            for request in requests:
                found = False
                for result in results:
                    if request.id == result.id:
                        found = True
                if not found:
                    results.append(request)

        add_if_unique(self.to_user_groups(username, user, status))
        add_if_unique(self.to_user_directly(username, user, status))
        results.sort(lambda a, b: cmp(a.last_updated, b.last_updated),
                     reverse=True)
        return results

    def from_user(self, username, user=None, status='P'):
        return self._query(user, status, Q(submitter__username=username))

    def _query(self, user, status, extra_query=None):
        query = Q(public=True)

        if user and user.is_authenticated():
            query = query | Q(submitter=user)

        if status:
            query = query & Q(status=status)

        if extra_query:
            query = query & extra_query

        return self.filter(query).distinct()


class ReviewRequest(models.Model):
    STATUSES = (
        ('P', 'Pending Review'),
        ('S', 'Submitted'),
        ('D', 'Discarded'),
    )

    submitter = models.ForeignKey(User, verbose_name="Submitter")
    time_added = models.DateTimeField("Time Added", default=datetime.now)
    last_updated = ModificationTimestampField("Last Updated")
    status = models.CharField(maxlength=1, choices=STATUSES)
    public = models.BooleanField("Public", default=False)
    changenum = models.PositiveIntegerField("Change Number", blank=True,
                                            null=True, db_index=True)
    repository = models.ForeignKey(Repository)
    email_message_id = models.CharField("E-Mail Message ID", maxlength=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField("Time E-Mailed", null=True,
                                        default=None, blank=True)

    summary = models.CharField("Summary", maxlength=300, core=True)
    description = models.TextField("Description", blank=True)
    testing_done = models.TextField("Testing Done", blank=True)
    bugs_closed = models.CommaSeparatedIntegerField("Bugs",
                                                    maxlength=300, blank=True)
    diffset_history = models.ForeignKey(DiffSetHistory,
                                        verbose_name='diff set history',
                                        blank=True)
    branch = models.CharField("Branch", maxlength=300, blank=True)
    target_groups = models.ManyToManyField(Group, verbose_name="Target Groups",
                                           core=False, blank=True)
    target_people = models.ManyToManyField(User, verbose_name="Target People",
                                           related_name="directed_review_requests",
                                           core=False, blank=True)
    screenshots = models.ManyToManyField(Screenshot, verbose_name="Screenshots",
                                         related_name="review_request",
                                         core=False, blank=True)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        related_name="inactive_review_request", core=False, blank=True)


    # Set this up with the ReviewRequestManager
    objects = ReviewRequestManager()


    def get_bug_list(self):
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def get_new_reviews(self, user):
        """
        Returns any new reviews since the user last viewed the review request.
        """
        if user.is_authenticated():
            visit = get_object_or_none(self.visits, user=user)

            if visit:
                return self.review_set.filter(
                    public=True,
                    timestamp__gt=visit.timestamp).exclude(user=user)

        return self.review_set.get_empty_query_set()

    def update_from_changenum(self, changenum):
        changeset = self.repository.get_scmtool().get_changeset(changenum)

        if not changeset:
            raise InvalidChangeNumberError()

        self.changenum = changenum
        self.summary = changeset.summary
        self.description = changeset.description
        self.testing_done = changeset.testing_done
        self.branch = changeset.branch
        self.bugs_closed = ','.join(changeset.bugs_closed)

    @permalink
    def get_absolute_url(self):
        return ('reviewboard.reviews.views.review_detail', None, {
            'review_request_id': self.id,
        })

    def __unicode__(self):
        return self.summary

    def save(self):
        self.bugs_closed = self.bugs_closed.strip()

        if self.status != "P":
            # If this is not a pending review request now, delete any
            # and all ReviewRequestVisit objects.
            self.visits.all().delete()

        super(ReviewRequest, self).save()

    class Admin:
        list_display = ('summary', 'submitter', 'status', 'public', \
                        'last_updated')
        list_filter = ('public', 'status', 'time_added', 'last_updated')

    class Meta:
        ordering = ['-last_updated', 'submitter', 'summary']
        unique_together = (('changenum', 'repository'),)
        permissions = (
            ("can_change_status", "Can change status"),
        )


class ReviewRequestDraft(models.Model):
    review_request = models.ForeignKey(ReviewRequest,
                                       verbose_name="Review Request", core=True)
    last_updated = ModificationTimestampField("Last Updated")
    summary = models.CharField("Summary", maxlength=300, core=True)
    description = models.TextField("Description")
    testing_done = models.TextField("Testing Done")
    bugs_closed = models.CommaSeparatedIntegerField("Bugs",
                                                    maxlength=300, blank=True)
    diffset = models.ForeignKey(DiffSet, verbose_name='diff set', blank=True,
                                null=True, core=False)
    branch = models.CharField("Branch", maxlength=300, blank=True)
    target_groups = models.ManyToManyField(Group, verbose_name="Target Groups",
                                           core=False, blank=True)
    target_people = models.ManyToManyField(User, verbose_name="Target People",
                                           related_name="directed_drafts",
                                           core=False, blank=True)
    screenshots = models.ManyToManyField(Screenshot, verbose_name="Screenshots",
                                         core=False, blank=True)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        related_name="inactive_drafts", core=False, blank=True)

    def get_bug_list(self):
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def __unicode__(self):
        return self.summary

    def _submitter(self):
        return self.review_request.submitter

    def save(self):
        self.bugs_closed = self.bugs_closed.strip()
        super(ReviewRequestDraft, self).save()

    @staticmethod
    def create(review_request):
        draft, draft_is_new = \
            ReviewRequestDraft.objects.get_or_create(
                review_request=review_request,
                defaults={
                    'summary': review_request.summary,
                    'description': review_request.description,
                    'testing_done': review_request.testing_done,
                    'bugs_closed': review_request.bugs_closed,
                    'branch': review_request.branch,
                })

        if draft_is_new:
            map(draft.target_groups.add, review_request.target_groups.all())
            map(draft.target_people.add, review_request.target_people.all())
            for screenshot in review_request.screenshots.all():
                screenshot.draft_caption = screenshot.caption
                screenshot.save()
                draft.screenshots.add(screenshot)

            if review_request.diffset_history.diffset_set.count() > 0:
                draft.diffset = review_request.diffset_history.diffset_set.latest()

        return draft

    def save_draft(self):
        request = self.review_request

        request.summary = self.summary
        request.description = self.description
        request.testing_done = self.testing_done
        request.bugs_closed = self.bugs_closed
        request.branch = self.branch

        request.target_groups.clear()
        map(request.target_groups.add, self.target_groups.all())

        request.target_people.clear()
        map(request.target_people.add, self.target_people.all())

        screenshots = self.screenshots.all()
        for s in request.screenshots.all():
            if s in screenshots:
                s.caption = s.draft_caption
                s.save()
        request.screenshots.clear()
        map(request.screenshots.add, self.screenshots.all())

        request.inactive_screenshots.clear()
        map(request.inactive_screenshots.add, self.inactive_screenshots.all())

        if self.diffset:
            self.diffset.history = request.diffset_history
            self.diffset.save()

        request.save()

    class Admin:
        list_display = ('summary', '_submitter', 'last_updated')
        list_filter = ('last_updated',)

    class Meta:
        ordering = ['-last_updated']


class Comment(models.Model):
    filediff = models.ForeignKey(FileDiff, verbose_name='File')
    reply_to = models.ForeignKey("self", blank=True, null=True,
                                 related_name="replies")
    timestamp = models.DateTimeField('Timestamp', default=datetime.now)
    text = models.TextField("Comment Text")

    # A null line number applies to an entire diff.  Non-null line numbers are
    # the line within the entire file, starting at 1.
    first_line = models.PositiveIntegerField("First Line", blank=True,
                                             null=True)
    num_lines = models.PositiveIntegerField("Number of lines", blank=True,
                                            null=True)

    def last_line(self):
        return self.first_line + self.num_lines - 1

    def public_replies(self, user=None):
        if user:
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def __unicode__(self):
        return self.text

    class Admin:
        list_display = ('text', 'filediff', 'first_line', 'num_lines',
                        'timestamp')
        list_filter = ('timestamp',)

    class Meta:
        ordering = ['timestamp']


class ScreenshotComment(models.Model):
    screenshot = models.ForeignKey(Screenshot, verbose_name='Screenshot')
    reply_to = models.ForeignKey('self', blank=True, null=True,
                                 related_name='replies')
    timestamp = models.DateTimeField('Timestamp', default=datetime.now)
    text = models.TextField('Comment Text')

    # This is a sub-region of the screenshot.  Null X indicates the entire
    # image.
    x = models.PositiveSmallIntegerField("Sub-image X", null=True)
    y = models.PositiveSmallIntegerField("Sub-image Y")
    w = models.PositiveSmallIntegerField("Sub-image width")
    h = models.PositiveSmallIntegerField("Sub-image height")

    def public_replies(self, user=None):
        if user:
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def image(self):
        url = crop_image(self.screenshot.image, self.x, self.y, self.w, self.h)
        return '<img src="%s" width="%s" height="%s" alt="%s" />' % \
            (url, self.w, self.h, self.text)

    def __unicode__(self):
        return self.text

    class Admin:
        list_display = ('text', 'screenshot', 'timestamp')
        list_filter = ('timestamp',)

    class Meta:
        ordering = ['timestamp']


class Review(models.Model):
    review_request = models.ForeignKey(ReviewRequest)
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField('Timestamp', default=datetime.now)
    public = models.BooleanField("Public", default=False)
    ship_it = models.BooleanField("Ship It", default=False)
    base_reply_to = models.ForeignKey("self", blank=True, null=True,
                                      related_name="replies")
    email_message_id = models.CharField("E-Mail Message ID", maxlength=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField("Time E-Mailed", null=True,
                                        default=None, blank=True)

    body_top = models.TextField("Body (Top)", blank=True)
    body_bottom = models.TextField("Body (Bottom)", blank=True)

    body_top_reply_to = models.ForeignKey("self", blank=True, null=True,
                                          related_name="body_top_replies")
    body_bottom_reply_to = models.ForeignKey("self", blank=True, null=True,
                                             related_name="body_bottom_replies")

    comments = models.ManyToManyField(Comment, verbose_name="Comments",
                                      core=False, blank=True,
                                      filter_interface=models.VERTICAL)
    screenshot_comments = models.ManyToManyField(
        ScreenshotComment,
        verbose_name="Screenshot Comments",
        core=False, blank=True, filter_interface=models.VERTICAL)
    reviewed_diffset = models.ForeignKey(DiffSet, verbose_name="Reviewed Diff",
                                         blank=True, null=True)

    def __unicode__(self):
        return "Review of '%s'" % self.review_request

    def is_reply(self):
        return self.base_reply_to != None
    is_reply.boolean = True

    def public_replies(self):
        return self.replies.filter(public=True)

    def publish(self):
        self.timestamp = datetime.now()
        self.public = True
        self.save()

        for comment in self.comments.all():
            comment.timetamp = self.timestamp
            comment.save()

        for comment in self.screenshot_comments.all():
            comment.timetamp = self.timestamp
            comment.save()

    def delete(self):
        for comment in self.comments.all():
            comment.delete()

        for comment in self.screenshot_comments.all():
            comment.delete()

        super(Review, self).delete()

    def get_absolute_url(self):
        return "%s#review%s" % (self.review_request.get_absolute_url(),
                                self.id)

    class Admin:
        list_display = ('review_request', 'user', 'public', 'ship_it',
                        'is_reply', 'timestamp')
        list_filter = ('public', 'timestamp')

    class Meta:
        ordering = ['timestamp']
