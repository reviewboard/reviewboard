import os

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.mimetypes import MimetypeHandler


class FileAttachment(models.Model):
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

    @property
    def mimetype_handler(self):
        return MimetypeHandler.for_type(self)

    @property
    def thumbnail(self):
        """Returns the thumbnail for display."""
        return self.mimetype_handler.get_thumbnail()

    @property
    def filename(self):
        """Returns the filename for display purposes."""
        return os.path.basename(self.file.name)

    @property
    def icon_url(self):
        """Returns the icon URL for this file."""
        return self.mimetype_handler.get_icon_url()

    def __unicode__(self):
        return self.caption

    def get_review_request(self):
        if hasattr(self, '_review_request'):
            return self._review_request

        try:
            return self.review_request.all()[0]
        except IndexError:
            try:
                return self.inactive_review_request.all()[0]
            except IndexError:
                # Maybe it's on a draft.
                try:
                    draft = self.drafts.get()
                except ObjectDoesNotExist:
                    draft = self.inactive_drafts.get()

                return draft.review_request

    def get_absolute_url(self):
        return self.file.url
