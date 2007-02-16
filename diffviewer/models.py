from django.db import models
from django.contrib.auth.models import User

class FileDiff(models.Model):
    diffset = models.ForeignKey('DiffSet', edit_inline=models.STACKED,
                                related_name='files')

    source_file = models.CharField("Source File", maxlength=256, core=True)
    dest_file = models.CharField("Destination File", maxlength=256, core=True)
    source_detail = models.CharField("Source File Details", maxlength=512)
    dest_detail = models.CharField("Destination File Details", maxlength=512)
    diff = models.TextField("Diff")

    def __str__(self):
        return "%s %s -> %s %s" % (self.source_file, self.source_detail,
                                  self.dest_file, self.dest_detail)

    class Admin:
        list_display = ('source_file', 'source_detail',
                        'dest_file', 'dest_detail')


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
