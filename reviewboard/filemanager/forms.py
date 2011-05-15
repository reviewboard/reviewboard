from datetime import datetime

from django import forms

from reviewboard.filemanager.models import UploadedFile
from reviewboard.reviews.models import ReviewRequestDraft, UploadedFileComment


class UploadFileForm(forms.Form):
    """A form that handles uploading of new files.

    A file takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.FileField(required=True)

    def create(self, file, review_request):
        uploaded_file = UploadedFile(caption=self.cleaned_data['caption'])
        uploaded_file.file.save(file.name, file, save=True)

        review_request.files.add(uploaded_file)

        draft = ReviewRequestDraft.create(review_request)
        draft.files.add(uploaded_file)
        draft.save()

        return uploaded_file


class CommentFileForm(forms.Form):
    """A form that handles commenting on a file."""
    review = forms.CharField(
        widget=forms.Textarea(attrs={'rows': '8','cols': '70'}))

    def create(self, file, review_request):
        comment = UploadedFileComment(text=self.cleaned_data['review'],
                                      file=file)

        comment.timestamp = datetime.now()
        comment.save(save=True)
        review_request.files.add(file)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_comments.add(comment)
        draft.save()

        return comment
