"""A comment on a file attachment."""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING, cast

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from typing_extensions import NotRequired, TypedDict

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models.base_comment import BaseComment

if TYPE_CHECKING:
    from django.utils.safestring import SafeText, mark_safe

    from reviewboard.diffviewer.models import DiffSet, FileDiff
    from reviewboard.reviews.ui.base import ReviewUI


logger = logging.getLogger(__name__)


class FileAttachmentCommentRevisionInfo(TypedDict):
    """Information about the diff revisions for a file attachment comment.

    For file attachment comments which are attached to files in a diff, we
    need to be able to get back the revision information.

    Version Added:
        7.0
    """

    #: The revision of the diff that the comment is on.
    diff_revision: int

    #: The PK of the DiffSet that the comment is on.
    diffset_id: int

    #: The interdiff revision, if present.
    interdiff_revision: Optional[int]

    #: The PK of the interdiff DiffSet, when present.
    interdiffset_id: Optional[int]

    #: The base commit ID, if present.
    base_commit_id: Optional[int]

    #: The tip commit ID, if present.
    tip_commit_id: Optional[int]

    #: The last commit ID in the commit series.
    #:
    #: This is used for some other computation when ``tip_commit_id`` is
    #: None.
    last_commit_id: NotRequired[int]

    #: The filediff for the modified version of the file.
    modified_filediff: FileDiff

    #: The diffset for the modified version of the file.
    modified_diffset: DiffSet


class FileAttachmentComment(BaseComment):
    """A comment on a file attachment."""

    anchor_prefix = "fcomment"
    comment_type = "file"

    file_attachment = models.ForeignKey(
        FileAttachment,
        on_delete=models.CASCADE,
        verbose_name=_('file attachment'),
        related_name="comments")
    diff_against_file_attachment = models.ForeignKey(
        FileAttachment,
        on_delete=models.CASCADE,
        verbose_name=_('diff against file attachment'),
        related_name="diffed_against_comments",
        null=True,
        blank=True)

    @cached_property
    def review_ui(self) -> Optional[ReviewUI]:
        """Return a ReviewUI appropriate for this comment.

        If a ReviewUI is available for this type of file, an instance of
        one will be returned that's associated with this comment's
        FileAttachment and the one being diffed against (if any).

        Returns:
            reviewboard.reviews.ui.base.ReviewUI:
            The Review UI instance, if one is available.
        """
        review_ui = self.file_attachment.review_ui

        if not review_ui:
            return None

        if review_ui.supports_diffing and self.diff_against_file_attachment:
            review_ui.set_diff_against(self.diff_against_file_attachment)

        return review_ui

    @property
    def thumbnail(self) -> Optional[SafeText]:
        """Return the thumbnail for this comment, if any, as HTML.

        The thumbnail will be generated from the appropriate ReviewUI,
        if there is one for this type of file.

        Returns:
            django.utils.safestring.SafeText:
            The thumbnail for the file comment.
        """
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_thumbnail(self)
            except Exception as e:
                logger.exception('Error when calling get_comment_thumbnail '
                                 'for ReviewUI %r: %s',
                                 review_ui, e)

        return mark_safe('')

    def get_absolute_url(self) -> Optional[str]:
        """Return the URL for this comment.

        Returns:
            str:
            The URL to link to for the comment.
        """
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_link_url(self)
            except Exception as e:
                logger.exception('Error when calling get_comment_link_url '
                                 'for ReviewUI %r: %s',
                                 review_ui, e)

        return self.file_attachment.get_absolute_url()

    def get_link_text(self) -> Optional[str]:
        """Return the text for the link to the file.

        Returns:
            str:
            The text to use for the link to the file.
        """
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_link_text(self)
            except Exception as e:
                logger.exception('Error when calling get_comment_link_text '
                                 'for ReviewUI %r: %s',
                                 review_ui, e)

        return self.file_attachment.display_name

    def attachment_is_public(self) -> bool:
        """Return whether the attachment(s) being commented on are public.

        Returns:
            bool:
            True if the file attachment (and diff against file attachment, if
            applicable) is public.
        """
        return (self.file_attachment.review_request.exists() or
                self.file_attachment.inactive_review_request.exists())

    def get_comment_diff_revision_info(
        self,
    ) -> Optional[FileAttachmentCommentRevisionInfo]:
        """Return the revision info for the comment.

        Version Added:
            7.0

        Returns:
            FileAttachmentCommentRevisionInfo:
            The revision information.
        """
        if not self.file_attachment.is_from_diff:
            return None

        diff_revision: int
        diffset_id: int
        interdiff_revision: Optional[int] = None
        interdiffset_id: Optional[int] = None

        modified_filediff = self.file_attachment.added_in_filediff
        modified_diffset = modified_filediff.diffset

        base_commit_id: Optional[int] = None
        tip_commit_id: Optional[int] = None

        diff_attachment = self.diff_against_file_attachment

        if diff_attachment is None:
            # This was a newly-added file.
            diff_revision = modified_diffset.revision
            diffset_id = modified_diffset.pk
            tip_commit_id = modified_filediff.commit_id
        else:
            orig_filediff = diff_attachment.added_in_filediff

            if orig_filediff is None:
                # The comment was made against a single diff revision.
                diff_revision = modified_diffset.revision
                diffset_id = modified_diffset.pk
                tip_commit_id = modified_filediff.commit_id
            else:
                orig_diffset = orig_filediff.diffset

                if orig_diffset.revision == modified_diffset.revision:
                    # The comment was made against a commit range on a single
                    # revision.
                    diff_revision = modified_diffset.revision
                    diffset_id = modified_diffset.pk
                    base_commit_id = orig_filediff.commit_id
                    tip_commit_id = modified_filediff.commit_id
                else:
                    # The comment was made on an interdiff.
                    diff_revision = orig_diffset.revision
                    diffset_id = orig_diffset.pk
                    interdiff_revision = modified_diffset.revision
                    interdiffset_id = modified_diffset.pk

        result: FileAttachmentCommentRevisionInfo = {
            'diff_revision': diff_revision,
            'diffset_id': diffset_id,
            'interdiff_revision': interdiff_revision,
            'interdiffset_id': interdiffset_id,
            'base_commit_id': base_commit_id,
            'tip_commit_id': tip_commit_id,
            'modified_filediff': modified_filediff,
            'modified_diffset': modified_diffset,
        }

        if tip_commit_id:
            last_commit_id = cast(int, (
                modified_diffset.commits
                .order_by('-pk')
                .values_list('pk', flat=True)
            )[0])

            # We don't specify the tip commit ID in the URL if it's the last
            # commit in the series.
            if tip_commit_id == last_commit_id:
                result['last_commit_id'] = last_commit_id
                result['tip_commit_id'] = None

        return result

    class Meta(BaseComment.Meta):
        """Metadata for the FileAttachmentComment model."""

        db_table = 'reviews_fileattachmentcomment'
        verbose_name = _('File Attachment Comment')
        verbose_name_plural = _('File Attachment Comments')
