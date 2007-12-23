import os
import re
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, permalink
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.util.misc import get_object_or_none
from djblets.util.db import ConcurrencyManager, QLeftOuterJoins

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.scmtools.models import Repository
from reviewboard.utils.fields import ModificationTimestampField
from reviewboard.utils.templatetags.htmlutils import crop_image, thumbnail


class InvalidChangeNumberError(Exception):
    def __init__(self):
        Exception.__init__(self, None)


class ChangeNumberInUseError(Exception):
    def __init__(self, review_request=None):
        Exception.__init__(self, None)
        self.review_request = review_request


class Group(models.Model):
    """
    A group of reviewers identified by a name. This is usually used to
    separate teams at a company or components of a project.

    Each group can have an e-mail address associated with it, sending
    all review requests and replies to that address.
    """
    name = models.SlugField(_("name"), max_length=64, blank=False, unique=True)
    display_name = models.CharField(_("display name"), max_length=64)
    mailing_list = models.EmailField(_("mailing list"), blank=True,
        help_text=_("The mailing list review requests and discussions "
                    "are sent to."))
    users = models.ManyToManyField(User, core=False, blank=True,
                                   filter_interface=models.HORIZONTAL,
                                   verbose_name=_("users"))

    def __unicode__(self):
        return self.name

    @permalink
    def get_absolute_url(self):
        return ('reviewboard.reviews.views.group', None, {'name': self.name})

    class Admin:
        list_display = ('name', 'display_name', 'mailing_list')

    class Meta:
        verbose_name = _("review group")
        ordering = ['name']


class DefaultReviewer(models.Model):
    """
    A default reviewer entry automatically adds default reviewers to a
    review request when the diff modifies a file matching the ``file_regex``
    pattern specified.

    This is useful when different groups own different parts of a codebase.
    Adding DefaultReviewer entries ensures that the right people will always
    see the review request and discussions.

    A ``file_regex`` of ``".*"`` will add the specified reviewers by
    default for every review request.
    """
    name = models.CharField(_("name"), max_length=64)
    file_regex = models.CharField(_("file regex"), max_length=256,
        help_text=_("File paths are matched against this regular expression "
                    "to determine if these reviewers should be added."))
    groups = models.ManyToManyField(Group, verbose_name=_("default groups"),
                                    core=False, blank=True)
    people = models.ManyToManyField(User, verbose_name=_("default people"),
                                    related_name="default_review_paths",
                                    core=False, blank=True)

    def __unicode__(self):
        return self.name

    class Admin:
        pass


class Screenshot(models.Model):
    """
    A screenshot associated with a review request.

    Like diffs, a screenshot can have comments associated with it.
    These comments are of type :model:`reviews.ScreenshotComment`.
    """
    caption = models.CharField(_("caption"), max_length=256, blank=True)
    draft_caption = models.CharField(_("draft caption"),
                                     max_length=256, blank=True)
    image = models.ImageField(_("image"),
                              upload_to=os.path.join('images', 'uploaded'))

    def thumb(self):
        """
        Creates a thumbnail of this screenshot and returns the HTML
        output embedding the thumbnail.
        """
        url = thumbnail(self.image)
        return mark_safe('<img src="%s" alt="%s" />' % (url, self.caption))
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


