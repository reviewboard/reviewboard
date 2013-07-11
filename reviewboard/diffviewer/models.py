import hashlib

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djblets.util.fields import Base64Field

from reviewboard.diffviewer.managers import FileDiffDataManager, DiffSetManager
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.scmtools.models import Repository


class FileDiffData(models.Model):
    """
    Contains hash and base64 pairs.

    These pairs are used to reduce diff database storage.
    """
    binary_hash = models.CharField(_("hash"), max_length=40, primary_key=True)
    binary = Base64Field(_("base64"))
    objects = FileDiffDataManager()


class FileDiff(models.Model):
    """
    A diff of a single file.

    This contains the patch and information needed to produce original and
    patched versions of a single file in a repository.
    """
    MODIFIED = 'M'
    MOVED = 'V'
    DELETED = 'D'

    STATUSES = (
        (MODIFIED, _('Modified')),
        (MOVED, _('Moved')),
        (DELETED, _('Deleted')),
    )

    diffset = models.ForeignKey('DiffSet',
                                related_name='files',
                                verbose_name=_("diff set"))

    source_file = models.CharField(_("source file"), max_length=1024)
    dest_file = models.CharField(_("destination file"), max_length=1024)
    source_revision = models.CharField(_("source file revision"),
                                       max_length=512)
    dest_detail = models.CharField(_("destination file details"),
                                   max_length=512)
    diff64 = Base64Field(_("diff"), db_column="diff_base64", blank=True)
    diff_hash = models.ForeignKey('FileDiffData', null=True)
    binary = models.BooleanField(_("binary file"), default=False)
    parent_diff64 = Base64Field(_("parent diff"),
                                db_column="parent_diff_base64", blank=True)
    parent_diff_hash = models.ForeignKey('FileDiffData', null=True,
                                         related_name='parent_filediff_set')
    status = models.CharField(_("status"), max_length=1, choices=STATUSES)

    @property
    def source_file_display(self):
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.source_file)

    @property
    def dest_file_display(self):
        tool = self.diffset.repository.get_scmtool()
        return tool.normalize_path_for_display(self.dest_file)

    @property
    def deleted(self):
        return self.status == self.DELETED

    @property
    def moved(self):
        return self.status == self.MOVED

    @property
    def is_new(self):
        return self.source_revision == PRE_CREATION

    def _get_diff(self):
        # If the diff is not in FileDiffData, it is in FileDiff.
        if not self.diff_hash:
            return self.diff64
        else:
            # Data exists in FileDiffData, retrieve it.
            return self.diff_hash.binary

    def _set_diff(self, diff):
        hashkey = self._hash_hexdigest(diff)

        # Add hash to table if it doesn't exist, and set diff_hash to this.
        self.diff_hash, is_new = FileDiffData.objects.get_or_create(
            binary_hash=hashkey, defaults={'binary': diff})
        self.diff64 = ""

    diff = property(_get_diff, _set_diff)

    def _get_parent_diff(self):
        if not self.parent_diff_hash:
            return self.parent_diff64
        else:
            return self.parent_diff_hash.binary

    def _set_parent_diff(self, parent_diff):
        if parent_diff != "":
            hashkey = self._hash_hexdigest(parent_diff)

            # Add hash to table if it doesn't exist, and set diff_hash to this.
            self.parent_diff_hash, is_new = FileDiffData.objects.get_or_create(
                binary_hash=hashkey, defaults={'binary': parent_diff})
            self.parent_diff64 = ""

    parent_diff = property(_get_parent_diff, _set_parent_diff)

    def _hash_hexdigest(self, diff):
        hasher = hashlib.sha1()
        hasher.update(diff)
        return hasher.hexdigest()

    def __unicode__(self):
        return u"%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                        self.dest_file, self.dest_detail)


class DiffSet(models.Model):
    """
    A revisioned collection of FileDiffs.
    """
    name = models.CharField(_('name'), max_length=256)
    revision = models.IntegerField(_("revision"))
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    basedir = models.CharField(_('base directory'), max_length=256,
                               blank=True, default='')
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

    base_commit_id = models.CharField(
        _('commit ID'), max_length=64, blank=True, null=True, db_index=True,
        help_text=_('The ID/revision this change is built upon.'))

    objects = DiffSetManager()

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

        if self.history:
            self.history.last_diff_updated = self.timestamp
            self.history.save()

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
    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now)
    last_diff_updated = models.DateTimeField(
        _("last updated"),
        blank=True,
        null=True,
        default=None)

    def __unicode__(self):
        return u'Diff Set History (%s revisions)' % self.diffsets.count()

    class Meta:
        verbose_name_plural = "Diff set histories"
