import os

from django.db import models
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.fields import Base64DecodedValue

from reviewboard.diffviewer.differ import DEFAULT_DIFF_COMPAT_VERSION
from reviewboard.diffviewer.errors import DiffTooBigError, EmptyDiffError
from reviewboard.scmtools.core import PRE_CREATION, UNKNOWN, FileNotFoundError


class FileDiffDataManager(models.Manager):
    """
    A custom manager for FileDiffData

    Sets the binary data to a Base64DecodedValue, so that Base64Field is
    forced to encode the data. This is a workaround to Base64Field checking
    if the object has been saved into the database using the pk.
    """
    def get_or_create(self, *args, **kwargs):
        defaults = kwargs.get('defaults', {})

        if defaults and defaults['binary']:
            defaults['binary'] = \
                Base64DecodedValue(kwargs['defaults']['binary'])

        return super(FileDiffDataManager, self).get_or_create(*args, **kwargs)


class DiffSetManager(models.Manager):
    """A custom manager for DiffSet objects.

    This includes utilities for creating diffsets based on the data from form
    uploads, webapi requests, and upstream repositories.
    """

    # Extensions used for intelligent sorting of header files
    # before implementation files.
    HEADER_EXTENSIONS = ["h", "H", "hh", "hpp", "hxx", "h++"]
    IMPL_EXTENSIONS = ["c", "C", "cc", "cpp", "cxx", "c++", "m", "mm", "M"]

    def create_from_upload(self, repository, diff_file, parent_diff_file,
                           diffset_history, basedir, request,
                           base_commit_id=None, save=True):
        """Create a DiffSet from a form upload.

        The diff_file and parent_diff_file parameters are django forms
        UploadedFile objects.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        max_diff_size = siteconfig.get('diffviewer_max_diff_size')

        if max_diff_size > 0:
            if diff_file.size > max_diff_size:
                raise DiffTooBigError(
                    _('The supplied diff file is too large'),
                    max_diff_size=max_diff_size)

            if parent_diff_file and parent_diff_file.size > max_diff_size:
                raise DiffTooBigError(
                    _('The supplied parent diff file is too large'),
                    max_diff_size=max_diff_size)

        if parent_diff_file:
            parent_diff_file_name = parent_diff_file.name
            parent_diff_file_contents = parent_diff_file.read()
        else:
            parent_diff_file_name = None
            parent_diff_file_contents = None

        return self.create_from_data(repository,
                                     diff_file.name,
                                     diff_file.read(),
                                     parent_diff_file_name,
                                     parent_diff_file_contents,
                                     diffset_history,
                                     basedir,
                                     request,
                                     base_commit_id=base_commit_id,
                                     save=save)

    def create_from_data(self, repository, diff_file_name, diff_file_contents,
                         parent_diff_file_name, parent_diff_file_contents,
                         diffset_history, basedir, request,
                         base_commit_id=None, save=True):
        """Create a DiffSet from raw diff data.

        The diff_file_contents and parent_diff_file_contents parameters are
        strings with the actual diff contents.
        """
        from reviewboard.diffviewer.models import FileDiff

        tool = repository.get_scmtool()

        files = list(self._process_files(
            tool.get_parser(diff_file_contents),
            basedir,
            repository,
            base_commit_id,
            request,
            check_existence=(not parent_diff_file_contents)))

        # Parse the diff
        if len(files) == 0:
            raise EmptyDiffError(_("The diff file is empty"))

        # Sort the files so that header files come before implementation.
        files.sort(cmp=self._compare_files, key=lambda f: f.origFile)

        # Parse the parent diff
        parent_files = {}

        # This is used only for tools like Mercurial that use atomic changeset
        # IDs to identify all file versions but not individual file version
        # IDs.
        parent_commit_id = None

        if parent_diff_file_contents:
            diff_filenames = set([f.origFile for f in files])

            parent_parser = tool.get_parser(parent_diff_file_contents)

            # If the user supplied a base diff, we need to parse it and
            # later apply each of the files that are in the main diff
            for f in self._process_files(parent_parser, basedir,
                                         repository, base_commit_id, request,
                                         check_existence=True,
                                         limit_to=diff_filenames):
                parent_files[f.origFile] = f

            # This will return a non-None value only for tools that use
            # commit IDs to identify file versions as opposed to file revision
            # IDs.
            parent_commit_id = parent_parser.get_orig_commit_id()

        diffset = super(DiffSetManager, self).create(
            name=diff_file_name, revision=0,
            basedir=basedir,
            history=diffset_history,
            repository=repository,
            diffcompat=DEFAULT_DIFF_COMPAT_VERSION,
            base_commit_id=base_commit_id)

        if save:
            diffset.save()

        for f in files:
            if f.origFile in parent_files:
                parent_file = parent_files[f.origFile]
                parent_content = parent_file.data
                source_rev = parent_file.origInfo
            else:
                parent_content = ""

                if parent_commit_id and f.origInfo != PRE_CREATION:
                    source_rev = parent_commit_id
                else:
                    source_rev = f.origInfo

            dest_file = os.path.join(basedir, f.newFile).replace("\\", "/")

            if f.deleted:
                status = FileDiff.DELETED
            elif f.moved:
                status = FileDiff.MOVED
            else:
                status = FileDiff.MODIFIED

            filediff = FileDiff(diffset=diffset,
                                source_file=f.origFile,
                                dest_file=dest_file,
                                source_revision=smart_unicode(source_rev),
                                dest_detail=f.newInfo,
                                diff=f.data,
                                parent_diff=parent_content,
                                binary=f.binary,
                                status=status)

            if save:
                filediff.save()

        return diffset

    def _process_files(self, parser, basedir, repository, base_commit_id,
                       request, check_existence=False, limit_to=None):
        tool = repository.get_scmtool()

        for f in parser.parse():
            f2, revision = tool.parse_diff_revision(f.origFile, f.origInfo,
                                                    f.moved)

            if f2.startswith("/"):
                filename = f2
            else:
                filename = os.path.join(basedir, f2).replace("\\", "/")

            if limit_to is not None and filename not in limit_to:
                # This file isn't actually needed for the diff, so save
                # ourselves a remote file existence check and some storage.
                continue

            # FIXME: this would be a good place to find permissions errors
            if (revision != PRE_CREATION and
                revision != UNKNOWN and
                not f.binary and
                not f.deleted and
                not f.moved and
                (check_existence and
                 not repository.get_file_exists(filename, revision,
                                                base_commit_id=base_commit_id,
                                                request=request))):
                raise FileNotFoundError(filename, revision, base_commit_id)

            f.origFile = filename
            f.origInfo = revision

            yield f

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
                if (ext1 in self.HEADER_EXTENSIONS and
                    ext2 in self.IMPL_EXTENSIONS):
                    return -1
                elif (ext1 in self.IMPL_EXTENSIONS and
                      ext2 in self.HEADER_EXTENSIONS):
                    return 1

        return cmp(filename1, filename2)
