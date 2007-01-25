from django import newforms as forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.diffviewer.models import DiffSet, FileDiff
import reviewboard.diffviewer.parser as diffparser
import reviewboard.scmtools as scmtools

class UploadDiffForm(forms.Form):
    basedir = forms.CharField()
    path = forms.CharField(widget=forms.FileInput())

    def create(self, file, diffset_history=None):
        # Parse the diff
        files = diffparser.parse(file["content"])

        if len(files) == 0:
            raise "Empty diff" # XXX

        # Check that we can actually get all these files.
        tool = scmtools.get_tool()

        if tool.get_diffs_use_absolute_paths():
            basedir = ''
        else:
            basedir = str(self.clean_data['basedir']) + '/'

        for f in files:
            revision = tool.parse_diff_revision(f.origInfo)
            filename = basedir + f.origFile

            if not tool.file_exists(filename, revision):
                raise scmtools.FileNotFoundException(filename, revision)

        diffset = DiffSet(name=file["filename"], revision=0,
                          history=diffset_history)
        diffset.save()

        for file in files:
            filediff = FileDiff(diffset=diffset,
                                source_file=basedir + file.origFile,
                                dest_file=basedir + file.newFile,
                                source_detail=file.origInfo,
                                dest_detail=file.newInfo,
                                diff=file.data)
            filediff.save()

        return diffset