class ReviewRequestManager(ConcurrencyManager):
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
        query = QLeftOuterJoins(Q(target_people__username=username) |
                                Q(starred_by__user__username=username))
        return self._query(user, status, query)

    def to_user(self, username, user=None, status='P'):
        query = QLeftOuterJoins(Q(target_groups__users__username=username) |
                                Q(target_people__username=username) |
                                Q(starred_by__user__username=username))
        return self._query(user, status, query)

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
    """
    A review request.

    This is one of the primary models in Review Board. Most everything
    is associated with a review request.

    The ReviewRequest model contains detailed information on a review
    request. Some fields are user-modifiable, while some are used for
    internal state.
    """
    STATUSES = (
        ('P', 'Pending Review'),
        ('S', 'Submitted'),
        ('D', 'Discarded'),
    )

    submitter = models.ForeignKey(User, verbose_name=_("submitter"))
    time_added = models.DateTimeField(_("time added"), default=datetime.now)
    last_updated = ModificationTimestampField(_("last updated"))
    status = models.CharField(_("status"), max_length=1, choices=STATUSES)
    public = models.BooleanField(_("public"), default=False)
    changenum = models.PositiveIntegerField(_("change number"), blank=True,
                                            null=True, db_index=True,
                                            unique=True)
    repository = models.ForeignKey(Repository, verbose_name=_("repository"))
    email_message_id = models.CharField(_("e-mail message ID"), max_length=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField(_("time e-mailed"), null=True,
                                        default=None, blank=True)

    summary = models.CharField(_("summary"), max_length=300, core=True)
    description = models.TextField(_("description"), blank=True)
    testing_done = models.TextField(_("testing done"), blank=True)
    bugs_closed = models.CommaSeparatedIntegerField(_("bugs"),
                                                    max_length=300, blank=True)
    diffset_history = models.ForeignKey(DiffSetHistory,
                                        verbose_name=_('diff set history'),
                                        blank=True)
    branch = models.CharField(_("branch"), max_length=300, blank=True)
    target_groups = models.ManyToManyField(
        Group,
        verbose_name=_("target groups"),
        core=False, blank=True,
        filter_interface=models.HORIZONTAL)
    target_people = models.ManyToManyField(
        User,
        verbose_name=_("target people"),
        related_name="directed_review_requests",
        core=False, blank=True,
        filter_interface=models.HORIZONTAL)
    screenshots = models.ManyToManyField(
        Screenshot,
        verbose_name=_("screenshots"),
        related_name="review_request",
        core=False, blank=True,
        filter_interface=models.VERTICAL)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        verbose_name=_("inactive screenshots"),
        help_text=_("A list of screenshots that used to be but are no "
                    "longer associated with this review request."),
        related_name="inactive_review_request",
        core=False,
        blank=True,
        filter_interface=models.VERTICAL)


    # Set this up with the ReviewRequestManager
    objects = ReviewRequestManager()


    def get_bug_list(self):
        """
        Returns a sorted list of bugs associated with this review request.
        """
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def get_new_reviews(self, user):
        """
        Returns any new reviews since the user last viewed the review request.
        """
        if user.is_authenticated():
            query = self.visits.filter(user=user)

            if query.count() > 0:
                visit = query[0]

                return self.review_set.filter(
                    public=True,
                    timestamp__gt=visit.timestamp).exclude(user=user)

        return self.review_set.get_empty_query_set()

    def add_default_reviewers(self):
        """
        Add default reviewers to this review request based on the diffset.

        This method goes through the DefaultReviewer objects in the database and
        adds any missing reviewers based on regular expression comparisons with
        the set of files in the diff.
        """

        if self.diffset_history.diffset_set.count() != 1:
            return

        diffset = self.diffset_history.diffset_set.get()

        people = set()
        groups = set()

        # TODO: This is kind of inefficient, and could maybe be optimized in
        # some fancy way.  Certainly the most superficial optimization that
        # could be made would be to cache the compiled regexes somewhere.
        files = diffset.files.all()
        for default in DefaultReviewer.objects.all():
            regex = re.compile(default.file_regex)

            for filediff in files:
                if regex.match(filediff.source_file or filediff.dest_file):
                    for person in default.people.all():
                        people.add(person)
                    for group in default.groups.all():
                        groups.add(group)
                    break

        existing_people = self.target_people.all()
        for person in people:
            if person not in existing_people:
                self.target_people.add(person)

        existing_groups = self.target_groups.all()
        for group in groups:
            if group not in existing_groups:
                self.target_groups.add(group)

    def get_public_reviews(self):
        """
        Returns all public top-level reviews for this review request.
        """
        return self.review_set.filter(public=True, base_reply_to__isnull=True)

    def update_from_changenum(self, changenum):
        """
        Updates this review request from the specified changeset's contents
        on the server.
        """
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
    """
    A draft of a review request.

    When a review request is being modified, a special draft copy of it is
    created containing all the details of the review request. This copy can
    be modified and eventually saved or discarded. When saved, the new
    details are copied back over to the originating ReviewRequest.
    """
    review_request = models.ForeignKey(ReviewRequest,
                                       verbose_name=_("review request"),
                                       core=True, unique=True)
    last_updated = ModificationTimestampField(_("last updated"))
    summary = models.CharField(_("summary"), max_length=300, core=True)
    description = models.TextField(_("description"))
    testing_done = models.TextField(_("testing done"))
    bugs_closed = models.CommaSeparatedIntegerField(_("bugs"),
                                                    max_length=300, blank=True)
    diffset = models.ForeignKey(DiffSet, verbose_name=_('diff set'),
                                blank=True, null=True, core=False)
    branch = models.CharField(_("branch"), max_length=300, blank=True)
    target_groups = models.ManyToManyField(Group,
                                           verbose_name=_("target groups"),
                                           core=False, blank=True,
                                           filter_interface=models.HORIZONTAL)
    target_people = models.ManyToManyField(User,
                                           verbose_name=_("target people"),
                                           related_name="directed_drafts",
                                           core=False, blank=True,
                                           filter_interface=models.HORIZONTAL)
    screenshots = models.ManyToManyField(Screenshot,
                                         verbose_name=_("screenshots"),
                                         core=False, blank=True,
                                         filter_interface=models.VERTICAL)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        verbose_name=_("inactive screenshots"),
        related_name="inactive_drafts", core=False, blank=True,
        filter_interface=models.VERTICAL)

    submitter = property(lambda self: self.review_request.submitter)

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    def get_bug_list(self):
        """
        Returns a sorted list of bugs associated with this review request.
        """
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def __unicode__(self):
        return self.summary

    def save(self):
        self.bugs_closed = self.bugs_closed.strip()
        super(ReviewRequestDraft, self).save()

    @staticmethod
    def create(review_request):
        """
        Creates a draft based on a review request.

        This will copy over all the details of the review request that
        we care about. If a draft already exists for the review request,
        the draft will be returned.
        """
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

            for screenshot in review_request.inactive_screenshots.all():
                screenshot.draft_caption = screenshot.caption
                screenshot.save()
                draft.inactive_screenshots.add(screenshot)

            draft.save();

        return draft

    def add_default_reviewers(self):
        """
        Add default reviewers to this draft based on the diffset.

        This method goes through the DefaultReviewer objects in the database and
        adds any missing reviewers based on regular expression comparisons with
        the set of files in the diff.
        """

        if not self.diffset:
            return

        people = set()
        groups = set()

        # TODO: This is kind of inefficient, and could maybe be optimized in
        # some fancy way.  Certainly the most superficial optimization that
        # could be made would be to cache the compiled regexes somewhere.
        files = self.diffset.files.all()
        for default in DefaultReviewer.objects.all():
            regex = re.compile(default.file_regex)

            for filediff in files:
                if regex.match(filediff.source_file or filediff.dest_file):
                    for person in default.people.all():
                        people.add(person)
                    for group in default.groups.all():
                        groups.add(group)
                    break

        existing_people = self.target_people.all()
        for person in people:
            if person not in existing_people:
                self.target_people.add(person)

        existing_groups = self.target_groups.all()
        for group in groups:
            if group not in existing_groups:
                self.target_groups.add(group)

    def save_draft(self):
        """
        Save this draft into the assocated ReviewRequest object.

        This returns a dict of changed fields, which is used by the e-mail
        template to tell people what's new and interesting.

        The possible keys inside the changes dict are:
            'summary'
            'description'
            'testing_done'
            'bugs_closed'
            'branch'
            'target_groups'
            'target_people'
            'screenshots'
            'diff'
        Each of these keys will have an associated boolean value.
        """
        request = self.review_request

        changes = {}

        def update_field(a, b, name):
            # Apparently django models don't have __getattr__ or __setattr__, so
            # we have to update __dict__ directly.  Sigh.
            value = b.__dict__[name]
            if a.__dict__[name] != value:
                changes[name] = True
                a.__dict__[name] = value
            else:
                changes[name] = False

        def update_list(a, b, name):
            aset = set([x.id for x in a.all()])
            bset = set([x.id for x in b.all()])
            changes[name] = bool(aset.symmetric_difference(bset))

            a.clear()
            map(a.add, b.all())

        update_field(request, self, 'summary')
        update_field(request, self, 'description')
        update_field(request, self, 'testing_done')
        update_field(request, self, 'bugs_closed')
        update_field(request, self, 'branch')

        update_list(request.target_groups, self.target_groups, 'target_groups')
        update_list(request.target_people, self.target_people, 'target_people')

        # Screenshots are a bit special.  The list of associated screenshots can
        # change, but so can captions within each screenshot.
        screenshots = self.screenshots.all()
        screenshots_changed = False
        for s in request.screenshots.all():
            if s in screenshots and s.caption != s.draft_caption:
                screenshots_changed = True
                s.caption = s.draft_caption
                s.save()
        update_list(request.screenshots, self.screenshots, 'screenshots')

        # If a caption changed, screenshots will always be changed regardless of
        # whether the list of associated screenshots changed.
        if screenshots_changed:
            changes['screenshots'] = True

        # There's no change notification required for this field.
        request.inactive_screenshots.clear()
        map(request.inactive_screenshots.add, self.inactive_screenshots.all())

        if self.diffset:
            changes['diff'] = True
            self.diffset.history = request.diffset_history
            self.diffset.save()
        else:
            changes['diff'] = False

        request.save()

        return changes

    class Admin:
        list_display = ('summary', 'submitter', 'last_updated')
        list_filter = ('last_updated',)

    class Meta:
        ordering = ['-last_updated']


