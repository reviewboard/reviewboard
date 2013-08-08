# -*- coding: utf-8 -*-
import logging
import os
import re
import urllib
import urlparse
import weakref

try:
    from pysvn import ClientError, Revision, opt_revision_kind
except ImportError:
    pass

from django.utils.translation import ugettext as _

from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.core import SCMTool, HEAD, PRE_CREATION, UNKNOWN
from reviewboard.scmtools.errors import AuthenticationError, \
                                        FileNotFoundError, \
                                        RepositoryNotFoundError, \
                                        SCMError, \
                                        UnverifiedCertificateError
from reviewboard.ssh import utils as sshutils


# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('svn+ssh')

sshutils.register_rbssh('SVN_SSH')


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
    HEADER_KEYWORDS   = ['Header']

    # Mapping of keywords to known aliases
    keywords = {
        # Standard keywords
        'Author':              AUTHOR_KEYWORDS,
        'Date':                DATE_KEYWORDS,
        'Revision':            REVISION_KEYWORDS,
        'HeadURL':             URL_KEYWORDS,
        'Id':                  ID_KEYWORDS,
        'Header':              HEADER_KEYWORDS,

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

        super(SVNTool, self).__init__(repository)

        if repository.local_site:
            local_site_name = repository.local_site.name
        else:
            local_site_name = None

        self.config_dir, self.client = \
            self.build_client(repository.username, repository.password,
                              local_site_name)

        # If we assign a function to the pysvn Client that accesses anything
        # bound to SVNClient, it'll end up keeping a reference and a copy of
        # the function for every instance that gets created, and will never
        # let go. This will cause a rather large memory leak.
        #
        # The solution is to access a weakref instead. The weakref will
        # reference the repository, but it will safely go away when needed.
        # The function we pass can access that without causing the leaks
        repository_ref = weakref.ref(repository)
        self.client.callback_ssl_server_trust_prompt = \
            lambda trust_dict: \
            SVNTool._ssl_server_trust_prompt(trust_dict, repository_ref())

        # 'svn diff' produces patches which have the revision string localized
        # to their system locale. This is a little ridiculous, but we have to
        # deal with it because not everyone uses post-review.
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

            \ *\((?:
                [Rr]ev(?:ision)?|           # english - svnlook uses 'rev 0'
                                            #           while svn diff uses
                                            #           'revision 0'
                revisión:|                  # espanol
                révision|                   # french
                revisione|                  # italian
                リビジョン|                 # japanese
                리비전|                     # korean
                revisjon|                   # norwegian
                wersja|                     # polish
                revisão|                    # brazilian portuguese
                版本                        # simplified chinese
            )\ (\d+)\)$
            """, re.VERBOSE)

    def _do_on_path(self, cb, path, revision=HEAD):
        if not path:
            raise FileNotFoundError(path, revision)

        try:
            normpath = self.__normalize_path(path)

            # SVN expects to have URLs escaped. Take care to only
            # escape the path part of the URL.
            if self.client.is_url(normpath):
                pathtuple = urlparse.urlsplit(normpath)
                path = pathtuple[2]
                if isinstance(path, unicode):
                    path = path.encode('utf-8', 'ignore')
                normpath = urlparse.urlunsplit((pathtuple[0],
                                                pathtuple[1],
                                                urllib.quote(path),
                                                '',''))

            normrev = self.__normalize_revision(revision)
            return cb(normpath, normrev)

        except ClientError, e:
            stre = str(e)
            if 'File not found' in stre or 'path not found' in stre:
                raise FileNotFoundError(path, revision, detail=str(e))
            elif 'callback_ssl_server_trust_prompt required' in stre:
                raise SCMError(
                    'HTTPS certificate not accepted.  Please ensure that '
                    'the proper certificate exists in %s '
                    'for the user that reviewboard is running as.'
                    % os.path.join(self.config_dir, 'auth'))
            elif 'callback_get_login required' in stre:
                raise AuthenticationError(msg='Login to the SCM server failed.')
            else:
                raise SCMError(e)

    def get_file(self, path, revision=HEAD):
        def get_file_data(normpath, normrev):
            data = self.client.cat(normpath, normrev)

            # Find out if this file has any keyword expansion set.
            # If it does, collapse these keywords. This is because SVN
            # will return the file expanded to us, which would break patching.
            keywords = self.client.propget("svn:keywords", normpath, normrev,
                                           recurse=True)
            if normpath in keywords:
                data = self.collapse_keywords(data, keywords[normpath])

            return data

        return self._do_on_path(get_file_data, path, revision)

    def get_keywords(self, path, revision=HEAD):
        def get_file_keywords(normpath, normrev):
            keywords = self.client.propget("svn:keywords", normpath, normrev,
                                           recurse=True)
            return keywords.get(normpath)

        return self._do_on_path(get_file_keywords, path, revision)

    def normalize_patch(self, patch, filename, revision=HEAD):
        """
	If using Subversion, we need not only contract keywords in file, but
        also in the patch. Otherwise, if a file with expanded keyword somehow
	ends up in the repository (e.g. by first checking in a file without
	svn:keywords and then setting svn:keywords in the repository), RB
	won't be able to apply a patch to such file.
	"""
        if revision != PRE_CREATION:
            keywords = self.get_keywords(filename, revision)

	    if keywords:
                return self.collapse_keywords(patch, keywords)

        return patch

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
                    for name in re.split(r'\W+', keyword_str)
                    for keyword in self.keywords.get(name, [])]

        return re.sub(r"\$(%s):(:?)([^\$\n\r]*)\$" % '|'.join(keywords),
                      repl, data)


    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        # Some diffs have additional tabs between the parts of the file
        # revisions
        revision_str = revision_str.strip()

        # The "(revision )" is generated by IntelliJ and has the same
        # meaning as "(working copy)". See bug 1937.
        if revision_str in ("(working copy)", "(revision )"):
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
        elif path.startswith('//'):
            return self.repopath + path[1:]
        elif path[0] == '/':
            return self.repopath + path
        else:
            return self.repopath + "/" + path

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_parser(self, data):
        return SVNDiffParser(data)

    @classmethod
    def _ssl_server_trust_prompt(cls, trust_dict, repository):
        """Callback for SSL cert verification.

        This will be called when accessing a repository with an SSL cert.
        We will look up a matching cert in the database and see if it's
        accepted.
        """
        saved_cert = repository.extra_data.get('cert', {})
        cert = trust_dict.copy()
        del cert['failures']

        return saved_cert == cert, trust_dict['failures'], False

    @classmethod
    def check_repository(cls, path, username=None, password=None,
                         local_site_name=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception
        will be thrown.
        """
        super(SVNTool, cls).check_repository(path, username, password,
                                             local_site_name)

        cert_data = {}

        def ssl_server_trust_prompt(trust_dict):
            cert_data.update(trust_dict)
            return False, 0, False

        config_dir, client = cls.build_client(username, password,
                                              local_site_name)
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        try:
            info = client.info2(path, recurse=False)
            logging.debug('SVN: Got repository information for %s: %s' %
                          (path, info))
        except ClientError, e:
            logging.error('SVN: Failed to get repository information '
                          'for %s: %s' % (path, e))

            if 'callback_get_login required' in str(e):
                raise AuthenticationError(msg="Authentication failed")

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
    def accept_certificate(cls, path, local_site_name=None, certificate=None):
        """Accepts the certificate for the given repository path."""
        cert = {}

        def ssl_server_trust_prompt(trust_dict):
            cert.update(trust_dict.copy())
            del cert['failures']
            return True, trust_dict['failures'], True

        client = cls.build_client(local_site_name=local_site_name)[1]
        client.callback_ssl_server_trust_prompt = ssl_server_trust_prompt

        try:
            client.info2(path, recurse=False)
        except ClientError:
            pass

        return cert

    @classmethod
    def build_client(cls, username=None, password=None, local_site_name=None):
        config_dir = os.path.join(os.path.expanduser('~'), '.subversion')

        if local_site_name:
            # LocalSites can have their own Subversion config, used for
            # per-LocalSite SSH keys.
            config_dir = cls._prepare_local_site_config_dir(local_site_name)
        elif not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

        import pysvn
        client = pysvn.Client(config_dir)

        if username:
            client.set_default_username(str(username))

        if password:
            client.set_default_password(str(password))

        return config_dir, client

    @classmethod
    def _create_subversion_dir(cls, config_dir):
        try:
            os.mkdir(config_dir, 0700)
        except OSError:
            raise IOError(_("Unable to create directory %(dirname)s, "
                            "which is needed for the Subversion "
                            "configuration. Create this directory and set "
                            "the web server's user as the the owner.") % {
                'dirname': config_dir,
            })

    @classmethod
    def _prepare_local_site_config_dir(cls, local_site_name):
        config_dir = os.path.join(os.path.expanduser('~'), '.subversion')

        if not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

        config_dir = os.path.join(config_dir, local_site_name)

        if not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

            fp = open(os.path.join(config_dir, 'config'), 'w')
            fp.write('[tunnels]\n')
            fp.write('ssh = rbssh --rb-local-site=%s\n' % local_site_name)
            fp.close()

        return config_dir


class SVNDiffParser(DiffParser):
    BINARY_STRING = "Cannot display: file marked as a binary type."
    PROPERTY_PATH_RE = re.compile(r'Property changes on: (.*)')

    def parse_diff_header(self, linenum, info):
        # We're looking for a SVN property change for SVN < 1.7.
        #
        # There's going to be at least 5 lines left:
        # 1) --- (blah)
        # 2) +++ (blah)
        # 3) Property changes on: <path>
        # 4) -----------------------------------------------------
        # 5) Modified: <propname>
        if (linenum + 4 < len(self.lines) and
            self.lines[linenum].startswith('--- (') and
            self.lines[linenum + 1].startswith('+++ (') and
            self.lines[linenum + 2].startswith('Property changes on:')):
            # Subversion diffs with property changes have no really
            # parsable format. The content of a property can easily mimic
            # the property change headers. So we can't rely upon it, and
            # can't easily display it. Instead, skip it, so it at least
            # won't break diffs.
            info['skip'] = True
            linenum += 4

            return linenum
        else:
            return super(SVNDiffParser, self).parse_diff_header(linenum, info)

    def parse_special_header(self, linenum, info):
        if (linenum + 1 < len(self.lines) and
            self.lines[linenum] == 'Index:'):
            # This is an empty Index: line. This might mean we're parsing
            # a property change.
            return linenum + 2

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

    def parse_after_headers(self, linenum, info):
        # We're looking for a SVN property change for SVN 1.7+.
        #
        # This differs from SVN property changes in older versions of SVN
        # in a couple ways:
        #
        # 1) The ---, +++, and Index: lines have actual filenames.
        #    Because of this, we won't hit the case in parse_diff_header
        #    above.
        # 2) There's an actual section per-property, so we could parse these
        #    out in a usable form. We'd still need a way to display that
        #    sanely, though.
        if (self.lines[linenum] == '' and
            linenum + 2 < len(self.lines) and
            self.lines[linenum + 1].startswith('Property changes on:')):
            # Skip over the next 3 lines (blank, "Property changes on:", and
            # the "__________" divider.
            info['skip'] = True
            linenum += 3

        return linenum
