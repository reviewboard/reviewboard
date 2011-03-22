import os
import re
from datetime import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import connection, models, transaction
from django.db.models import F, Q, permalink
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.util.db import ConcurrencyManager
from djblets.util.decorators import root_url
from djblets.util.fields import CounterField, ModificationTimestampField
from djblets.util.misc import get_object_or_none
from djblets.util.templatetags.djblets_images import crop_image, thumbnail

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.signals import review_request_published, \
                                        reply_published, review_published
from reviewboard.reviews.errors import PermissionError
from reviewboard.scmtools.errors import EmptyChangeSetError, \
                                        InvalidChangeNumberError
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite

class UploadedFile(models.Model):
    """
    A file associated with a review request.

    Like diffs, a screenshot can have comments associated with it.
    These comments are of type :model:`reviews.FileComment`.
    """
    caption = models.CharField(_("caption"), max_length=256, blank=True)
    draft_caption = models.CharField(_("draft caption"),
                                     max_length=256, blank=True)
    upfile = models.FileField(_("file"),
                              upload_to=os.path.join('uploaded', 'files',
                                                     '%Y', '%m', '%d'))

    def get_path(self):
        """
        Returns the file path for downloading purposes.
        """
        return "%s" % (self.upfile.url)

    def get_title(self):
        """
        Returns the file title for display purposes
        """
        title = self.upfile.name
        title = title.split('/')[-1]
        return "%s" % (title)

    def __unicode__(self):
        return u"%s" % (self.caption)

    def get_absolute_url(self):
        try:
            review = self.review_request.all()[0]
        except IndexError:
            review = self.inactive_review_request.all()[0]

        return '%sf/%d/' % (review.get_absolute_url(), self.id)

