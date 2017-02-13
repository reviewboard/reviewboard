from __future__ import unicode_literals

import logging

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models.base_comment import BaseComment


class FileAttachmentComment(BaseComment):
    """A comment on a file attachment."""
    anchor_prefix = "fcomment"
    comment_type = "file"

    file_attachment = models.ForeignKey(
        FileAttachment,
        verbose_name=_('file attachment'),
        related_name="comments")
    diff_against_file_attachment = models.ForeignKey(
        FileAttachment,
        verbose_name=_('diff against file attachment'),
        related_name="diffed_against_comments",
        null=True,
        blank=True)

    @cached_property
    def review_ui(self):
        """Return a ReviewUI appropriate for this comment.

        If a ReviewUI is available for this type of file, an instance of
        one will be returned that's associated with this comment's
        FileAttachment and the one being diffed against (if any).
        """
        from reviewboard.reviews.ui.base import FileAttachmentReviewUI

        # Note that we need to create our own instance here, so that we don't
        # end up altering the state of another ReviewUI's file attachment
        # (particularly with calling set_diff_against below).
        review_ui = FileAttachmentReviewUI.for_type(self.file_attachment)

        if not review_ui:
            return None

        if review_ui.supports_diffing and self.diff_against_file_attachment:
            review_ui.set_diff_against(self.diff_against_file_attachment)

        return review_ui

    @property
    def thumbnail(self):
        """Returns the thumbnail for this comment, if any, as HTML.

        The thumbnail will be generated from the appropriate ReviewUI,
        if there is one for this type of file.
        """
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_thumbnail(self)
            except Exception as e:
                logging.error('Error when calling get_comment_thumbnail for '
                              'FileAttachmentReviewUI %r: %s',
                              review_ui, e, exc_info=1)
        else:
            return ''

    def get_absolute_url(self):
        """Returns the URL for this comment."""
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_link_url(self)
            except Exception as e:
                logging.error('Error when calling get_comment_thumbnail for '
                              'FileAttachmentReviewUI %r: %s',
                              review_ui, e, exc_info=1)
        else:
            return self.file_attachment.get_absolute_url()

    def get_link_text(self):
        """Returns the text for the link to the file."""
        review_ui = self.review_ui

        if review_ui:
            try:
                return review_ui.get_comment_link_text(self)
            except Exception as e:
                logging.error('Error when calling get_comment_link_text for '
                              'FileAttachmentReviewUI %r: %s',
                              review_ui, e, exc_info=1)
        else:
            return self.file_attachment.display_name

    class Meta(BaseComment.Meta):
        db_table = 'reviews_fileattachmentcomment'
        verbose_name = _('File Attachment Comment')
        verbose_name_plural = _('File Attachment Comments')
