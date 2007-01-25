from django import newforms as forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.diffviewer.models import DiffSet, FileDiff
import reviewboard.diffviewer.parser as diffparser

class UploadDiffForm(forms.Form):
    path = forms.CharField(widget=forms.FileInput())

    def create(self, file, diffset_history=None):
        # Parse the diff
        files = diffparser.parse(file["content"])

        if len(files) == 0:
            raise "Empty diff" # XXX

        diffset = DiffSet(name=file["filename"], revision=0,
                          history=diffset_history)
        diffset.save()

        for file in files:
            filediff = FileDiff(diffset=diffset,
                                source_file=file.origFile,
                                dest_file=file.newFile,
                                source_detail=file.origInfo,
                                dest_detail=file.newInfo,
                                diff=file.data)
            filediff.save()

        return diffset
