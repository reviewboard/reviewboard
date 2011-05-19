import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.mimetypes import MIMETYPE_ICON_ALIASES


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

    def get_path(self):
        """Returns the file path for downloading purposes."""
        return self.file.url

    def get_title(self):
        """Returns the file title for display purposes"""
        return os.path.basename(self.file.name)

    def get_icon_url(self):
        """Returns the icon URL for this file."""
        if self.mimetype in MIMETYPE_ICON_ALIASES:
            name = MIMETYPE_ICON_ALIASES[self.mimetype]
        else:
            category = self.mimetype.split('/')[0]
            name = self.mimetype.replace('/', '-')

            mimetypes_dir = os.path.join(settings.MEDIA_ROOT, 'rb', 'images',
                                         'mimetypes')

            if not os.path.exists(os.path.join(mimetypes_dir, name + '.png')):
                name = category + '-x-generic'

                if not os.path.exists(os.path.join(mimetypes_dir,
                                                   name + '.png')):
                    # We'll just use this as our fallback.
                    name = 'text-x-generic'

        return '%srb/images/mimetypes/%s.png?%s' % \
            (settings.MEDIA_URL, name, settings.MEDIA_SERIAL)

    def __unicode__(self):
        return self.caption

    def get_review_request(self):
        try:
            return self.review_request.all()[0]
        except IndexError:
            try:
                return self.inactive_review_request.all()[0]
            except IndexError:
                # Maybe it's on a draft.
                try:
                    draft = self.drafts.get()
                except ReviewRequestDraft.DoesNotExist:
                    draft = self.inactive_drafts.get()

                return draft.review_request

    def get_absolute_url(self):
        return self.file.url
