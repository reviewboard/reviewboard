from __future__ import unicode_literals

from uuid import uuid4
import os

from django import forms
from django.utils import timezone

from reviewboard.attachments.mimetypes import get_uploaded_file_mimetype
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.reviews.models import (ReviewRequestDraft,
                                        FileAttachmentComment)


class UploadFileForm(forms.Form):
    """A form that handles uploading of new files.

    A file takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.FileField(required=True)
    attachment_history = forms.ModelChoiceField(
        queryset=FileAttachmentHistory.objects.all(),
        required=False)

    def __init__(self, review_request, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)

        self.review_request = review_request

    def clean_attachment_history(self):
        history = self.cleaned_data['attachment_history']

        if (history is not None and
            not self.review_request.file_attachment_histories.filter(
                pk=history.pk).exists()):
            raise forms.ValidationError(
                'The FileAttachmentHistory provided is not part of this '
                'review request.')

        return history

    def create(self, filediff=None):
        file = self.files['path']
        caption = self.cleaned_data['caption'] or file.name

        mimetype = get_uploaded_file_mimetype(file)
        filename = get_unique_filename(file.name)

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
            'orig_filename': os.path.basename(file.name),
            'mimetype': mimetype,
        }

        if filediff:
            file_attachment = FileAttachment.objects.create_from_filediff(
                filediff,
                save=False,
                **attachment_kwargs)
        else:
            file_attachment = FileAttachment(**attachment_kwargs)

        file_attachment.file.save(filename, file, save=True)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.file_attachments.add(file_attachment)
        draft.save()

        return file_attachment


class UploadUserFileForm(forms.Form):
    """A form that handles uploading of user files.

    A file takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.FileField(required=False)

    def create(self, user, local_site=None):
        file = self.files.get('path')

        if file:
            mimetype = get_uploaded_file_mimetype(file)
            filename = get_unique_filename(file.name)

            attachment_kwargs = {
                'caption': self.cleaned_data['caption'] or file.name,
                'uuid': uuid4(),
                'orig_filename': os.path.basename(file.name),
                'mimetype': mimetype,
                'user': user,
                'local_site': local_site,
            }

            file_attachment = FileAttachment(**attachment_kwargs)
            file_attachment.file.save(filename, file, save=True)
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
        caption = self.cleaned_data['caption']
        file = self.files.get('path')

        if caption:
            file_attachment.caption = caption

        if file:
            mimetype = get_uploaded_file_mimetype(file)
            filename = get_unique_filename(file.name)

            file_attachment.mimetype = mimetype
            file_attachment.orig_filename = os.path.basename(file.name)
            file_attachment.file.save(filename, file, save=True)

        file_attachment.save()

        return file_attachment


class CommentFileForm(forms.Form):
    """A form that handles commenting on a file."""
    review = forms.CharField(widget=forms.Textarea(attrs={
        'rows': '8',
        'cols': '70'
    }))

    def create(self, file_attachment, review_request):
        comment = FileAttachmentComment(text=self.cleaned_data['review'],
                                        file_attachment=file_attachment)

        comment.timestamp = timezone.now()
        comment.save(save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_attachment_comments.add(comment)
        draft.save()

        return comment


def get_unique_filename(filename):
    """Creates a unique filename.

    Creates a unique filename by concatenating a UUID with the given filename.
    """
    return '%s__%s' % (uuid4(), filename)
