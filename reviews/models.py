import os
import re
from datetime import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import connection, models
from django.db.models import Q, permalink
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.siteconfig.models import SiteConfiguration
from djblets.util.db import ConcurrencyManager
from djblets.util.fields import ModificationTimestampField
from djblets.util.misc import get_object_or_none
from djblets.util.templatetags.djblets_images import crop_image, thumbnail

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.email import mail_review_request
from reviewboard.reviews.errors import PermissionError
from reviewboard.reviews.managers import ReviewRequestManager, ReviewManager
from reviewboard.scmtools.errors import InvalidChangeNumberError
from reviewboard.scmtools.models import Repository

#the model for the summery only allows it to be 300 chars in length
MAX_SUMMARY_LENGTH = 300


def update_obj_with_changenum(obj, repository, changenum):
    """
    Utility helper to update a review request or draft from the
    specified changeset's contents on the server.
    """
    changeset = repository.get_scmtool().get_changeset(changenum)

    if not changeset:
        raise InvalidChangeNumberError()

    obj.changenum = changenum
    obj.summary = changeset.summary
    obj.description = changeset.description
    obj.testing_done = changeset.testing_done
    obj.branch = changeset.branch
    obj.bugs_closed = ','.join(changeset.bugs_closed)

def truncate(string, num):
   if len(string) > num:
      string = string[0:num]
      i = string.rfind('.')

      if i != -1:
         string = string[0:i + 1]

   return string

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
    users = models.ManyToManyField(User, blank=True,
                                   related_name="review_groups",
                                   verbose_name=_("users"))

    def __unicode__(self):
        return self.name

    @permalink
    def get_absolute_url(self):
        return ('reviewboard.reviews.views.group', None, {'name': self.name})

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
                                    blank=True)
    people = models.ManyToManyField(User, verbose_name=_("default people"),
                                    related_name="default_review_paths",
                                    blank=True)

    def __unicode__(self):
        return self.name


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
                              upload_to=os.path.join('uploaded', 'images',
                                                     '%Y', '%m', '%d'))

    def thumb(self):
        """
        Creates a thumbnail of this screenshot and returns the HTML
        output embedding the thumbnail.
        """
        url = thumbnail(self.image)
        return mark_safe('<img src="%s" alt="%s" />' % (url, self.caption))
    thumb.allow_tags = True

    def __unicode__(self):
        return u"%s (%s)" % (self.caption, self.image)

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


