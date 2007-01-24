from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from reviewboard.diffviewer.models import DiffSet
import re

class Comment(models.Model):
    filename = models.CharField("Filename", maxlength=256, core=True)


class ReviewRequest(models.Model):
    STATUSES = (
        ('P', 'Pending Review'),
        ('S', 'Submitted'),
        ('D', 'Discarded'),
    )

    submitter = models.ForeignKey(User, verbose_name="Submitter")
    time_added = models.DateTimeField("Time Added", auto_now_add=True)
    last_updated = models.DateTimeField("Last Updated", auto_now=True)
    status = models.CharField(maxlength=1, choices=STATUSES)
    public = models.BooleanField("Public", default=False)
    summary = models.CharField("Summary", maxlength=300, core=True)
    description = models.TextField("Description")
    testing_done = models.TextField("Testing Done")
    bugs_closed = models.CommaSeparatedIntegerField("Bugs Closed",
                                                    maxlength=300, blank=True)
    diffsets = models.ManyToManyField(DiffSet, verbose_name='Diff Sets',
                                      blank=True)
    branch = models.CharField("Branch", maxlength=30)
    target_groups = models.ManyToManyField(Group, verbose_name="Target Groups",
                                           core=False, blank=True)
    target_people = models.ManyToManyField(User, verbose_name="Target People",
                                           related_name="target_people",
                                           core=False, blank=True)

    def get_bug_list(self):
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def get_absolute_url(self):
        return "/reviews/%s/" % self.id

    def __str__(self):
        return self.summary

    class Admin:
        list_display = ('summary', 'submitter', 'status', 'public', \
                        'last_updated')

    class Meta:
        ordering = ['-last_updated', 'submitter', 'summary']


class Review(models.Model):
    review_request = models.ForeignKey(ReviewRequest)
    ship_it = models.BooleanField("Ship It", default=False)
    comments = models.ManyToManyField(Comment, verbose_name="Comments",
                                      core=False, blank=True)
    reviewed_diffset = models.ForeignKey(DiffSet, verbose_name="Reviewed Diff")


class ReviewRequestDraft(models.Model):
    review_request = models.ForeignKey(ReviewRequest,
                                       verbose_name="Review Request", core=True)
    last_updated = models.DateTimeField("Last Updated", auto_now=True)
    summary = models.CharField("Summary", maxlength=300, core=True)
    description = models.TextField("Description")
    testing_done = models.TextField("Testing Done")
    bugs_closed = models.CommaSeparatedIntegerField("Bugs Closed",
                                                    maxlength=300, blank=True)
    diffset = models.ForeignKey(DiffSet, verbose_name='DiffSet', blank=True,
                                null=True)
    branch = models.CharField("Branch", maxlength=30)
    target_groups = models.ManyToManyField(Group, verbose_name="Target Groups",
                                           core=False, blank=True)
    target_people = models.ManyToManyField(User, verbose_name="Target People",
                                           related_name="draft_target_people",
                                           core=False, blank=True)

    def get_bug_list(self):
        bugs = re.split(r"[, ]+", self.bugs_closed)
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def __str__(self):
        return self.summary

    def _submitter(self):
        return self.review_request.submitter

    class Admin:
        list_display = ('summary', '_submitter', 'last_updated')

    class Meta:
        ordering = ['-last_updated']