class Comment(models.Model):
    """
    A comment made on a diff.

    A comment can belong to a single filediff or to an interdiff between
    two filediffs. It can also have multiple replies.
    """
    filediff = models.ForeignKey(FileDiff, verbose_name=_('file diff'))
    interfilediff = models.ForeignKey(FileDiff,
                                      verbose_name=_('interdiff file'),
                                      blank=True, null=True,
                                      related_name="interdiff_comments")
    reply_to = models.ForeignKey("self", blank=True, null=True,
                                 related_name="replies",
                                 verbose_name=_("reply to"))
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)
    text = models.TextField(_("comment text"))

    # A null line number applies to an entire diff.  Non-null line numbers are
    # the line within the entire file, starting at 1.
    first_line = models.PositiveIntegerField(_("first line"), blank=True,
                                             null=True)
    num_lines = models.PositiveIntegerField(_("number of lines"), blank=True,
                                            null=True)

    last_line = property(lambda self: self.first_line + self.num_lines - 1)

    def public_replies(self, user=None):
        """
        Returns a list of public replies to this comment, optionally
        specifying the user replying.
        """
        if user:
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def get_absolute_url(self):
        revision_path = str(self.filediff.diffset.revision)
        if self.interfilediff:
            revision_path += "-%s" % self.interfilediff.diffset.revision

        return "%sdiff/%s/#file%sline%s" % \
            (self.review_set.get().review_request.get_absolute_url(),
             revision_path, self.filediff.id, self.first_line)


    def __unicode__(self):
        return self.text

    class Admin:
        list_display = ('text', 'filediff', 'first_line', 'num_lines',
                        'timestamp')
        list_filter = ('timestamp',)

    class Meta:
        ordering = ['timestamp']


