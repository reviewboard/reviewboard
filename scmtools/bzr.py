import calendar
from datetime import datetime, timedelta
import subprocess
import time

from reviewboard.scmtools.core import SCMError, SCMTool, PRE_CREATION


# BZRTool: An interface to Bazaar SCM Tool (http://bazaar-vcs.org/)

class BZRTool(SCMTool):
    # Timestamp format in bzr diffs.
    # This isn't totally accurate: there should be a %z at the end.
    # Unfortunately, strptime() doesn't support %z.
    DIFF_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

    # "bzr diff" indicates that a file is new by setting the old
    # timestamp to the epoch time.
    PRE_CREATION_TIMESTAMP = '1970-01-01 00:00:00 +0000'

    def __init__(self, repository):
        SCMTool.__init__(self, repository)

    def get_file(self, path, revision):
        if revision == BZRTool.PRE_CREATION_TIMESTAMP:
            return ''

        # "bzr -r date:" expects the timestamp to be in local time.
        local_datetime = self._revision_timestamp_to_local(revision)

        p = subprocess.Popen(['bzr', 'cat',
                             '-r', 'date:' + str(local_datetime), self._get_repo_path(path)],
                             stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             close_fds=True)
        contents = p.stdout.read()
        errmsg = p.stderr.read()
        failure = p.wait()

        if failure:
            raise SCMError(errmsg)

        return contents

    def parse_diff_revision(self, file_str, revision_str):
        if revision_str == BZRTool.PRE_CREATION_TIMESTAMP:
            return (file_str, PRE_CREATION)

        return file_str, revision_str

    def get_filenames_in_revision(self, revision):
        local_datetime = self._revision_timestamp_to_local(revision)

        p = subprocess.Popen(['bzr', 'inventory',
                             '-r', 'date:' + str(local_datetime), str(self.repository.path)],
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
        return False

    def _get_repo_path(self, path, basedir=None):
        parts = [self.repository.path.strip("/")]

        if basedir:
            parts.append(basedir.strip("/"))

        parts.append(path.strip("/"))

        return "/".join(parts)

    def _revision_timestamp_to_local(self, timestamp_str):
        """When using a date to ask bzr for a file revision, it expects
        the date to be in local time. So, this function converts a
        timestamp from a bzr diff file to local time.
        """

        timestamp = datetime(*time.strptime(timestamp_str[0:19], BZRTool.DIFF_TIMESTAMP_FORMAT)[0:6])

        # Now, parse the difference to GMT time (such as +0200)
        # If only strptime() supported %z, we wouldn't have to do this manually.
        delta = timedelta(hours=int(timestamp_str[21:23]), minutes=int(timestamp_str[23:25]))
        if timestamp_str[20] == '+':
            timestamp -= delta
        else:
            timestamp += delta

        # convert to local time
        return datetime.fromtimestamp(calendar.timegm(timestamp.timetuple()))

