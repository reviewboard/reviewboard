import os

from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import ObjectDoesNotExist
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

    @property
    def filename(self):
        """Returns the filename for display purposes."""
        return os.path.basename(self.file.name)

    @property
    def icon_url(self):
        """Returns the icon URL for this file."""
        if self.mimetype in MIMETYPE_ICON_ALIASES:
            name = MIMETYPE_ICON_ALIASES[self.mimetype]
        else:
            category = self.mimetype.split('/')[0]
            name = self.mimetype.replace('/', '-')

            mimetypes_dir = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                         'mimetypes')

            if not os.path.exists(os.path.join(mimetypes_dir, name + '.png')):
                name = category + '-x-generic'

                if not os.path.exists(os.path.join(mimetypes_dir,
                                                   name + '.png')):
                    # We'll just use this as our fallback.
                    name = 'text-x-generic'

        return static('rb/images/mimetypes/%s.png' % name)

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
                except ObjectDoesNotExist:
                    draft = self.inactive_drafts.get()

                return draft.review_request

    def get_absolute_url(self):
        return self.file.url