class ReviewRequest(models.Model):
    """
    A review request.

    This is one of the primary models in Review Board. Most everything
    is associated with a review request.

    The ReviewRequest model contains detailed information on a review
    request. Some fields are user-modifiable, while some are used for
    internal state.
    """
    PENDING_REVIEW = "P"
    SUBMITTED      = "S"
    DISCARDED      = "D"

    STATUSES = (
        (PENDING_REVIEW, _('Pending Review')),
        (SUBMITTED,      _('Submitted')),
        (DISCARDED,      _('Discarded')),
    )

    submitter = models.ForeignKey(User, verbose_name=_("submitter"),
                                  related_name="review_requests")
    time_added = models.DateTimeField(_("time added"), default=datetime.now)
    last_updated = ModificationTimestampField(_("last updated"))
    status = models.CharField(_("status"), max_length=1, choices=STATUSES,
                              db_index=True)
    public = models.BooleanField(_("public"), default=False)
    changenum = models.PositiveIntegerField(_("change number"), blank=True,
                                            null=True, db_index=True)
    repository = models.ForeignKey(Repository,
                                   related_name="review_requests",
                                   verbose_name=_("repository"))
    email_message_id = models.CharField(_("e-mail message ID"), max_length=255,
                                        blank=True, null=True)
    time_emailed = models.DateTimeField(_("time e-mailed"), null=True,
                                        default=None, blank=True)

    summary = models.CharField(_("summary"), max_length=300)
    description = models.TextField(_("description"), blank=True)
    testing_done = models.TextField(_("testing done"), blank=True)
    bugs_closed = models.CommaSeparatedIntegerField(_("bugs"),
                                                    max_length=300, blank=True)
    diffset_history = models.ForeignKey(DiffSetHistory,
                                        related_name="review_request",
                                        verbose_name=_('diff set history'),
                                        blank=True)
    branch = models.CharField(_("branch"), max_length=300, blank=True)
    target_groups = models.ManyToManyField(
        Group,
        related_name="review_requests",
        verbose_name=_("target groups"),
        blank=True)
    target_people = models.ManyToManyField(
        User,
        verbose_name=_("target people"),
        related_name="directed_review_requests",
        blank=True)
    screenshots = models.ManyToManyField(
        Screenshot,
        related_name="review_request",
        verbose_name=_("screenshots"),
        blank=True)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        verbose_name=_("inactive screenshots"),
        help_text=_("A list of screenshots that used to be but are no "
                    "longer associated with this review request."),
        related_name="inactive_review_request",
        blank=True)

    changedescs = models.ManyToManyField(ChangeDescription,
        verbose_name=_("change descriptions"),
        related_name="review_request",
        blank=True)

    # Review-related information
    last_review_timestamp = models.DateTimeField(_("last review timestamp"),
                                                 null=True, default=None,
                                                 blank=True)
    shipit_count = models.IntegerField(_("ship-it count"), default=0,
                                       null=True)


    # Set this up with the ReviewRequestManager
    objects = ReviewRequestManager()


    def get_bug_list(self):
        """
        Returns a sorted list of bugs associated with this review request.
        """
        if self.bugs_closed == "":
            return []

        bugs = re.split(r"[, ]+", self.bugs_closed)

        # First try a numeric sort, to show the best results for the majority
        # case of bug trackers with numeric IDs.  If that fails, sort
        # alphabetically.
        try:
            bugs.sort(cmp=lambda x,y: int(x) - int(y))
        except ValueError:
            bugs.sort()

        return bugs

    def get_new_reviews(self, user):
        """
        Returns any new reviews since the user last viewed the review request.
        """
        if user.is_authenticated():
            # If this ReviewRequest was queried using with_counts=True,
            # then we should know the new review count and can use this to
            # decide whether we have anything at all to show.
            if hasattr(self, "new_review_count") and self.new_review_count > 0:
                query = self.visits.filter(user=user)

                try:
                    visit = query[0]

                    return self.reviews.filter(
                        public=True,
                        timestamp__gt=visit.timestamp).exclude(user=user)
                except IndexError:
                    # This visit doesn't exist, so bail.
                    pass


        return self.reviews.get_empty_query_set()

    def add_default_reviewers(self):
        """
        Add default reviewers to this review request based on the diffset.

        This method goes through the DefaultReviewer objects in the database and
        adds any missing reviewers based on regular expression comparisons with
        the set of files in the diff.
        """

        if self.diffset_history.diffsets.count() != 1:
            return

        diffset = self.diffset_history.diffsets.get()

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
        return self.reviews.filter(public=True, base_reply_to__isnull=True)

    def update_from_changenum(self, changenum):
        """
        Updates this review request from the specified changeset's contents
        on the server.
        """
        update_obj_with_changenum(self, self.repository, changenum)

    def is_accessible_by(self, user):
        "Returns true if the user can read this review request"
        return self.public or self.is_mutable_by(user)

    def is_mutable_by(self, user):
        "Returns true if the user can modify this review request"
        return self.submitter == user or \
               user.has_perm('reviews.can_edit_reviewrequest')

    def get_draft(self, user=None):
        """
        Returns the draft of the review request. If a user is specified,
        than the draft will be returned only if owned by the user. Otherwise,
        None will be returned.
        """
        if not user:
            return get_object_or_none(self.draft)
        elif user.is_authenticated():
            return get_object_or_none(self.draft,
                                      review_request__submitter=user)

        return None

    def get_pending_review(self, user):
        """
        Returns the pending review owned by the specified user, if any.
        This will return an actual review, not a reply to a review.
        """
        return Review.objects.get_pending_review(self, user)

    @permalink
    def get_absolute_url(self):
        return ('review-request-detail', None, {
            'review_request_id': self.id,
        })

    def __unicode__(self):
        return self.summary

    def save(self, **kwargs):
        self.bugs_closed = self.bugs_closed.strip()
        self.summary = truncate(self.summary, MAX_SUMMARY_LENGTH)

        if self.status != "P":
            # If this is not a pending review request now, delete any
            # and all ReviewRequestVisit objects.
            self.visits.all().delete()

        super(ReviewRequest, self).save()

    def can_publish(self):
        return not self.public or get_object_or_none(self.draft) is not None

    def close(self, type, user=None):
        """
        Closes the review request. The type must be one of
        SUBMITTED or DISCARDED.
        """
        if (user and not self.is_mutable_by(user) and
            not user.has_perm("reviews.can_change_status")):
            raise PermissionError

        if type not in [self.SUBMITTED, self.DISCARDED]:
            raise AttributeError("%s is not a valid close type" % type)

        self.status = type
        self.save()

        try:
            draft = self.draft.get()
        except ReviewRequestDraft.DoesNotExist:
            pass
        else:
            draft.delete()

    def reopen(self, user=None):
        """
        Reopens the review request for review.
        """
        if (user and not self.is_mutable_by(user) and
            not user.has_perm("reviews.can_change_status")):
            raise PermissionError

        if self.status != self.PENDING_REVIEW:
            if self.status == self.DISCARDED:
                self.public = False

            self.status = self.PENDING_REVIEW
            self.save()

    def publish(self, user):
        """
        Save the current draft attached to this review request. Send out the
        associated email. Returns the review request that was saved.
        """
        if not self.is_mutable_by(user):
            raise PermissionError

        draft = get_object_or_none(self.draft)
        if draft is not None:
            # This will in turn save the review request, so we'll be done.
            changes = draft.publish(self)
            draft.delete()
        else:
            changes = None

        self.public = True
        self.save()

        siteconfig = SiteConfiguration.objects.get_current()
        if siteconfig.get("mail_send_review_mail"):
            mail_review_request(user, self, changes)

    def increment_ship_it(self):
        """Atomicly increments the ship-it count on the review request."""

        # TODO: When we switch to Django 1.1, change this to:
        #
        #       ReviewRequest.objects.filter(pk=self.id).update(
        #           shipit_count=F('shipit_count') + 1)

        cursor = connection.cursor()
        cursor.execute("UPDATE reviews_reviewrequest"
                       "   SET shipit_count = shipit_count + 1"
                       " WHERE id = %s",
                       [self.id])

        # Update our copy.
        r = ReviewRequest.objects.get(pk=self.id)
        self.shipit_count = r.shipit_count

    class Meta:
        ordering = ['-last_updated', 'submitter', 'summary']
        unique_together = (('changenum', 'repository'),)
        permissions = (
            ("can_change_status", "Can change status"),
            ("can_submit_as_another_user", "Can submit as another user"),
            ("can_edit_reviewrequest", "Can edit review request"),
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
                                       related_name="draft",
                                       verbose_name=_("review request"),
                                       unique=True)
    last_updated = ModificationTimestampField(_("last updated"))
    summary = models.CharField(_("summary"), max_length=300)
    description = models.TextField(_("description"))
    testing_done = models.TextField(_("testing done"))
    bugs_closed = models.CommaSeparatedIntegerField(_("bugs"),
                                                    max_length=300, blank=True)
    diffset = models.ForeignKey(DiffSet, verbose_name=_('diff set'),
                                blank=True, null=True)
    changedesc = models.ForeignKey(ChangeDescription,
                                   verbose_name=_('change description'),
                                   blank=True, null=True)
    branch = models.CharField(_("branch"), max_length=300, blank=True)
    target_groups = models.ManyToManyField(Group,
                                           related_name="drafts",
                                           verbose_name=_("target groups"),
                                           blank=True)
    target_people = models.ManyToManyField(User,
                                           verbose_name=_("target people"),
                                           related_name="directed_drafts",
                                           blank=True)
    screenshots = models.ManyToManyField(Screenshot,
                                         related_name="drafts",
                                         verbose_name=_("screenshots"),
                                         blank=True)
    inactive_screenshots = models.ManyToManyField(Screenshot,
        verbose_name=_("inactive screenshots"),
        related_name="inactive_drafts",
        blank=True)

    submitter = property(lambda self: self.review_request.submitter)

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

    def get_bug_list(self):
        """
        Returns a sorted list of bugs associated with this review request.
        """
        if self.bugs_closed == "":
            return []

        bugs = re.split(r"[, ]+", self.bugs_closed)

        # First try a numeric sort, to show the best results for the majority
        # case of bug trackers with numeric IDs.  If that fails, sort
        # alphabetically.
        try:
            bugs.sort(cmp=lambda x,y: int(x) - int(y))
        except ValueError:
            bugs.sort()

        return bugs

    def __unicode__(self):
        return self.summary

    def save(self, **kwargs):
        self.bugs_closed = self.bugs_closed.strip()
        self.summary = truncate(self.summary, MAX_SUMMARY_LENGTH)
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

        if draft.changedesc is None and review_request.public:
            changedesc = ChangeDescription()
            changedesc.save()
            draft.changedesc = changedesc

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
            try:
                regex = re.compile(default.file_regex)
            except:
                continue

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

    def publish(self, review_request=None):
        """
        Publishes this draft. Uses the draft's assocated ReviewRequest
        object if one isn't passed in.

        This updates and returns the draft's ChangeDescription, which
        contains the changed fields. This is used by the e-mail template
        to tell people what's new and interesting.

        The keys that may be saved in 'fields_changed' in the
        ChangeDescription are:

           *  'summary'
           *  'description'
           *  'testing_done'
           *  'bugs_closed'
           *  'branch'
           *  'target_groups'
           *  'target_people'
           *  'screenshots'
           *  'screenshot_captions'
           *  'diff'

        Each field in 'fields_changed' represents a changed field. This will
        save fields in the standard formats as defined by the
        'ChangeDescription' documentation, with the exception of the
        'screenshot_captions' and 'diff' fields.

        For the 'screenshot_captions' field, the value will be a dictionary
        of screenshot ID/dict pairs with the following fields:

           * 'old': The old value of the field
           * 'new': The new value of the field

        For the 'diff' field, there is only ever an 'added' field, containing
        the ID of the new diffset.
        """
        if not review_request:
            review_request = self.review_request

        if not self.changedesc and review_request.public:
            self.changedesc = ChangeDescription()

        def update_field(a, b, name, record_changes=True):
            # Apparently django models don't have __getattr__ or __setattr__,
            # so we have to update __dict__ directly.  Sigh.
            value = b.__dict__[name]
            old_value = a.__dict__[name]

            if old_value != value:
                if record_changes and self.changedesc:
                    self.changedesc.record_field_change(name, old_value, value)

                a.__dict__[name] = value

        def update_list(a, b, name, record_changes=True, name_field=None):
            aset = set([x.id for x in a.all()])
            bset = set([x.id for x in b.all()])

            if aset.symmetric_difference(bset):
                if record_changes and self.changedesc:
                    self.changedesc.record_field_change(name, a.all(), b.all(),
                                                        name_field)

                a.clear()
                map(a.add, b.all())


        update_field(review_request, self, 'summary')
        update_field(review_request, self, 'description')
        update_field(review_request, self, 'testing_done')
        update_field(review_request, self, 'branch')

        update_list(review_request.target_groups, self.target_groups,
                    'target_groups', name_field="name")
        update_list(review_request.target_people, self.target_people,
                    'target_people', name_field="username")

        # Specifically handle bug numbers
        old_bugs = set(review_request.get_bug_list())
        new_bugs = set(self.get_bug_list())

        if old_bugs != new_bugs:
            update_field(review_request, self, 'bugs_closed',
                         record_changes=False)

            if self.changedesc:
                self.changedesc.record_field_change('bugs_closed',
                                                    old_bugs - new_bugs,
                                                    new_bugs - old_bugs)


        # Screenshots are a bit special.  The list of associated screenshots can
        # change, but so can captions within each screenshot.
        screenshots = self.screenshots.all()
        caption_changes = {}

        for s in review_request.screenshots.all():
            if s in screenshots and s.caption != s.draft_caption:
                caption_changes[s.id] = {
                    'old': (s.caption,),
                    'new': (s.draft_caption,),
                }

                s.caption = s.draft_caption
                s.save()

        if caption_changes and self.changedesc:
            self.changedesc.fields_changed['screenshot_captions'] = \
                caption_changes

        update_list(review_request.screenshots, self.screenshots,
                    'screenshots', name_field="caption")

        # There's no change notification required for this field.
        review_request.inactive_screenshots.clear()
        map(review_request.inactive_screenshots.add,
            self.inactive_screenshots.all())

        if self.diffset:
            if self.changedesc:
                self.changedesc.fields_changed['diff'] = {
                    'added': [(_("Diff r%s") % self.diffset.revision,
                               reverse("view_diff_revision",
                                       args=[review_request.id,
                                             self.diffset.revision]),
                               self.diffset.id)],
                }

            self.diffset.history = review_request.diffset_history
            self.diffset.save()

        if self.changedesc:
            self.changedesc.timestamp = datetime.now()
            self.changedesc.public = True
            self.changedesc.save()
            review_request.changedescs.add(self.changedesc)

        review_request.save()

        return self.changedesc

    def update_from_changenum(self, changenum):
        """
        Updates this draft from the specified changeset's contents on
        the server.
        """
        update_obj_with_changenum(self, self.review_request.repository,
                                  changenum)

    class Meta:
        ordering = ['-last_updated']


