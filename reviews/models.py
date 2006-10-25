from django.conf import settings
from django.db import models

class Group(models.Model):
    name = models.CharField("Name", maxlength=30, core=True)

    def get_absolute_url(self):
        return "/groups/%s/" % self.name

    def __str__(self):
        return self.name

    class Admin:
        pass


class Person(models.Model):
    username = models.CharField("Username", maxlength=30, core=True)

    def get_absolute_url(self):
        return "/submitters/%s/" % self.username

    def __str__(self):
        return self.username

    class Admin:
        pass

    class Meta:
        verbose_name_plural = "People"


class ReviewRequest(models.Model):
    STATUSES = (
        ('P', 'Pending Review'),
        ('S', 'Submitted'),
        ('D', 'Discarded'),
    )

    submitter = models.ForeignKey(Person, verbose_name="Submitter")
    time_added = models.DateTimeField("Time Added", auto_now_add=True)
    last_updated = models.DateTimeField("Last Updated", auto_now=True)
    status = models.CharField(maxlength=1, choices=STATUSES)
    summary = models.CharField("Summary", maxlength=300, core=True)
    description = models.TextField("Description")
    testing_done = models.TextField("Testing Done")
    bugs_closed = models.CommaSeparatedIntegerField("Bugs Closed",
                                                    maxlength=300)
    htmldiff = models.URLField("HTML Diff URL", core=True,
                               verify_exists=False) # XXX
    branch = models.CharField("Branch", maxlength=30)

    target_groups = models.ManyToManyField(Group, verbose_name="Target Group",
                                           core=False, blank=True)
    target_people = models.ManyToManyField(Person, verbose_name="Target People",
                                           related_name="target_people",
                                           core=False, blank=True)

    def get_bug_list(self):
        bugs = self.bugs_closed.split(',')
        bugs.sort(cmp=lambda x,y: int(x) - int(y))
        return bugs

    def get_absolute_url(self):
        return "/reviews/%s/" % self.id

    def __str__(self):
        return self.summary

    class Admin:
        list_display = ('summary', 'submitter', 'status', 'last_updated')

    class Meta:
        ordering = ['status', 'last_updated', 'submitter', 'summary']
