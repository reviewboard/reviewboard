from django.db import models

class FileDiff(models.Model):
    filename = models.CharField("Filename", maxlength=256, core=True)
    source_path = models.CharField("Source Path", maxlength=256, core=True)
    diff = models.TextField("Diff")

    def __str__(self):
        return self.source_path

    class Admin:
        list_display = ('source_path', 'filename')


class DiffSet(models.Model):
    revision = models.IntegerField("Revision", core=True)
    timestamp = models.DateTimeField("Timestamp", auto_now_add=True)
    files = models.ManyToManyField(FileDiff, verbose_name="Files", core=True)

    def __str__(self):
        return 'Diff Set'

    class Admin:
        list_display = ('__str__', 'revision',)

    class Meta:
        get_latest_by = 'timestamp'
