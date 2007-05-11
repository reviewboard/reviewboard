from django import newforms as forms
from django.conf import settings
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.scmtools.models import Repository
import reviewboard.diffviewer.parser as diffparser
import reviewboard.scmtools as scmtools
from scmtools import PRE_CREATION

class UploadDiffForm(forms.Form):
    # XXX: it'd be really nice to have "required" dependent on scmtool
    repositoryid = forms.IntegerField(required=True, widget=forms.HiddenInput)
    basedir = forms.CharField(required=False)
    path = forms.CharField(widget=forms.FileInput())

    def create(self, file, diffset_history=None):
        # Parse the diff
        repository = Repository.objects.get(pk=self.clean_data['repositoryid'])

        files = diffparser.parse(file["content"])

        if len(files) == 0:
            raise Exception("Empty diff") # XXX

        # Check that we can actually get all these files.
        tool = repository.get_scmtool()

        if tool.get_diffs_use_absolute_paths():
            basedir = ''
        else:
            basedir = str(self.clean_data['basedir']) + '/'

        for f in files:
            f2, revision = tool.parse_diff_revision(f.origFile, f.origInfo)
            filename = basedir + f2

            if revision != PRE_CREATION and \
               not tool.file_exists(filename, revision):
                raise scmtools.FileNotFoundException(filename, revision)

            f.origFile = filename
            f.origInfo = revision

        diffset = DiffSet(name=file["filename"], revision=0,
                          history=diffset_history)
        diffset.repository = repository
        diffset.save()

        for f in files:
            filediff = FileDiff(diffset=diffset,
                                source_file=f.origFile,
                                dest_file=basedir + f.newFile,
                                source_revision=str(f.origInfo),
                                dest_detail=f.newInfo,
                                diff=f.data)
            filediff.save()

        return diffset
