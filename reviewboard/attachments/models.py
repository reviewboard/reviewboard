from __future__ import unicode_literals

import logging
import os

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import RelationCounterField

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.managers import FileAttachmentManager
from reviewboard.attachments.mimetypes import MimetypeHandler
from reviewboard.diffviewer.models import FileDiff
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


class FileAttachmentHistory(models.Model):
    """Revision history for a single file attachment.

    This tracks multiple revisions of the same file attachment (for instance,
    when someone replaces a screenshot with an updated version).
    """

    display_position = models.IntegerField()
    latest_revision = RelationCounterField('file_attachments')

    def get_revision_to_id_map(self):
        """Return a map from revision number to FileAttachment ID."""
        results = {}

        for attachment in self.file_attachments.all():
            results[attachment.attachment_revision] = attachment.id

        return results

    @staticmethod
    def compute_next_display_position(review_request):
        """Compute the display position for a new FileAttachmentHistory."""
        # Right now, display_position is monotonically increasing for each
        # review request. In the future this might be extended to allow the
        # user to change the order of attachments on the page.
        max_position = (
            FileAttachmentHistory.objects
            .filter(review_request=review_request)
            .aggregate(Max('display_position'))
            .get('display_position__max')) or 0

        return max_position + 1

    class Meta:
        db_table = 'attachments_fileattachmenthistory'
        verbose_name = _('File Attachment History')
        verbose_name_plural = _('File Attachment Histories')


@python_2_unicode_compatible
class FileAttachment(models.Model):
    """A file associated with a review request.

    Like diffs, a file can have comments associated with it.
    These comments are of type
    :py:class:`reviewboard.reviews.models.FileAttachmentComment`.
    """

    caption = models.CharField(_('caption'), max_length=256, blank=True)
    draft_caption = models.CharField(_('draft caption'),
                                     max_length=256, blank=True)
    orig_filename = models.CharField(_('original filename'),
                                     max_length=256, blank=True, null=True)
    user = models.ForeignKey(User,
                             blank=True,
                             null=True,
                             related_name='file_attachments')

    local_site = models.ForeignKey(LocalSite,
                                   blank=True,
                                   null=True,
                                   related_name='file_attachments')

    uuid = models.CharField(_('uuid'), max_length=255, blank=True)

    file = models.FileField(_('file'),
                            max_length=512,
                            blank=True,
                            null=True,
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

    attachment_history = models.ForeignKey(FileAttachmentHistory,
                                           blank=True,
                                           null=True,
                                           related_name='file_attachments')
    attachment_revision = models.IntegerField(default=0)

    objects = FileAttachmentManager()

    @property
    def mimetype_handler(self):
        """Return the mimetype handler for this file."""
        if not hasattr(self, '_thumbnail'):
            self._thumbnail = MimetypeHandler.for_type(self)

        return self._thumbnail

    @property
    def review_ui(self):
        """Return the review UI for this file."""
        if not hasattr(self, '_review_ui'):
            from reviewboard.reviews.ui.base import FileAttachmentReviewUI
            self._review_ui = FileAttachmentReviewUI.for_type(self)

        return self._review_ui

    def _get_thumbnail(self):
        """Return the thumbnail for display."""
        if not self.mimetype_handler:
            return None

        try:
            return self.mimetype_handler.get_thumbnail()
        except Exception as e:
            logging.error('Error when calling get_thumbnail for '
                          'MimetypeHandler %r: %s',
                          self.mimetype_handler, e, exc_info=1)
            return None

    def _set_thumbnail(self, data):
        """Set the thumbnail."""
        if not self.mimetype_handler:
            return None

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
        """Return the filename for display purposes."""
        # Older versions of Review Board didn't store the original filename,
        # instead just using the FileField's name. Newer versions have
        # a dedicated filename field.
        if self.file:
            alt = os.path.basename(self.file.name)
        else:
            alt = None

        return self.orig_filename or alt

    @property
    def display_name(self):
        """Return a display name for the file."""
        if self.caption:
            return self.caption
        else:
            return self.filename

    @property
    def icon_url(self):
        """Return the icon URL for this file."""
        if not self.mimetype_handler:
            return None

        try:
            return self.mimetype_handler.get_icon_url()
        except Exception as e:
            logging.error('Error when calling get_thumbnail for '
                          'MimetypeHandler %r: %s',
                          self.mimetype_handler, e, exc_info=1)
            return None

    @property
    def is_from_diff(self):
        """Return if this file attachment is associated with a diff."""
        return (self.repository_id is not None or
                self.added_in_filediff_id is not None)

    @property
    def num_revisions(self):
        """Return the number of revisions of this attachment."""
        return FileAttachment.objects.filter(
            attachment_history=self.attachment_history_id).count() - 1

    def __str__(self):
        """Return a string representation of this file for the admin list."""
        return self.caption

    def get_review_request(self):
        """Return the ReviewRequest that this file is attached to."""
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
        """Return all the comments made on this file attachment."""
        if not hasattr(self, '_comments'):
            self._comments = list(self.comments.all())

        return self._comments

    def get_absolute_url(self):
        """Return the absolute URL to download this file."""
        if not self.file:
            return None

        url = self.file.url

        if url.startswith('http:') or url.startswith('https:'):
            return url

        return build_server_url(url)

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to this FileAttachment.

        This checks that the user has access to the LocalSite if the attachment
        is associated with a local site. This is only applicable for user owned
        file attachments.
        """
        return (self.user_id is not None and
                user.is_authenticated() and
                (user.is_superuser or self.user_id == user.pk) and
                (not self.local_site or
                 self.local_site.is_accessible_by(user)))

    def is_mutable_by(self, user):
        """Returns whether or not a user can modify this FileAttachment.

        This checks that the user is either a superuser or the owner of the
        file attachment. This is only applicable for user owned file
        attachments.
        """
        return (self.user_id is not None and
                user.is_authenticated() and
                (user.is_superuser or self.user_id == user.pk))

    class Meta:
        db_table = 'attachments_fileattachment'
        get_latest_by = 'attachment_revision'
        verbose_name = _('File Attachment')
        verbose_name_plural = _('File Attachments')


def get_latest_file_attachments(file_attachments):
    """Filter the list of file attachments to only return the latest revisions.

    Args:
        file_attachments (list of
                          reviewboard.attachments.models.FileAttachment):
            The file attachments to filter.

    Returns:
        list of reviewboard.attachments.models.FileAttachment:
        The list of file attachments that are the latest revisions in their
        respective histories.
    """
    file_attachment_histories = FileAttachmentHistory.objects.filter(
        file_attachments__in=file_attachments)
    latest = {
        data['id']: data['latest_revision']
        for data in file_attachment_histories.values('id', 'latest_revision')
    }

    return [
        f
        for f in file_attachments
        if (not f.is_from_diff and
            f.attachment_revision == latest[f.attachment_history_id])
    ]
