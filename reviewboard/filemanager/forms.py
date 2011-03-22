import logging
import re

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import ugettext as _
from djblets.util.misc import get_object_or_none

from reviewboard.diffviewer import forms as diffviewer_forms
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.errors import OwnershipError
from reviewboard.reviews.models import DefaultReviewer, ReviewRequest, \
                                       ReviewRequestDraft, UploadedFileComment
from reviewboard.scmtools.errors import SCMError, ChangeNumberInUseError, \
                                        InvalidChangeNumberError, \
                                        ChangeSetError
from reviewboard.filemanager.models import UploadedFile
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite

class UploadFileForm(forms.Form):
    """
    A form that handles uploading of new files.
    A file takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.FileField(required=True)

    def create(self, file, review_request):
        upFile = UploadedFile(caption=self.cleaned_data['caption'],
                                draft_caption=self.cleaned_data['caption'])
        upFile.upfile.save(file.name, file, save=True)

        review_request.files.add(upFile)

        draft = ReviewRequestDraft.create(review_request)
        draft.files.add(upFile)
        draft.save()

        return upFile

class CommentFileForm(forms.Form):
    """
    A form that handles commenting on a file.
    """
    review = forms.CharField(widget=forms.Textarea(attrs={'rows':'8','cols':'70'}))

    def create(self, upfile, review_request):

        comment = UploadedFileComment(text=self.cleaned_data['review'],
                                upfile=upfile)

        comment.timestamp = datetime.now()
        comment.save(save=True)
        review_request.files.add(upFile)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_comments.add(comment)
        draft.save()

        return comment
