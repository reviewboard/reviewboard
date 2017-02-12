from __future__ import unicode_literals

import logging

from django.db import models
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

    @property
    def thumbnail(self):
        """Returns the thumbnail for this comment, if any, as HTML.

        The thumbnail will be generated from the appropriate ReviewUI,
        if there is one for this type of file.
        """
        review_ui = self.file_attachment.review_ui

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
        review_ui = self.file_attachment.review_ui
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
        review_ui = self.file_attachment.review_ui
        if review_ui:
            try:
                return review_ui.get_comment_link_text(self)
            except Exception as e:
                logging.error('Error when calling get_comment_thumbnail for '
                              'FileAttachmentReviewUI %r: %s',
                              review_ui, e, exc_info=1)
        else:
            return self.file_attachment.filename

    class Meta(BaseComment.Meta):
        verbose_name = _('file attachment comment')
        verbose_name_plural = _('file attachment comments')
