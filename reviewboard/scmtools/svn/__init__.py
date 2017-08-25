# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import re
import weakref

from django.conf import settings
from django.utils import six
from django.utils.translation import ugettext as _

from reviewboard.diffviewer.diffutils import convert_to_unicode
from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.core import (Branch, Commit, SCMTool, HEAD,
                                       PRE_CREATION, UNKNOWN)
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError,
                                         SCMError,
                                         UnverifiedCertificateError)
from reviewboard.ssh import utils as sshutils


# These will be set later in recompute_svn_backend().
Client = None
has_svn_backend = False


# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('svn+ssh')

sshutils.register_rbssh('SVN_SSH')


class SVNCertificateFailures:
    """SVN HTTPS certificate failure codes.

    These map to the various SVN HTTPS certificate failures in libsvn.
    """
    NOT_YET_VALID = 1 << 0
    EXPIRED = 1 << 1
    CN_MISMATCH = 1 << 2
    UNKNOWN_CA = 1 << 3


class SVNTool(SCMTool):
    name = "Subversion"
    supports_post_commit = True
    dependencies = {
        'modules': [],  # This will get filled in later in
                        # recompute_svn_backend()
    }

    COMMITS_PAGE_LIMIT = 31

    def __init__(self, repository):
        self.repopath = repository.path
        if self.repopath[-1] == '/':
            self.repopath = self.repopath[:-1]

        super(SVNTool, self).__init__(repository)

        if repository.local_site:
            local_site_name = repository.local_site.name
        else:
            local_site_name = None

        credentials = repository.get_credentials()

        self.config_dir, self.client = \
            self.build_client(self.repopath,
                              credentials['username'], credentials['password'],
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
        self.client.set_ssl_server_trust_prompt(
            lambda trust_dict:
            SVNTool._ssl_server_trust_prompt(trust_dict, repository_ref()))

        # 'svn diff' produces patches which have the revision string localized
        # to their system locale. This is a little ridiculous, but we have to
        # deal with it because not everyone uses RBTools.
        #
        # svnlook diff creates lines like
        # '2016-05-12 12:30:05 UTC (rev 1234)'
        #
        # whereas svn diff creates lines like
        # '(Revision 94754)'
        # '        (.../branches/product-2.0) (revision 321)'
        # '        (.../trunk)     (nonexistent)'
        #
        # So we need to form a regex to match relocation information and the
        # revision number. Subversion >=1.9 adds the 'nonexistent' revision
        # string.
        self.revision_re = re.compile('''
            ^(\(([^\)]+)\)\s)?      # creating diffs between two branches of a
                                    # remote repository will insert extra
                                    # "relocation information" into the diff.

            (?:\d+-\d+-\d+\ +       # svnlook-style diffs contain a timestamp
               \d+:\d+:\d+\ +       # on each line before the revision number.
               [A-Z]+\ +)?          # This here is probably a really crappy
                                    # to express that, but oh well.

            \ *\(
             (                      # - svn 1.9 nonexistent revision indicator
              nonexistent|          # English
              nicht\ existent|      # German
              不存在的|             # Simplified Chinese
              (?:

                revisão|            # Brazilian Portuguese
                [Rr]ev(?:ision)?|   # English, German

                                    # - svnlook uses 'rev 0' while svn diff
                                    #   uses 'revision 0'
                révision|           # French
                revisione|          # Italian
                リビジョン|         # Japanese
                리비전|             # Korean
                revisjon|           # Norwegian
                wersja|             # Polish
                版本|               # Simplified Chinese
                revisión:           # Spanish
              )\ (\d+)              # - the revision number
              )
            \)$
            ''', re.VERBOSE)

        # 'svn diff' also localises the (working copy) string to the system
        # locale.
        self.working_copy_re = re.compile(r'''
            ^\((?:
                cópia\ de\ trabalho|   # Brazilian Portuguese
                working\ copy|         # English
                copie\ de\ travail|    # French
                Arbeitskopie|          # German
                copia\ locale|         # Italian
                作業コピー|            # Japanese
                작업\ 사본|            # Korean
                arbeidskopi|           # Norweigan
                kopia\ robocza|        # Polish
                工作副本|              # Simplified Chinese
                copia\ de\ trabajo     # Spanish
            )\)$
        ''', re.VERBOSE)

    def get_file(self, path, revision=HEAD, **kwargs):
        return self.client.get_file(path, revision)

    def get_keywords(self, path, revision=HEAD):
        return self.client.get_keywords(path, revision)

    def get_branches(self):
        """Returns a list of branches.

        This assumes the standard layout in the repository.
        """
        results = []

        try:
            root_dirents = self.client.list_dir('/')
        except Exception as e:
            raise self.normalize_error(e)

        default = True
        if 'trunk' in root_dirents:
            # Looks like the standard layout. Adds trunk and any branches.
            trunk = root_dirents['trunk']
            results.append(self._create_branch_from_dirent(
                'trunk', trunk, default=True))
            default = False

        if 'branches' in root_dirents:
            try:
                dirents = self.client.list_dir('branches')

                results += [
                    self._create_branch_from_dirent(name, dirents[name])
                    for name in sorted(six.iterkeys(dirents))
                ]
            except Exception as e:
                raise self.normalize_error(e)

        # Add anything else from the root of the repository. This is a
        # catch-all for repositories which do not use the standard layout, and
        # for those that do, will include any additional top-level directories
        # that people may have.
        for name in sorted(six.iterkeys(root_dirents)):
            if name not in ('trunk', 'branches'):
                results.append(self._create_branch_from_dirent(
                    name, root_dirents[name], default))
                default = False

        return results

    def get_commits(self, branch=None, start=None):
        """Return a list of commits."""
        try:
            commits = self.client.get_log(branch or '/',
                                          start=start,
                                          limit=self.COMMITS_PAGE_LIMIT,
                                          limit_to_path=False)
        except Exception as e:
            raise self.normalize_error(e)

        results = []

        # We fetch one more commit than we care about, because the entries in
        # the svn log doesn't include the parent revision.
        for i in range(len(commits) - 1):
            commit = commits[i]
            parent = commits[i + 1]
            results.append(self._build_commit(commit, parent['revision']))

        # If there were fewer than the requested number of commits fetched,
        # also include the last one in the list so we don't leave off the
        # initial revision.
        if len(commits) < self.COMMITS_PAGE_LIMIT:
            commit = commits[-1]
            results.append(self._build_commit(commit))

        return results

    def get_change(self, revision):
        """Get an individual change.

        This returns a Commit object containing the details of the commit.
        """
        revision = int(revision)

        commits = self.client.get_log('/', start=revision, limit=2)

        commit = commits[0]
        message = commit.get('message', b'').decode('utf-8', 'replace')
        author_name = commit.get('author', b'').decode('utf-8', 'replace')
        date = commit['date'].isoformat()

        if len(commits) > 1:
            base_revision = commits[1]['revision']
        else:
            base_revision = 0

        try:
            enc, diff = convert_to_unicode(
                self.client.diff(base_revision, revision),
                self.repository.get_encoding_list())
        except Exception as e:
            raise self.normalize_error(e)

        commit = Commit(author_name, six.text_type(revision), date,
                        message, six.text_type(base_revision))
        commit.diff = diff

        return commit

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
                return self.client.collapse_keywords(patch, keywords)

        return patch

    def parse_diff_revision(self, file_str, revision_str, *args, **kwargs):
        # Some diffs have additional tabs between the parts of the file
        # revisions
        revision_str = revision_str.strip()

        if self.working_copy_re.match(revision_str):
            return file_str, HEAD

        # "(revision )" is generated by a few weird tools (like IntelliJ). If
        # in the +++ line of the diff, it means HEAD, and in the --- line, it
        # means PRE_CREATION. Since the more important use case is parsing the
        # source revision, we treat it as a new file. See bugs 1937 and 2632.
        if revision_str == "(revision )":
            return file_str, PRE_CREATION

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
        revision = m.group(4)

        # group(3) holds the revision string in braces, like '(revision 4)'
        # group(4) only matches the revision number, which might by None when
        # 'nonexistent' is given as the revision string
        if revision in (None, '0'):
            revision = PRE_CREATION

        if relocated_file:
            if not relocated_file.startswith("..."):
                raise SCMError("Unable to parse SVN relocated path '%s'" %
                               relocated_file)

            file_str = "%s/%s" % (relocated_file[4:], file_str)

        return file_str, revision

    def get_repository_info(self):
        return self.client.repository_info

    def get_fields(self):
        return ['basedir', 'diff_path']

    def get_parser(self, data):
        return SVNDiffParser(data)

    def _create_branch_from_dirent(self, name, dirent, default=False):
        return Branch(
            id=dirent['path'].strip('/'),
            name=name,
            commit=dirent['created_rev'],
            default=default)

    def _build_commit(self, data, parent=''):
        date = data.get('date', '')

        if date:
            date = date.isoformat()

        return Commit(
            data.get('author', ''),
            data['revision'],
            date,
            data.get('message', ''),
            parent)

    @classmethod
    def normalize_error(cls, e):
        if 'callback_get_login required' in six.text_type(e):
            return AuthenticationError(
                msg='Authentication failed when talking to the Subversion '
                    'repository')
        else:
            return SCMError(e)

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

    @staticmethod
    def on_ssl_failure(e, path, cert_data):
        logging.error('SVN: Failed to get repository information '
                      'for %s: %s' % (path, e))

        error = SVNTool.normalize_error(e)

        if isinstance(error, AuthenticationError):
            raise error

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

        if path.startswith('https://'):
            client = cls.build_client(path, username, password,
                                      local_site_name=local_site_name)[1]
            client.accept_ssl_certificate(path, cls.on_ssl_failure)

    @classmethod
    def accept_certificate(cls, path, username=None, password=None,
                           local_site_name=None, certificate=None):
        """Accepts the certificate for the given repository path."""
        client = cls.build_client(path, username, password,
                                  local_site_name=local_site_name)[1]

        return client.accept_ssl_certificate(path)

    @classmethod
    def build_client(cls, repopath, username=None, password=None,
                     local_site_name=None):
        if not has_svn_backend:
            raise ImportError(_(
                'SVN integration requires either subvertpy or pysvn'))
        config_dir = os.path.join(os.path.expanduser('~'), '.subversion')

        if local_site_name:
            # LocalSites can have their own Subversion config, used for
            # per-LocalSite SSH keys.
            config_dir = cls._prepare_local_site_config_dir(local_site_name)
        elif not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

        client = Client(config_dir, repopath, username, password)

        return config_dir, client

    @classmethod
    def _create_subversion_dir(cls, config_dir):
        try:
            os.mkdir(config_dir, 0o700)
        except OSError:
            raise IOError(
                _("Unable to create directory %(dirname)s, which is needed "
                  "for the Subversion configuration. Create this directory "
                  "and set the web server's user as the the owner.")
                % {'dirname': config_dir})

    @classmethod
    def _prepare_local_site_config_dir(cls, local_site_name):
        config_dir = os.path.join(os.path.expanduser('~'), '.subversion')

        if not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

        config_dir = os.path.join(config_dir, local_site_name)

        if not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

            with open(os.path.join(config_dir, 'config'), 'w') as fp:
                fp.write('[tunnels]\n')
                fp.write('ssh = rbssh --rb-local-site=%s\n' % local_site_name)

        return config_dir


class SVNDiffParser(DiffParser):
    BINARY_STRING = b"Cannot display: file marked as a binary type."
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
        try:
            is_property_change = (
                self.lines[linenum].startswith(b'--- (') and
                self.lines[linenum + 1].startswith(b'+++ (') and
                self.lines[linenum + 2].startswith(b'Property changes on:')
            )
        except IndexError:
            is_property_change = False

        if is_property_change:
            # Subversion diffs with property changes have no really
            # parsable format. The content of a property can easily mimic
            # the property change headers. So we can't rely upon it, and
            # can't easily display it. Instead, skip it, so it at least
            # won't break diffs.
            info['skip'] = True
            linenum += 4

            return linenum
        else:
            # Handle deleted empty files.
            try:
                if info['index'].endswith(b'\t(deleted)'):
                    info['deleted'] = True
            except KeyError:
                # There's no index information.
                pass

            return super(SVNDiffParser, self).parse_diff_header(linenum, info)

    def parse_special_header(self, linenum, info):
        if (linenum + 1 < len(self.lines) and
            self.lines[linenum] == b'Index:'):
            # This is an empty Index: line. This might mean we're parsing
            # a property change.
            return linenum + 2

        linenum = super(SVNDiffParser, self).parse_special_header(
            linenum, info)

        try:
            file_index = info['index']
        except KeyError:
            return linenum

        try:
            if self.lines[linenum] == self.BINARY_STRING:
                # Skip this and the svn:mime-type line.
                linenum += 2

                info.update({
                    'binary': True,
                    'origFile': file_index,
                    'newFile': file_index,

                    # We can't get the revision info from this diff header.
                    'origInfo': '(unknown)',
                    'newInfo': '(working copy)',
                })
        except IndexError:
            pass

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
        try:
            if (self.lines[linenum] == b'' and
                self.lines[linenum + 1].startswith(b'Property changes on:')):
                # Skip over the next 3 lines (blank, "Property changes on:",
                # and the "__________" divider.
                info['skip'] = True
                linenum += 3
        except IndexError:
            pass

        return linenum


def recompute_svn_backend():
    """Recomputes the SVNTool client backend to use.

    Normally, this is only called once, but it may be used to reset the
    backend for use in testing.
    """
    global Client
    global has_svn_backend

    Client = None
    has_svn_backend = False
    required_module = None

    for backend_path in settings.SVNTOOL_BACKENDS:
        try:
            mod = __import__(six.binary_type(backend_path),
                             fromlist=['Client', 'has_svn_backend'])

            # Check that this is a valid SVN backend.
            if (not hasattr(mod, 'has_svn_backend') or
                not hasattr(mod, 'Client')):
                logging.error('Attempted to load invalid SVN backend %s',
                              backend_path)
                continue

            has_svn_backend = mod.has_svn_backend

            # We want either the winning SVN backend or the first one to show
            # up in the required module dependencies list.
            if has_svn_backend or not required_module:
                SVNTool.dependencies['modules'] = [mod.Client.required_module]

            if has_svn_backend:
                # We found a suitable backend.
                logging.info('Using %s backend for SVN', backend_path)
                Client = mod.Client
                break
        except ImportError:
            logging.error('Unable to load SVN backend %s',
                          backend_path, exc_info=1)

recompute_svn_backend()