class ScreenshotComment(models.Model):
    """
    A comment on a screenshot.
    """
    screenshot = models.ForeignKey(Screenshot, verbose_name=_('screenshot'))
    reply_to = models.ForeignKey('self', blank=True, null=True,
                                 related_name='replies',
                                 verbose_name=_("reply to"))
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)
    text = models.TextField(_('comment text'))

    # This is a sub-region of the screenshot.  Null X indicates the entire
    # image.
    x = models.PositiveSmallIntegerField(_("sub-image X"), null=True)
    y = models.PositiveSmallIntegerField(_("sub-image Y"))
    w = models.PositiveSmallIntegerField(_("sub-image width"))
    h = models.PositiveSmallIntegerField(_("sub-image height"))

    def public_replies(self, user=None):
        """
        Returns a list of public replies to this comment, optionally
        specifying the user replying.
        """
        if user:
            return self.replies.filter(Q(review__public=True) |
                                       Q(review__user=user))
        else:
            return self.replies.filter(review__public=True)

    def image(self):
        """
        Generates the cropped part of the screenshot referenced by this
        comment and returns the HTML markup embedding it.
        """
        url = crop_image(self.screenshot.image, self.x, self.y, self.w, self.h)
        return '<img src="%s" width="%s" height="%s" alt="%s" />' % \
            (url, self.w, self.h, escape(self.text))

    def __unicode__(self):
        return self.text

    class Admin:
        list_display = ('text', 'screenshot', 'timestamp')
        list_filter = ('timestamp',)

    class Meta:
        ordering = ['timestamp']


