from __future__ import unicode_literals

import logging
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.managers import FileAttachmentManager
from reviewboard.attachments.mimetypes import MimetypeHandler
from reviewboard.diffviewer.models import FileDiff
from reviewboard.scmtools.models import Repository


@python_2_unicode_compatible
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

    # repo_path, repo_revision, and repository are used to identify
    # FileAttachments associated with committed binary files in a source tree.
    # They are not used for new files that don't yet have a revision.
    #
    # For new files, the added_in_filediff association is used.
    repo_path = models.CharField(_('repository file path'),
                                 max_length=1024,
                                 blank=True,
                                 null=True)
    repo_revision = models.CharField(_('repository file revision'),
                                     max_length=64,
                                     blank=True,
                                     null=True,
                                     db_index=True)
    repository = models.ForeignKey(Repository,
                                   blank=True,
                                   null=True,
                                   related_name='file_attachments')
    added_in_filediff = models.ForeignKey(FileDiff,
                                          blank=True,
                                          null=True,
                                          related_name='added_attachments')

    objects = FileAttachmentManager()

    @property
    def mimetype_handler(self):
        if not hasattr(self, '_thumbnail'):
            self._thumbnail = MimetypeHandler.for_type(self)

        return self._thumbnail

    @property
    def review_ui(self):
        if not hasattr(self, '_review_ui'):
            from reviewboard.reviews.ui.base import FileAttachmentReviewUI
            self._review_ui = FileAttachmentReviewUI.for_type(self)

        return self._review_ui

    def _get_thumbnail(self):
        """Returns the thumbnail for display."""
        try:
            return self.mimetype_handler.get_thumbnail()
        except Exception as e:
            logging.error('Error when calling get_thumbnail for '
                          'MimetypeHandler %r: %s',
                          self.mimetype_handler, e, exc_info=1)
            return None

    def _set_thumbnail(self, data):
        """Set the thumbnail."""
        try:
            self.mimetype_handler.set_thumbnail(data)
        except Exception as e:
            logging.error('Error when calling get_thumbnail for '
                          'MimetypeHandler %r: %s',
                          self.mimetype_handler, e, exc_info=1)
            return None

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
        try:
            return self.mimetype_handler.get_icon_url()
        except Exception as e:
            logging.error('Error when calling get_thumbnail for '
                          'MimetypeHandler %r: %s',
                          self.mimetype_handler, e, exc_info=1)
            return None

    @property
    def is_from_diff(self):
        """Returns if this file attachment is associated with a diff."""
        return (self.repository_id is not None or
                self.added_in_filediff_id is not None)

    def __str__(self):
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
        url = self.file.url

        if url.startswith('http:') or url.startswith('https:'):
            return url

        return build_server_url(url)