class Comment(models.Model):
    """
    A comment made on a diff.

    A comment can belong to a single filediff or to an interdiff between
    two filediffs. It can also have multiple replies.
    """
    filediff = models.ForeignKey(FileDiff, verbose_name=_('file diff'),
                                 related_name="comments")
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

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

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

        return "%sdiff/%s/?file=%s#file%sline%s" % \
             (self.review.get().review_request.get_absolute_url(),
              revision_path, self.filediff.id, self.filediff.id,
              self.first_line)

    def get_review_url(self):
        return "%s#comment%d" % \
            (self.review.get().review_request.get_absolute_url(), self.id)

    def save(self, **kwargs):
        super(Comment, self).save()

        try:
            # Update the review timestamp.
            review = self.review.get()
            review.timestamp = datetime.now()
            review.save()
        except Review.DoesNotExist:
            pass

    def __unicode__(self):
        return self.text

    def truncate_text(self):
        if len(self.text) > 60:
            return self.text[0:57] + "..."
        else:
            return self.text

    class Meta:
        ordering = ['timestamp']


class ScreenshotComment(models.Model):
    """
    A comment on a screenshot.
    """
    screenshot = models.ForeignKey(Screenshot, verbose_name=_('screenshot'),
                                   related_name="comments")
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

    # Set this up with a ConcurrencyManager to help prevent race conditions.
    objects = ConcurrencyManager()

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

    def get_review_url(self):
        return "%s#scomment%d" % \
            (self.review.get().review_request.get_absolute_url(), self.id)

    def save(self, **kwargs):
        super(ScreenshotComment, self).save()

        try:
            # Update the review timestamp.
            review = self.review.get()
            review.timestamp = datetime.now()
            review.save()
        except Review.DoesNotExist:
            pass

    def __unicode__(self):
        return self.text

    class Meta:
        ordering = ['timestamp']


