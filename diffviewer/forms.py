from django import newforms as forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.diffviewer.models import DiffSet, FileDiff

class UploadDiffForm(forms.Form):
    path = forms.CharField(widget=forms.FileInput())

    def create(self, diffset_history, file):
        diffset = DiffSet()

        if diffset_history.diffsets.count() == 0:
            diffset.revision = 0
        else:
            diffset.revision = diffset_history.diffsets.latest().revision + 1

        # Parse the diff
        lines = file["content"].splitlines()
        for line in lines:
            if line.startswith("Index: "):
                filediff = FileDiff(filename=filename, source_path=source_path)

