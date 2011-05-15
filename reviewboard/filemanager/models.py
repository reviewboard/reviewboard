import os

from django.db import models
from django.utils.translation import ugettext_lazy as _


class UploadedFile(models.Model):
    """A file associated with a review request.

    Like diffs, a file can have comments associated with it.
    These comments are of type :model:`reviews.FileComment`.
    """
    caption = models.CharField(_("caption"), max_length=256, blank=True)
    draft_caption = models.CharField(_("draft caption"),
                                     max_length=256, blank=True)
    file = models.FileField(_("file"),
                              upload_to=os.path.join('uploaded', 'files',
                                                     '%Y', '%m', '%d'))
    mimetype = models.CharField(_('mimetype'), max_length=256, blank=True)

    def get_path(self):
        """Returns the file path for downloading purposes."""
        return self.file.url

    def get_title(self):
        """Returns the file title for display purposes"""
        return os.path.basename(self.file.name)

    def __unicode__(self):
        return self.caption

    def get_absolute_url(self):
        return self.file.url