class Review(models.Model):
    """
    A review of a review request.
    """
    review_request = models.ForeignKey(ReviewRequest,
                                       related_name="reviews",
                                       verbose_name=_("review request"))
    user = models.ForeignKey(User, verbose_name=_("user"),
                             related_name="reviews")
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
                                      related_name="review", blank=True)
    screenshot_comments = models.ManyToManyField(
        ScreenshotComment,
        verbose_name=_("screenshot comments"),
        related_name="review",
        blank=True)

    # XXX Deprecated. This will be removed in a future release.
    reviewed_diffset = models.ForeignKey(
        DiffSet, verbose_name="Reviewed Diff",
        blank=True, null=True,
        help_text=_("This field is unused and will be removed in a future "
                    "version."))

    # Set this up with a ReviewManager to help prevent race conditions and
    # to fix duplicate reviews.
    objects = ReviewManager()


    def __unicode__(self):
        return u"Review of '%s'" % self.review_request

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

    def get_pending_reply(self, user):
        """
        Returns the pending reply to this review owned by the specified
        user, if any.
        """
        if user.is_authenticated():
            return get_object_or_none(Review,
                                      user=user,
                                      public=False,
                                      base_reply_to=self)

        return None

    def save(self, **kwargs):
        self.timestamp = datetime.now()

        super(Review, self).save()

    def publish(self):
        """
        Publishes this review.

        This will make the review public and update the timestamps of all
        contained comments.
        """
        self.public = True
        self.save()

        for comment in self.comments.all():
            comment.timetamp = self.timestamp
            comment.save()

        for comment in self.screenshot_comments.all():
            comment.timetamp = self.timestamp
            comment.save()

        # Update the last_updated timestamp on the review request.
        self.review_request.last_review_timestamp = self.timestamp
        self.review_request.save()

        # Atomicly update the shipit_count
        if self.ship_it:
            self.review_request.increment_ship_it()

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

    class Meta:
        ordering = ['timestamp']
        get_latest_by = 'timestamp'
