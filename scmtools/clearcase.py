import os
import subprocess

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION
from reviewboard.scmtools.errors import SCMError, FileNotFoundError


class ClearCaseTool(SCMTool):
    def __init__(self, repository):
        self.repopath = repository.path

        SCMTool.__init__(self, repository)

        self.client = ClearCaseClient(self.repopath)
        self.uses_atomic_revisions = False

    def unextend_path(self, path):
        # ClearCase extended path is kind of unreadable on the diff viewer.
        # For example:
        #     /vobs/comm/@@/main/122/network/@@/main/55/sntp/
        #     @@/main/4/src/@@/main/1/sntp.c/@@/main/8
        # This function converts the extended path to regular path:
        #     /vobs/comm/network/sntp/sntp.c
        fpath = ['vobs']
        path = os.path.normpath(path)
        splpath = path.split("@@")
        source_rev = splpath.pop()
        for splp in splpath:
            spsplp = splp.split("/")
            fname = spsplp.pop()
            if not fname:
                fname = spsplp.pop()
            fpath.append(fname)

        file_str = '/'.join(fpath)
        return (source_rev, '/' + file_str.rstrip('/'))

    def get_file(self, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        return self.client.cat_file(self.adjust_path(path), revision)

    def parse_diff_revision(self, file_str, revision_str):
        self.orifile = file_str;
        if revision_str == "PRE-CREATION":
            return file_str, PRE_CREATION

        spl = file_str.split("@@")
        return file_str, spl.pop().lstrip('/\\')

    def get_filenames_in_revision(self, revision):
        r = self.__normalize_revision(revision)
        logs = self.client.log(self.repopath, r, r, True)

        if len(logs) == 0:
            return []
        elif len(logs) == 1:
            return [f['path'] for f in logs[0]['changed_paths']]
        else:
            assert False

    def adjust_path(self, path):
        # This function adjust the given path to the
        #   linux path used on the server
        drive, elem_path = os.path.splitdrive(path)
        if drive:
           # Windows like path starting with <drive letter>:\
           tofind = "\\"
           if elem_path.find('\\') == -1:
               tofind = "//"
           # Remove the heading element until the remaining
           #   path is a valid path into the repository path.
           while not (os.path.exists(self.repopath + elem_path)):
               elem_path = elem_path[elem_path.find(tofind):]
           elem_path = os.path.normpath(elem_path)
        else:
           # In this case it is already a linux path
           # Get everything after the vobs/
           elem_path = elem_path[elem_path.rindex("vobs/")+5:]

        # Add the repository to the file path and return.
        return os.path.join(self.repopath, elem_path)

    def __normalize_revision(self, revision):
        return revision

    def __normalize_path(self, path):
        if path.startswith(self.repopath):
            return path
        else:
            return os.path.join(self.repopath, path)

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_parser(self, data):
        return ClearCaseDiffParser(data)


class ClearCaseDiffParser(DiffParser):
    BINARY_STRING = "Cannot display: file marked as a binary type."

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_special_header(self, linenum, info):
        linenum = super(ClearCaseDiffParser, self).parse_special_header(linenum, info)

        if ('index' in info and
            self.lines[linenum] == self.BINARY_STRING) :
                # Skip this and the svn:mime-type line.
                linenum += 2
                info['binary'] = True
                info['origFile'] = info['index']
                info['newFile'] = info['index']

                # We can't get the revision info from this diff header.
                info['origInfo'] = '(unknown)'
                info['newInfo'] = '(working copy)'

        return linenum

class ClearCaseClient:
    def __init__(self, path):
        self.path = path

    def cat_file(self, filename, revision):
        p = subprocess.Popen(
            ['cat', filename],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE, close_fds=True
        )
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if not failure:
            return contents

        if errmsg.startswith("fatal: Not a valid object name"):
            raise FileNotFoundError(filename)
        else:
            raise SCMError(errmsg)

