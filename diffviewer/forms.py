import os

from django import newforms as forms
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

from reviewboard.diffviewer.diffutils import DEFAULT_DIFF_COMPAT_VERSION
from reviewboard.diffviewer.models import DiffSet, FileDiff
import reviewboard.scmtools as scmtools
from scmtools import PRE_CREATION, UNKNOWN

class EmptyDiffError(ValueError):
    pass


class UploadDiffForm(forms.Form):
    basedir = forms.CharField(label=_("Base directory"))
    path = forms.CharField(label=_("Diff path"), widget=forms.FileInput())

    # Extensions used for intelligent sorting of header files
    # before implementation files.
    HEADER_EXTENSIONS = ["h", "H", "hh", "hpp", "hxx", "h++"]
    IMPL_EXTENSIONS   = ["c", "C", "cc", "cpp", "cxx", "c++", "m", "mm", "M"]

    def __init__(self, repository, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.repository = repository

        if self.repository.get_scmtool().get_diffs_use_absolute_paths():
            # This SCMTool uses absolute paths, so there's no need to ask
            # the user for the base directory.
            del(self.fields['basedir'])

    def create(self, file, diffset_history=None):
        # Parse the diff
        tool = self.repository.get_scmtool()
        files = tool.get_parser(file["content"]).parse()

        if len(files) == 0:
            raise EmptyDiffError(_("The diff file is empty"))

        # Check that we can actually get all these files.
        if tool.get_diffs_use_absolute_paths():
            basedir = ''
        else:
            basedir = smart_unicode(self.cleaned_data['basedir'])

        for f in files:
            f2, revision = tool.parse_diff_revision(f.origFile, f.origInfo)
            if f2.startswith("/"):
                filename = f2
            else:
                filename = os.path.join(basedir, f2).replace("\\", "/")

            # FIXME: this would be a good place to find permissions errors
            if revision != PRE_CREATION and revision != UNKNOWN and \
               not tool.file_exists(filename, revision):
                raise scmtools.FileNotFoundError(filename, revision)

            f.origFile = filename
            f.origInfo = revision

        diffset = DiffSet(name=file["filename"], revision=0,
                          history=diffset_history,
                          diffcompat=DEFAULT_DIFF_COMPAT_VERSION)
        diffset.repository = self.repository
        diffset.save()

        # Sort the files so that header files come before implementation.
        files.sort(cmp=self._compare_files, key=lambda f: f.origFile)

        for f in files:
            filediff = FileDiff(diffset=diffset,
                                source_file=f.origFile,
                                dest_file=os.path.join(basedir, f.newFile).replace("\\", "/"),
                                source_revision=smart_unicode(f.origInfo),
                                dest_detail=f.newInfo,
                                diff=f.data,
                                binary=f.binary)
            filediff.save()

        return diffset

    def _compare_files(self, filename1, filename2):
        """
        Compares two files, giving precedence to header files over source
        files. This allows the resulting list of files to be more
        intelligently sorted.
        """
        if filename1.find('.') != -1 and filename2.find('.') != -1:
            basename1, ext1 = filename1.rsplit('.', 1)
            basename2, ext2 = filename2.rsplit('.', 1)

            if basename1 == basename2:
                if ext1 in self.HEADER_EXTENSIONS and \
                   ext2 in self.IMPL_EXTENSIONS:
                    return -1
                elif ext1 in self.IMPL_EXTENSIONS and \
                     ext2 in self.HEADER_EXTENSIONS:
                    return 1

        return cmp(filename1, filename2)
