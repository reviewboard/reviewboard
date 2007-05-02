import base64

from django.db import models
from django.contrib.auth.models import User
from reviewboard.scmtools import PRE_CREATION, HEAD

class FileDiff(models.Model):
    diffset = models.ForeignKey('DiffSet', edit_inline=models.STACKED,
                                related_name='files')

    source_file = models.CharField("Source File", maxlength=256, core=True)
    dest_file = models.CharField("Destination File", maxlength=256, core=True)
    source_revision = models.CharField("Source File Revision", maxlength=512)
    dest_detail = models.CharField("Destination File Details", maxlength=512)
    diff_base64 = models.TextField("Diff (Base64)")

    def _set_diff(self, data):
        self.diff_base64 = base64.encodestring(data)

    def _get_diff(self):
        return base64.decodestring(self.diff_base64)

    diff = property(fget=lambda self: self._get_diff(),
                    fset=lambda self, v: self._set_diff(v))

    def __str__(self):
        return "%s (%s) -> %s (%s)" % (self.source_file, self.source_revision,
                                       self.dest_file, self.dest_detail)

    class Admin:
        list_display = ('source_file', 'source_revision',
                        'dest_file', 'dest_detail')
        fields = (
            (None, {
                'fields': ('diffset', ('source_file', 'source_revision'),
                           ('dest_file', 'dest_detail'),
                           'diff_base64')
            }),
        )


class DiffSet(models.Model):
    name = models.CharField('Name', maxlength=256, core=True)
    revision = models.IntegerField("Revision", core=True)
    timestamp = models.DateTimeField("Timestamp", auto_now_add=True)
    history = models.ForeignKey('DiffSetHistory', null=True, core=True,
                                edit_inline=models.STACKED)

    def save(self):
        if self.revision == 0 and self.history != None:
            if self.history.diffset_set.count() == 0:
                self.revision = 0
            else:
                self.revision = self.history.diffset_set.latest().revision + 1

        super(DiffSet, self).save()

    def __str__(self):
        return "%s r%s" % (self.name, self.revision)

    class Admin:
        list_display = ('__str__', 'revision', 'timestamp')

    class Meta:
        get_latest_by = 'timestamp'


class DiffSetHistory(models.Model):
    name = models.CharField('Name', maxlength=256)
    timestamp = models.DateTimeField("Timestamp", auto_now_add=True)

    def __str__(self):
        return 'Diff Set History (%s revisions)' % (self.diffset_set.count())

    class Admin:
        pass