class Review(models.Model):
    """
    A review of a review request.
    """
    review_request = models.ForeignKey(ReviewRequest,
                                       verbose_name=_("review request"))
    user = models.ForeignKey(User, verbose_name=_("user"))
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)
    public = models.BooleanField(_("public"), default=False)
    ship_it = models.BooleanField(_("ship it"), default=False,
        help_text=_("Indicates whether the reviewer thinks this code is "
                    "ready to ship."))
    base_reply_to = models.ForeignKey(
        "self", blank=True, null=True,
        related_name="replies",
        verbose_name=_("Base reply to"),
        help_text=_("The top-most review in the discussion thread for "
                    "this review reply."))
    email_message_id = models.CharField(_("e-mail message ID"), max_length=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField(_("time e-mailed"), null=True,
                                        default=None, blank=True)

    body_top = models.TextField(_("body (top)"), blank=True,
        help_text=_("The review text shown above the diff and screenshot "
                    "comments."))
    body_bottom = models.TextField(_("body (bottom)"), blank=True,
        help_text=_("The review text shown below the diff and screenshot "
                    "comments."))

    body_top_reply_to = models.ForeignKey(
        "self", blank=True, null=True,
        related_name="body_top_replies",
        verbose_name=_("body (top) reply to"),
        help_text=_("The review that the body (top) field is in reply to."))
    body_bottom_reply_to = models.ForeignKey(
        "self", blank=True, null=True,
        related_name="body_bottom_replies",
        verbose_name=_("body (bottom) reply to"),
        help_text=_("The review that the body (bottom) field is in reply to."))

    comments = models.ManyToManyField(Comment, verbose_name=_("comments"),
                                      core=False, blank=True,
                                      filter_interface=models.VERTICAL)
    screenshot_comments = models.ManyToManyField(
        ScreenshotComment,
        verbose_name=_("screenshot comments"),
        core=False, blank=True, filter_interface=models.VERTICAL)

    # XXX Deprecated. This will be removed in a future release.
    reviewed_diffset = models.ForeignKey(
        DiffSet, verbose_name="Reviewed Diff",
        blank=True, null=True,
        help_text=_("This field is unused and will be removed in a future "
                    "version."))

    def __unicode__(self):
        return "Review of '%s'" % self.review_request

    def is_reply(self):
        """
        Returns whether or not this review is a reply to another review.
        """
        return self.base_reply_to != None
    is_reply.boolean = True

    def public_replies(self):
        """
        Returns a list of public replies to this review.
        """
        return self.replies.filter(public=True)

    def publish(self):
        """
        Publishes this review.

        This will make the review public and update the timestamps of all
        contained comments.
        """
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
        """
        Deletes this review.

        This will enforce that all contained comments are also deleted.
        """
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
