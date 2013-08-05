import os

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
    orig_filename = models.CharField(_('original filename'),
                                     max_length=256, blank=True, null=True)
    file = models.FileField(_("file"),
                            max_length=512,
                            upload_to=os.path.join('uploaded', 'files',
                                                   '%Y', '%m', '%d'))
    mimetype = models.CharField(_('mimetype'), max_length=256, blank=True)

    @property
    def mimetype_handler(self):
        return MimetypeHandler.for_type(self)

    @property
    def review_ui(self):
        if not hasattr(self, '_review_ui'):
            from reviewboard.reviews.ui.base import FileAttachmentReviewUI
            self._review_ui = FileAttachmentReviewUI.for_type(self)

        return self._review_ui

    def _get_thumbnail(self):
        """Returns the thumbnail for display."""
        return self.mimetype_handler.get_thumbnail()

    def _set_thumbnail(self, data):
        """Set the thumbnail."""
        self.mimetype_handler.set_thumbnail(data)

    thumbnail = property(_get_thumbnail, _set_thumbnail)

    @property
    def filename(self):
        """Returns the filename for display purposes."""
        # Older versions of Review Board didn't store the original filename,
        # instead just using the FileField's name. Newer versions have
        # a dedicated filename field.
        return self.orig_filename or os.path.basename(self.file.name)

    @property
    def display_name(self):
        """Returns a display name for the file."""
        if self.caption:
            return self.caption
        else:
            return self.filename

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

    def get_comments(self):
        """Returns all the comments made on this file attachment."""
        if not hasattr(self, '_comments'):
            self._comments = list(self.comments.all())

        return self._comments

    def get_absolute_url(self):
        return self.file.url
