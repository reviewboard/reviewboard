"""Models for file attachments and related objects."""

from __future__ import annotations

import logging
import os
from inspect import signature
from typing import ClassVar, List, Optional, Sequence, TYPE_CHECKING

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField, RelationCounterField
from djblets.util.decorators import cached_property
from typing_extensions import TypeAlias

from reviewboard.admin.server import build_server_url
from reviewboard.attachments.managers import FileAttachmentManager
from reviewboard.attachments.mimetypes import MimetypeHandler
from reviewboard.deprecation import RemovedInReviewBoard90Warning
from reviewboard.diffviewer.diffutils import get_sha256
from reviewboard.diffviewer.models import FileDiff
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse

if TYPE_CHECKING:
    from reviewboard.reviews.models import ReviewRequest


logger = logging.getLogger(__name__)


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
                             on_delete=models.CASCADE,
                             blank=True,
                             null=True,
                             related_name='file_attachments')

    #: The local site that this attachment is on.
    #:
    #: Prior to RB 8.1, this was only  present for "user" file attachments
    #: (that is, attachments that were uploaded into a comment box or otherwise
    #: created from the user file attachments API) and for ones linked to
    #: file diffs. Attachments which are uploaded directly to a Review Request,
    #: not part of the diff, did not have this relation populated.
    #:
    #: On RB 8.1 and higher we set this for all file attachments. Callers
    #: should still use the :py:meth:`get_local_site` method instead of
    #: accessing this directly for consistency.
    local_site = models.ForeignKey(LocalSite,
                                   on_delete=models.CASCADE,
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

    extra_data = JSONField(null=True)

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
                                   on_delete=models.CASCADE,
                                   blank=True,
                                   null=True,
                                   related_name='file_attachments')
    added_in_filediff = models.ForeignKey(FileDiff,
                                          on_delete=models.CASCADE,
                                          blank=True,
                                          null=True,
                                          related_name='added_attachments')

    attachment_history = models.ForeignKey(FileAttachmentHistory,
                                           on_delete=models.CASCADE,
                                           blank=True,
                                           null=True,
                                           related_name='file_attachments')
    attachment_revision = models.IntegerField(default=0)

    objects: ClassVar[FileAttachmentManager] = FileAttachmentManager()

    #: The extra_data key that denotes if :py:attr:`local_site` has been set.
    #:
    #: Version Added:
    #:     8.1
    DEFINED_LOCAL_SITE_KEY = '__defined_local_site'

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
            self._review_ui = None

            from reviewboard.reviews.ui.base import ReviewUI
            review_ui_class = ReviewUI.for_object(self)

            if review_ui_class:
                try:
                    self._review_ui = review_ui_class(
                        obj=self,
                        review_request=self.get_review_request())
                except ObjectDoesNotExist as e:
                    logger.error('Unable to load Review UI %r for %s: %s',
                                 review_ui_class, self, e)
                except Exception as e:
                    logger.exception('Error instantiating Review UI %r" %s',
                                     review_ui_class, e)

        return self._review_ui

    def _get_thumbnail(self):
        """Return the thumbnail for display."""
        if not self.mimetype_handler:
            return None

        try:
            return self.mimetype_handler.get_thumbnail()
        except Exception as e:
            logger.error('Error when calling get_thumbnail for '
                         'MimetypeHandler %r: %s',
                         self.mimetype_handler, e, exc_info=True)
            return None

    def _set_thumbnail(self, data):
        """Set the thumbnail."""
        if not self.mimetype_handler:
            return None

        try:
            self.mimetype_handler.set_thumbnail(data)
        except Exception as e:
            logger.error('Error when calling get_thumbnail for '
                         'MimetypeHandler %r: %s',
                         self.mimetype_handler, e, exc_info=True)
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
            logger.error('Error when calling get_thumbnail for '
                         'MimetypeHandler %r: %s',
                         self.mimetype_handler, e, exc_info=True)
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

    @cached_property
    def sha256_checksum(self) -> str:
        """The SHA256 hash of the file.

        Version Added:
            8.0
        """
        checksum: (str | None) = self.extra_data.get('sha256_checksum')

        if checksum is None:
            f = self.file

            try:
                checksum = get_sha256(f.file)
            finally:
                f.close()

            self.extra_data['sha256_checksum'] = checksum
            self.save(update_fields=['extra_data'])

        return checksum

    def __str__(self):
        """Return a string representation of this file for the admin list."""
        return self.caption

    def get_review_request(self) -> ReviewRequest:
        """Return the ReviewRequest that this file is attached to.

        Raises:
            django.core.exceptions.ObjectDoesNotExist:
                The review request does not exist or hasn't been linked yet.
        """
        if hasattr(self, '_review_request'):
            return self._review_request

        try:
            self._review_request = self.review_request.all()[0]
        except IndexError:
            try:
                self._review_request = self.inactive_review_request.all()[0]
            except IndexError:
                # Maybe it's on a draft.
                try:
                    draft = self.drafts.get()
                except ObjectDoesNotExist:
                    draft = self.inactive_drafts.get()

                self._review_request = draft.review_request

        return self._review_request

    def get_local_site(self) -> LocalSite | None:
        """Return the local site for this attachment.

        Version Changed:
            8.1:
            This will return :py:attr:`local_site` if we know that a value has
            been explicitly set for it. Otherwise, this will determine the
            local site, save that value to :py:attr:`local_site` and return
            it.

        Version Added:
            7.0.3

        Returns:
            reviewboard.site.models.LocalSite:
            The local site that this attachment is related to, if any.
        """
        local_site = self.local_site
        defined_local_site_key = self.DEFINED_LOCAL_SITE_KEY

        if self.extra_data.get(defined_local_site_key, False):
            # We have an explicit value for the local site (passed on creation
            # for RB 8.1+ or we figured it out below already). We can use it.
            return local_site

        # Pre RB 8.1, we need to figure out the local site and save it.
        if self.user_id is None and local_site is None:
            # This could be a file attachment that doesn't have a local site,
            # or one that relies on its review request for the local site.
            try:
                local_site = self.get_review_request().local_site
            except ObjectDoesNotExist:
                # We're being asked for the local site before the attachment
                # has been linked to a review request. This shouldn't happen
                # in normal operation, RB 8.1+ sets local_site at creation
                # and any existing attachments will have already been linked
                # to their review request right after their first save.
                #
                # Fall back to ``None`` and log just in case.
                logger.error(
                    'Could not determine Local Site for file attachment %s. '
                    'Set either the Local Site or the review request on the '
                    'attachment to fix this.',
                    self.pk)

                return None

        # We now know the local_site value for pre RB 8.1 file attachments.
        # Save it so we don't have to figure it out again on the next access.
        self.local_site = local_site
        self.extra_data[defined_local_site_key] = True

        if self.pk is not None:
            self.save(update_fields=['local_site', 'extra_data'])

        return local_site

    def get_comments(self):
        """Return all the comments made on this file attachment."""
        if not hasattr(self, '_comments'):
            self._comments = list(self.comments.all())

        return self._comments

    def get_raw_download_url(self) -> Optional[str]:
        """Return the absolute URL to download this file.

        The URL will be determined by the storage backend. It may be
        accessible for only a limited amount of time, and may or may not be
        cacheable by the browser.

        Version Added:
            7.0

        Returns:
            str:
            The absolute URL to the file.

            This will be ``None`` if there's no file backing for any reason.
        """
        if not self.file:
            return None

        url = self.file.url

        if not url or url.startswith(('http:', 'https:')):
            return url

        return build_server_url(url)

    def get_raw_thumbnail_image_url(
        self,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[str]:
        """Return the absolute URL for an image thumbnail for this file.

        The URL will be determined by the storage backend. It may be
        accessible for only a limited amount of time, and may or may not be
        cacheable by the browser.

        Not all file attachments support image thumbnails. If not supported,
        this will be ``None``.

        Version Added:
            7.0

        Returns:
            str:
            The absolute URL to the file.

            This will be ``None`` if there's no file backing for any reason,
            or if the attachment doesn't support image thumbnails.
        """
        url: Optional[str] = None
        mimetype_handler = self.mimetype_handler

        if mimetype_handler:
            try:
                url = mimetype_handler.get_raw_thumbnail_image_url(
                    width=width,
                    height=height)
            except NotImplementedError:
                # This file type doesn't support image thumbnails.
                pass

        if not url or url.startswith(('http:', 'https:')):
            return url

        return build_server_url(url)

    def get_absolute_url(self) -> Optional[str]:
        """Return the absolute URL for accessing the file.

        This will return the correct URL for either user-uploaded or
        review request file attachments.

        If the association could not be determined, this will return ``None``.

        The URL will always be a full absolute URL, usable in e-mails and
        other sources.

        Returns:
            str:
            The URL to access the file attachment contents.
        """
        if self.user is not None:
            # This is a user-uploaded file attachment.
            path = local_site_reverse(
                'user-file-attachment',
                local_site=self.get_local_site(),
                kwargs={
                    'file_attachment_uuid': self.uuid,
                    'username': self.user.username,
                })
        else:
            # This is a file attachment on a review request.
            try:
                review_request = self.get_review_request()

                path = local_site_reverse(
                    'download-file-attachment',
                    local_site=self.get_local_site(),
                    kwargs={
                        'file_attachment_id': self.pk,
                        'review_request_id': review_request.get_display_id(),
                    })
            except ObjectDoesNotExist:
                return None

        return build_server_url(path)

    def is_review_ui_accessible_by(
        self,
        user: User,
    ) -> bool:
        """Return whether a user can access the file attachment's review UI.

        This will check that a review UI exists for the file attachment and
        that it's enabled for the provided user and review request.

        Version Added:
            7.0.3

        Args:
            user (django.contrib.auth.models.User):
                The user who is accessing the review UI.

        Returns:
            bool:
            ``True`` if a review UI exists and can be accessed by the user.
            ``False`` if the review UI does not exist, cannot be used, or
            there's an error when checking.
        """
        review_ui = self.review_ui

        if not review_ui:
            return False

        review_request = self.get_review_request()

        try:
            params = signature(review_ui.is_enabled_for).parameters

            if 'file_attachment' in params:
                RemovedInReviewBoard90Warning.warn(
                    'The file_attachment parameter to ReviewUI.is_enabled_for '
                    'has been removed. Please use obj= instead in Review UI %r'
                    % review_ui)

                return review_ui.is_enabled_for(
                    user=user,
                    review_request=review_request,
                    file_attachment=self)
            else:
                return review_ui.is_enabled_for(
                    user=user,
                    review_request=review_request,
                    obj=self)
        except Exception as e:
            logger.exception('Error when calling is_enabled_for with '
                             'ReviewUI %r: %s',
                             review_ui, e)
            return False

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to this FileAttachment.

        This checks that the user has access to the LocalSite if the attachment
        is associated with a local site. This is only applicable for user owned
        file attachments.
        """
        return (self.user_id is not None and
                user.is_authenticated and
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
                user.is_authenticated and
                (user.is_superuser or self.user_id == user.pk))

    class Meta:
        db_table = 'attachments_fileattachment'
        get_latest_by = 'attachment_revision'
        verbose_name = _('File Attachment')
        verbose_name_plural = _('File Attachments')


def get_latest_file_attachments(
    file_attachments: FileAttachmentSequence,
) -> List[FileAttachment]:
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


#: Type alias for a sequence of file attachments.
#:
#: Version Added:
#:     6.0
FileAttachmentSequence: TypeAlias = Sequence[FileAttachment]
