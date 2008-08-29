from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.util.fields import Base64Field

from reviewboard.scmtools.models import Repository


class FileDiff(models.Model):
    """
    A diff of a single file.

    This contains the patch and information needed to produce original and
    patched versions of a single file in a repository.
    """
    diffset = models.ForeignKey('DiffSet',
                                related_name='files',
                                verbose_name=_("diff set"))

    source_file = models.CharField(_("source file"), max_length=256)
    dest_file = models.CharField(_("destination file"), max_length=256)
    source_revision = models.CharField(_("source file revision"), max_length=512)
    dest_detail = models.CharField(_("destination file details"), max_length=512)
    diff = Base64Field(_("diff"), db_column="diff_base64")
    binary = models.BooleanField(_("binary file"), default=False)
    parent_diff = Base64Field(_("parent diff"), db_column="parent_diff_base64",
                              blank=True)

    def __unicode__(self):
        return u"%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                        self.dest_file, self.dest_detail)


class DiffSet(models.Model):
    """
    A revisioned collection of FileDiffs.
    """
    name = models.CharField(_('name'), max_length=256)
    revision = models.IntegerField(_("revision"))
    timestamp = models.DateTimeField(_("timestamp"), default=datetime.now)
    history = models.ForeignKey('DiffSetHistory', null=True,
                                related_name="diffsets",
                                verbose_name=_("diff set history"))
    repository = models.ForeignKey(Repository, related_name="diffsets",
                                   verbose_name=_("repository"))
    diffcompat = models.IntegerField(
        _('differ compatibility version'),
        default=0,
        help_text=_("The diff generator compatibility version to use. "
                    "This can and should be ignored."))

    def save(self, **kwargs):
        """
        Saves this diffset.

        This will set an initial revision of 1 if this is the first diffset
        in the history, and will set it to on more than the most recent
        diffset otherwise.
        """
        if self.revision == 0 and self.history != None:
            if self.history.diffsets.count() == 0:
                # Start on revision 1. It's more human-grokable.
                self.revision = 1
            else:
                self.revision = self.history.diffsets.latest().revision + 1

        super(DiffSet, self).save()

    def __unicode__(self):
        return u"[%s] %s r%s" % (self.id, self.name, self.revision)

    class Meta:
        get_latest_by = 'revision'
        ordering = ['revision', 'timestamp']


class DiffSetHistory(models.Model):
    """
    A collection of diffsets.

    This gives us a way to store and keep track of multiple revisions of
    diffsets belonging to an object.
    """
    name = models.CharField(_('name'), max_length=256)
    timestamp = models.DateTimeField(_("timestamp"), default=datetime.now)

    def __unicode__(self):
        return u'Diff Set History (%s revisions)' % self.diffsets.count()

    class Meta:
        verbose_name_plural = "Diff set histories"
