from django import forms
from djblets.util.dates import get_tz_aware_utcnow

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import ReviewRequestDraft, FileAttachmentComment


class UploadFileForm(forms.Form):
    """A form that handles uploading of new files.

    A file takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.FileField(required=True)

    def create(self, file, review_request):
        caption = self.cleaned_data['caption']

        file_attachment = FileAttachment(caption='',
                                         draft_caption=caption,
                                         mimetype=file.content_type)
        file_attachment.file.save(file.name, file, save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_attachments.add(file_attachment)
        draft.save()

        return file_attachment


class CommentFileForm(forms.Form):
    """A form that handles commenting on a file."""
    review = forms.CharField(
        widget=forms.Textarea(attrs={'rows': '8','cols': '70'}))

    def create(self, file_attachment, review_request):
        comment = FileAttachmentComment(text=self.cleaned_data['review'],
                                        file_attachment=file_attachment)

        comment.timestamp = get_tz_aware_utcnow()
        comment.save(save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_attachment_comments.add(comment)
        draft.save()

        return comment
