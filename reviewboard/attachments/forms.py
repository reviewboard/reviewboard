from __future__ import unicode_literals

from uuid import uuid4
import os

from django import forms

from reviewboard.attachments.mimetypes import get_uploaded_file_mimetype
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.reviews.models import ReviewRequestDraft


class UploadFileForm(forms.Form):
    """A form that handles uploading of new files."""

    #: The caption for the file.
    caption = forms.CharField(required=False)

    #: The file itself.
    path = forms.FileField(required=True)

    #: An optional file attachment history, used when creating a new revision
    #: for an existing file attachment. If this is not specified, a new history
    #: will be created.
    attachment_history = forms.ModelChoiceField(
        queryset=FileAttachmentHistory.objects.all(),
        required=False)

    def __init__(self, review_request, *args, **kwargs):
        """Initialize the form.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to attach the file to.
        """
        super(UploadFileForm, self).__init__(*args, **kwargs)

        self.review_request = review_request

    def clean_attachment_history(self):
        """Validate that the specified file attachment history exists.

        Returns:
            reviewboard.attachments.models.FileAttachmentHistory:
            The history model.
        """
        history = self.cleaned_data['attachment_history']

        if (history is not None and
            not self.review_request.file_attachment_histories.filter(
                pk=history.pk).exists()):
            raise forms.ValidationError(
                'The FileAttachmentHistory provided is not part of this '
                'review request.')

        return history

    def create(self, filediff=None):
        """Create a FileAttachment based on this form.

        Args:
            filediff (reviewboard.diffviewer.models.FileDiff):
                The optional diff to attach this file to (for use when this
                file represents a binary file within the diff).

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment model.
        """
        file_obj = self.files['path']
        caption = self.cleaned_data['caption'] or file_obj.name

        mimetype = get_uploaded_file_mimetype(file_obj)
        filename = get_unique_filename(file_obj.name)

        if self.cleaned_data['attachment_history'] is None:
            # This is a new file: create a new FileAttachmentHistory for it
            attachment_history = FileAttachmentHistory()
            attachment_revision = 1

            attachment_history.display_position = \
                FileAttachmentHistory.compute_next_display_position(
                    self.review_request)
            attachment_history.save()
            self.review_request.file_attachment_histories.add(
                attachment_history)
        else:
            attachment_history = self.cleaned_data['attachment_history']

            try:
                latest = attachment_history.file_attachments.latest()
            except FileAttachment.DoesNotExist:
                latest = None

            if latest is None:
                # This should theoretically never happen, but who knows.
                attachment_revision = 1
            elif latest.review_request.exists():
                # This is a new update in the draft.
                attachment_revision = latest.attachment_revision + 1
            else:
                # The most recent revision is part of the same draft. Delete it
                # and replace with the newly uploaded file.
                attachment_revision = latest.attachment_revision
                latest.delete()

        attachment_kwargs = {
            'attachment_history': attachment_history,
            'attachment_revision': attachment_revision,
            'caption': '',
            'draft_caption': caption,
            'orig_filename': os.path.basename(file_obj.name),
            'mimetype': mimetype,
        }

        if filediff:
            file_attachment = FileAttachment.objects.create_from_filediff(
                filediff,
                save=False,
                **attachment_kwargs)
        else:
            file_attachment = FileAttachment(**attachment_kwargs)

        file_attachment.file.save(filename, file_obj, save=True)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.file_attachments.add(file_attachment)
        draft.save()

        return file_attachment


class UploadUserFileForm(forms.Form):
    """A form that handles uploading of user files."""

    #: The caption for the file.
    caption = forms.CharField(required=False)

    #: The file itself.
    path = forms.FileField(required=False)

    def create(self, user, local_site=None):
        """Create a FileAttachment based on this form.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns this file attachment.

            local_site (reviewboard.site.models.LocalSite):
                The optional local site.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment model.
        """
        file_obj = self.files.get('path')

        if file_obj:
            mimetype = get_uploaded_file_mimetype(file_obj)
            filename = get_unique_filename(file_obj.name)

            attachment_kwargs = {
                'caption': self.cleaned_data['caption'] or file_obj.name,
                'uuid': uuid4(),
                'orig_filename': os.path.basename(file_obj.name),
                'mimetype': mimetype,
                'user': user,
                'local_site': local_site,
            }

            file_attachment = FileAttachment(**attachment_kwargs)
            file_attachment.file.save(filename, file_obj, save=True)
        else:
            attachment_kwargs = {
                'caption': self.cleaned_data['caption'] or '',
                'uuid': uuid4(),
                'user': user,
                'local_site': local_site,
            }

            file_attachment = FileAttachment(**attachment_kwargs)

        file_attachment.save()

        return file_attachment

    def update(self, file_attachment):
        """Update an existing file attachment.

        Args:
            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment to update.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The updated file attachment.
        """
        caption = self.cleaned_data['caption']
        file_obj = self.files.get('path')

        if caption:
            file_attachment.caption = caption

        if file_obj:
            mimetype = get_uploaded_file_mimetype(file_obj)
            filename = get_unique_filename(file_obj.name)

            file_attachment.mimetype = mimetype
            file_attachment.orig_filename = os.path.basename(file_obj.name)
            file_attachment.file.save(filename, file_obj, save=True)

        file_attachment.save()

        return file_attachment


def get_unique_filename(filename):
    """Return a unique filename.

    Create a unique filename by concatenating a UUID with the given filename.

    Args:
        filename (six.text_type):
            The original filename.

    Returns:
        six.text_type:
        A new filename which is more unique.
    """
    return '%s__%s' % (uuid4(), filename)
