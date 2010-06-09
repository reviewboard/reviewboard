import logging
import os
import re
import urllib
import urlparse

try:
    from pysvn import ClientError, Revision, opt_revision_kind
except ImportError:
    pass

from django.utils.translation import ugettext as _

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION, UNKNOWN
from reviewboard.scmtools.errors import SCMError, \
                                        FileNotFoundError, \
                                        UnverifiedCertificateError, \
                                        RepositoryNotFoundError


# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('svn+ssh')


class SVNCertificateFailures:
    """SVN HTTPS certificate failure codes.

    These map to the various SVN HTTPS certificate failures in libsvn.
    """
    NOT_YET_VALID = 1 << 0
    EXPIRED       = 1 << 1
    CN_MISMATCH   = 1 << 2
    UNKNOWN_CA    = 1 << 3


class SVNTool(SCMTool):
    name = "Subversion"
    uses_atomic_revisions = True
    supports_authentication = True
    dependencies = {
        'modules': ['pysvn'],
    }

    AUTHOR_KEYWORDS   = ['Author', 'LastChangedBy']
    DATE_KEYWORDS     = ['Date', 'LastChangedDate']
    REVISION_KEYWORDS = ['Revision', 'LastChangedRevision', 'Rev']
    URL_KEYWORDS      = ['HeadURL', 'URL']
    ID_KEYWORDS       = ['Id']

    # Mapping of keywords to known aliases
    keywords = {
        # Standard keywords
        'Author':              AUTHOR_KEYWORDS,
        'Date':                DATE_KEYWORDS,
        'Revision':            REVISION_KEYWORDS,
        'HeadURL':             URL_KEYWORDS,
        'Id':                  ID_KEYWORDS,

        # Aliases
        'LastChangedBy':       AUTHOR_KEYWORDS,
        'LastChangedDate':     DATE_KEYWORDS,
        'LastChangedRevision': REVISION_KEYWORDS,
        'Rev':                 REVISION_KEYWORDS,
        'URL':                 URL_KEYWORDS,
    }

    def __init__(self, repository):
        self.repopath = repository.path
        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        SCMTool.__init__(self, repository)

        import pysvn
        self.client = pysvn.Client()
        if repository.username:
            self.client.set_default_username(str(repository.username))
        if repository.password:
            self.client.set_default_password(str(repository.password))

        # svnlook uses 'rev 0', while svn diff uses 'revision 0'
        self.revision_re = re.compile("""
            ^(\(([^\)]+)\)\s)?              # creating diffs between two branches
                                            # of a remote repository will insert
                                            # extra "relocation information" into
                                            # the diff.

            (?:\d+-\d+-\d+\ +               # svnlook-style diffs contain a
               \d+:\d+:\d+\ +               # timestamp on each line before the
               [A-Z]+\ +)?                  # revision number.  This here is
                                            # probably a really crappy way to
                                            # express that, but oh well.

            \ *\([Rr]ev(?:ision)?\ (\d+)\)$ # svnlook uses 'rev 0' while svn diff
                                            # uses 'revision 0'
            """, re.VERBOSE)

    def get_file(self, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        try:
            normpath = self.__normalize_path(path)

            # SVN expects to have URLs escaped. Take care to only
            # escape the path part of the URL.
            if self.client.is_url(normpath):
                pathtuple = urlparse.urlsplit(normpath)
                normpath = urlparse.urlunsplit((pathtuple[0],
                                                pathtuple[1],
                                                urllib.quote(pathtuple[2]),
                                                '',''))

            normrev  = self.__normalize_revision(revision)

            data = self.client.cat(normpath, normrev)

            # Find out if this file has any keyword expansion set.
            # If it does, collapse these keywords. This is because SVN
            # will return the file expanded to us, which would break patching.
            keywords = self.client.propget("svn:keywords", normpath, normrev,
                                           recurse=True)

            if normpath in keywords:
                data = self.collapse_keywords(data, keywords[normpath])

            return data
        except ClientError, e:
            stre = str(e)
            if 'File not found' in stre or 'path not found' in stre:
                raise FileNotFoundError(path, revision, str(e))
            elif 'callback_ssl_server_trust_prompt required' in stre:
                home = os.path.expanduser('~')
                raise SCMError(
                    'HTTPS certificate not accepted.  Please ensure that '
                    'the proper certificate exists in %s/.subversion/auth '
                    'for the user that reviewboard is running as.' % home)
            elif 'callback_get_login required' in stre:
                raise SCMError('Login to the SCM server failed.')
            else:
                raise SCMError(e)

    def collapse_keywords(self, data, keyword_str):
        """
        Collapse SVN keywords in string.

        SVN allows for several keywords (such as $Id$ and $Revision$) to
        be expanded, though these keywords are limited to a fixed set
        (and associated aliases) and must be enabled per-file.

        Keywords can take two forms: $Keyword$ and $Keyword::     $
        The latter allows the field to take a fixed size when expanded.

        When we cat a file on SVN, the keywords come back expanded, which
        isn't good for us as we need to diff against the collapsed version.
        This function makes that transformation.
        """
        def repl(m):
            if m.group(2):
                return "$%s::%s$" % (m.group(1), " " * len(m.group(3)))

            return "$%s$" % m.group(1)

        # Get any aliased keywords
        keywords = [keyword
                    for name in keyword_str.split(" ")
                    for keyword in self.keywords.get(name, [])]

        return re.sub(r"\$(%s):(:?)([^\$\n\r]+)\$" % '|'.join(keywords),
                      repl, data)


    def parse_diff_revision(self, file_str, revision_str):
        if revision_str == "(working copy)":
            return file_str, HEAD

        # Binary diffs don't provide revision information, so we set a fake
        # "(unknown)" in the SVNDiffParser. This will never actually appear
        # in SVN diffs.
        if revision_str == "(unknown)":
            return file_str, UNKNOWN

        m = self.revision_re.match(revision_str)
        if not m:
            raise SCMError("Unable to parse diff revision header '%s'" %
                           revision_str)

        relocated_file = m.group(2)
        revision = m.group(3)

        if revision == "0":
            revision = PRE_CREATION

        if relocated_file:
            if not relocated_file.startswith("..."):
                raise SCMError("Unable to parse SVN relocated path '%s'" %
                               relocated_file)

            file_str = "%s/%s" % (relocated_file[4:], file_str)

        return file_str, revision


    def get_filenames_in_revision(self, revision):
        r = self.__normalize_revision(revision)
        logs = self.client.log(self.repopath, r, r, True)

        if len(logs) == 0:
            return []
        elif len(logs) == 1:
            return [f['path'] for f in logs[0]['changed_paths']]
        else:
            assert False

    def get_repository_info(self):
        try:
            info = self.client.info2( self.repopath, recurse=False )
        except ClientError, e:
            raise SCMError(e)

        return {
            'uuid': info[0][1].repos_UUID,
            'root_url': info[0][1].repos_root_URL,
            'url': info[0][1].URL
        }

    def __normalize_revision(self, revision):
        if revision == HEAD:
            r = Revision(opt_revision_kind.head)
        elif revision == PRE_CREATION:
            raise FileNotFoundError('', revision)
        else:
            r = Revision(opt_revision_kind.number, str(revision))

        return r

    def __normalize_path(self, path):
        if path.startswith(self.repopath):
            return path
        elif path[0] == '/':
            return self.repopath + path
        else:
            return self.repopath + "/" + path

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_parser(self, data):
        return SVNDiffParser(data)

    @classmethod
    def check_repository(cls, path, username=None, password=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception
        will be thrown.
        """
        import pysvn

        super(SVNTool, cls).check_repository(path, username, password)

        cert_data = {}

        def ssl_server_trust_prompt(trust_dict):
            cert_data.update(trust_dict)
            return False, 0, False

        client = pysvn.Client()
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        if username:
            client.set_default_username(str(username))

        if password:
            client.set_default_password(str(password))

        try:
            info = client.info2(path, recurse=False)
            logging.debug('SVN: Got repository information for %s: %s' %
                          (path, info))
        except ClientError, e:
            logging.error('SVN: Failed to get repository information '
                          'for %s: %s' % (path, e))

            if 'callback_get_login required' in str(e):
                raise SCMError("Authentication failed") # XXX

            if cert_data:
                failures = cert_data['failures']

                reasons = []

                if failures & SVNCertificateFailures.NOT_YET_VALID:
                    reasons.append(_('The certificate is not yet valid.'))

                if failures & SVNCertificateFailures.EXPIRED:
                    reasons.append(_('The certificate has expired.'))

                if failures & SVNCertificateFailures.CN_MISMATCH:
                    reasons.append(_('The certificate hostname does not '
                                     'match.'))

                if failures & SVNCertificateFailures.UNKNOWN_CA:
                    reasons.append(_('The certificate is not issued by a '
                                     'trusted authority. Use the fingerprint '
                                     'to validate the certificate manually.'))

                raise UnverifiedCertificateError(
                    Certificate(valid_from=cert_data['valid_from'],
                                valid_until=cert_data['valid_until'],
                                hostname=cert_data['hostname'],
                                realm=cert_data['realm'],
                                fingerprint=cert_data['finger_print'],
                                issuer=cert_data['issuer_dname'],
                                failures=reasons))

            raise RepositoryNotFoundError()

    @classmethod
    def accept_certificate(cls, path):
        """Accepts the certificate for the given repository path."""
        import pysvn

        def ssl_server_trust_prompt(trust_dict):
            return True, trust_dict['failures'], True

        dirname = os.path.expanduser('~/.subversion')

        if not os.path.exists(dirname):
            # Make sure the .ssh directory exists.
            try:
                os.mkdir(dirname, 0700)
            except OSError, e:
                raise IOError(_("Unable to create directory %(dirname)s, "
                                "which is needed for the Subversion "
                                "configuration. Create this directory and set "
                                "the web server's user as the the owner.") % {
                    'dirname': dirname,
                })

        client = pysvn.Client()
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        try:
            info = client.info2(path, recurse=False)
        except ClientError, e:
            pass


class SVNDiffParser(DiffParser):
    BINARY_STRING = "Cannot display: file marked as a binary type."

    def __init__(self, data):
        DiffParser.__init__(self, data)

    def parse_special_header(self, linenum, info):
        linenum = super(SVNDiffParser, self).parse_special_header(linenum, info)

        if 'index' in info and linenum != len(self.lines):
            if self.lines[linenum] == self.BINARY_STRING:
                # Skip this and the svn:mime-type line.
                linenum += 2
                info['binary'] = True
                info['origFile'] = info['index']
                info['newFile'] = info['index']

                # We can't get the revision info from this diff header.
                info['origInfo'] = '(unknown)'
                info['newInfo'] = '(working copy)'

        return linenum
