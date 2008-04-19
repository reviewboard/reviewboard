from datetime import datetime, timedelta
import subprocess
import time

from reviewboard.scmtools.core import SCMError, SCMTool


# BZRTool: An interface to Bazaar SCM Tool (http://bazaar-vcs.org/)

class BZRTool(SCMTool):
    def __init__(self, repository):
        SCMTool.__init__(self, repository)

    def get_file(self, path, revision=0):
        p = subprocess.Popen(['bzr', 'cat',
                              '-r', str(revision), str(self.repository.path) + '/' + path],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=True)
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        return contents

    def parse_diff_revision(self, file_str, revision_str):

        # A Bazaar diff contains only timestamps, so we try
        # to deduce the actual revision number based on that.

        p = subprocess.Popen(['bzr', 'log',
                             str(self.repository.path) + '/' + file_str],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=True)
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        # A log entry has, for example, the following lines (among others):
        # revno: 1
        # timestamp: Thu 2008-03-20 18:25:34 +0200

        revision_timestamp = self.__parse_timestamp(revision_str)
        revision = 0 # If no revision is found, use 0
        current_revision = 0 # Temporary per log entry
        lines = contents.splitlines()
        for line in lines:
            values=line.split(':', 1);
            if values[0] == 'revno':
                current_revision = values[1].strip()
            elif values[0] == 'timestamp':
                timestamp = self.__parse_timestamp(values[1].strip()[4:])
                if timestamp == revision_timestamp:
                    revision = current_revision

        if revision == 0:
            raise SCMError("%s: no revision found for timestamp '%s'." %
                           (file_str, revision_str))

        return file_str, str(revision)

    def get_filenames_in_revision(self, revision):
        p = subprocess.Popen(['bzr', 'inventory',
                              '-r', str(revision), str(self.repository.path)],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=True)
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        return contents.strip().splitlines();

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_diffs_use_absolute_paths(self):
        return True

    def __parse_timestamp(self, timestamp_str):
        # The timestamp format is: YYYY-MM-DD HH:MM:SS +HHMM
        timestamp = datetime(*time.strptime(timestamp_str[0:19], '%Y-%m-%d %H:%M:%S')[0:6])

        # Now, parse the difference to GMT time (such as +0200)
        delta = timedelta(hours=int(timestamp_str[21:23]), minutes=int(timestamp_str[23:25]))
        if timestamp_str[20] == '+':
            timestamp -= delta
        else:
            timestamp += delta

        return timestamp
