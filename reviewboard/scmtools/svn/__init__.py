"""Support for Subversion repositories."""

from __future__ import annotations

import logging
import os
import re
import weakref
from enum import IntEnum
from importlib import import_module
from typing import (Any, Dict, List, Mapping, Optional, Sequence, Tuple,
                    TYPE_CHECKING, Type, Union, cast)
from urllib.parse import urlparse

from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext as _
from typing_extensions import Final, TypedDict

from reviewboard import get_manual_url
from reviewboard.admin.server import get_data_dir
from reviewboard.diffviewer.parser import DiffParser
from reviewboard.scmtools.certs import Certificate
from reviewboard.scmtools.core import (Branch, Commit, SCMTool, HEAD,
                                       PRE_CREATION, UNKNOWN)
from reviewboard.scmtools.errors import (AuthenticationError,
                                         RepositoryNotFoundError,
                                         SCMError,
                                         UnverifiedCertificateError)
from reviewboard.scmtools.forms import StandardSCMToolRepositoryForm
from reviewboard.scmtools.svn.utils import (collapse_svn_keywords,
                                            has_expanded_svn_keywords)
from reviewboard.ssh import utils as sshutils

if TYPE_CHECKING:
    from reviewboard.scmtools.core import Revision, RevisionID
    from reviewboard.scmtools.models import Repository
    from reviewboard.scmtools.svn.base import (Client,
                                               SVNDirEntry,
                                               SVNLogEntry)


logger = logging.getLogger(__name__)


# These will be set later in recompute_svn_backend().
_SVNClientBackend: Optional[Type[Client]] = None
has_svn_backend: bool = False


# Register these URI schemes so we can handle them properly.
sshutils.ssh_uri_schemes.append('svn+ssh')

sshutils.register_rbssh('SVN_SSH')


class SVNCertificateFailures(IntEnum):
    """SVN HTTPS certificate failure codes.

    These map to the various SVN HTTPS certificate failures in libsvn.
    """

    #: The certificate is not yet valid.
    NOT_YET_VALID = 1 << 0

    #: The certificate has expired.
    EXPIRED = 1 << 1

    #: The certificate does not match the hostname.
    CN_MISMATCH = 1 << 2

    #: The certificate is self-signed or signed by an untrusted authority.
    UNKNOWN_CA = 1 << 3


class RawSSLTrustDict(TypedDict):
    """A dictionary of SSL trust data to verify.

    For details, see
    https://pysvn.sourceforge.io/Docs/pysvn_prog_ref.html#pysvn_client_callback_ssl_server_trust_prompt

    Version Added:
        6.0
    """

    #: The bitmask of failures:
    #:
    #: Type:
    #:     int
    failures: int

    #: The SSL certificate fingerprint.
    finger_print: str

    #: The hostname that served the certificate.
    #:
    #: Type:
    #:     str
    hostname: str

    #: The issuer of the certificate.
    #:
    #: Type:
    #:     str
    issuer_dname: str

    #: The realm serving the certificate.
    #:
    #: Type:
    #:     str
    realm: str

    #: The start of the certificate validity period.
    #:
    #: This is in :term:`ISO8601 format`.
    #:
    #: Type:
    #:     str
    valid_from: str

    #: The end of the certificate validity period.
    #:
    #: This is in :term:`ISO8601 format`.
    #:
    #: Type:
    #:     str
    valid_until: str


class SVNRepositoryForm(StandardSCMToolRepositoryForm):
    """Form for editing SVN repositories.

    Version Added:
        6.0
    """

    def clean(self) -> Dict[str, Any]:
        """Perform validation on the form.

        Returns:
            dict:
            The cleaned form data.
        """
        cleaned_data = super().clean()
        assert cleaned_data is not None

        path = cleaned_data.get('path', '')

        if path:
            url_parts = urlparse(path)

            if not url_parts.scheme:
                self.add_error('path', _(
                    'The path to the SVN repository must be a URL. To specify '
                    'a local repository, use a file:// URL.'))

        return cleaned_data


class SVNTool(SCMTool):
    """Repository support for Subversion.

    Subversion is an open source centralized source code management system
    maintained by the Apache Software Foundation. It supports tagging and
    branching, atomic commits, full remote communication, file/directory-level
    metadata, large binary files, and more.

    Review Board uses Subversion's native diff format. This has had some
    changes and inconsistencies over time, but is otherwise a fairly
    comprehensive diff format.
    """

    scmtool_id = 'subversion'
    name = 'Subversion'
    supports_post_commit = True
    dependencies = {
        # This will get filled in later in recompute_svn_backend()
        'modules': [],
    }
    repository_form = SVNRepositoryForm

    #: The number of commits to retrieve per page.
    COMMITS_PAGE_LIMIT: Final[int] = 31

    ######################
    # Instance variables #
    ######################

    #: The configured Subversion client backend.
    #:
    #: Type:
    #:     reviewboard.scmtools.svn.base.Client
    client: Client

    def __init__(
        self,
        repository: Repository,
    ) -> None:
        """Initialize the Subversion support.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The Subversion repository that this tool will communicate with.
        """
        repopath = repository.path

        if repopath.endswith('/'):
            repopath = repopath.rstrip('/')

        super().__init__(repository=repository)

        if repository.local_site:
            local_site_name = repository.local_site.name
        else:
            local_site_name = None

        credentials = repository.get_credentials()

        client = self.build_client(repo_path=repopath,
                                   username=credentials['username'],
                                   password=credentials['password'],
                                   local_site_name=local_site_name)
        self.client = client

        # If we assign a function to the pysvn Client that accesses anything
        # bound to SVNClient, it'll end up keeping a reference and a copy of
        # the function for every instance that gets created, and will never
        # let go. This will cause a rather large memory leak.
        #
        # The solution is to access a weakref instead. The weakref will
        # reference the repository, but it will safely go away when needed.
        # The function we pass can access that without causing the leaks
        repository_ref = weakref.ref(repository)
        client.set_ssl_server_trust_prompt(
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
        self.revision_re = re.compile(r'''
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
            '''.encode('utf-8'), re.VERBOSE)

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
        '''.encode('utf-8'), re.VERBOSE)

    def get_file(
        self,
        path: str,
        revision: RevisionID = HEAD,
        *args,
        **kwargs,
    ) -> bytes:
        """Return the contents of a file from a repository.

        This attempts to return the raw binary contents of a file from the
        repository, given a file path and revision.

        Args:
            path (str):
                The path to the file in the repository.

            revision (reviewboard.scmtools.core.Revision, optional):
                The revision to fetch. Subclasses should default this to
                :py:data:`HEAD`.

            *args (tuple, unused):
                Additional unused positional arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Returns:
            bytes:
            The returned file contents.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                The file could not be found in the repository.

            reviewboard.scmtools.errors.InvalidRevisionFormatError:
                The ``revision`` argument was in an invalid format.

            reviewboard.scmtools.errors.SCMError:
                An unexpected error was encountered with the repository.
        """
        return self.client.get_file(path, revision)

    def get_branches(self) -> Sequence[Branch]:
        """Return a list of all branches on the repository.

        This will fetch a list of all known branches for use in the API and
        New Review Request page.

        This assumes the standard layout in the repository.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of branches in the repository. One (and only one) will
            be marked as the default branch.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.
        """
        results: List[Branch] = []

        root_dirents = self.client.list_dir('/')
        default = True

        if 'trunk' in root_dirents:
            # Looks like the standard layout. Adds trunk and any branches.
            trunk = root_dirents['trunk']
            results.append(self._create_branch_from_dirent(
                name='trunk',
                dirent=trunk,
                default=True))
            default = False

        if 'branches' in root_dirents:
            dirents = self.client.list_dir('branches')
            results += [
                self._create_branch_from_dirent(name=name,
                                                dirent=dirents[name])
                for name in sorted(dirents.keys())
            ]

        # Add anything else from the root of the repository. This is a
        # catch-all for repositories which do not use the standard layout, and
        # for those that do, will include any additional top-level directories
        # that people may have.
        for name in sorted(root_dirents.keys()):
            if name not in ('trunk', 'branches'):
                results.append(self._create_branch_from_dirent(
                    name=name,
                    dirent=root_dirents[name],
                    default=default))
                default = False

        return results

    def get_commits(
        self,
        branch: Optional[str] = None,
        start: Optional[str] = None,
    ) -> Sequence[Commit]:
        """Return a list of commits backward in history from a given point.

        This will fetch a batch of commits from the repository for use in the
        API and New Review Request page.

        The resulting commits will be in order from newest to oldest, and
        should return up to a fixed number of commits (usually 30, but this
        depends on the type of repository and its limitations). It may also be
        limited to commits that exist on a given branch (if supported by the
        repository).

        This can be called multiple times in succession using the
        :py:attr:`Commit.parent` of the last entry as the ``start`` parameter
        in order to paginate through the history of commits in the repository.

        Args:
            branch (str, optional):
                The branch to limit commits to. This may not be supported by
                all repositories.

            start (str, optional):
                The commit to start at. If not provided, this will fetch the
                first commit in the repository.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The list of commits, in order from newest to oldest.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Commits retrieval is not available for this type of repository.
        """
        commits = self.client.get_log(branch or '/',
                                      start=start,
                                      limit=self.COMMITS_PAGE_LIMIT,
                                      limit_to_path=False)

        results: List[Commit] = []

        # We fetch one more commit than we care about, because the entries in
        # the svn log doesn't include the parent revision.
        for i in range(len(commits) - 1):
            commit = commits[i]
            parent = commits[i + 1]
            results.append(self._build_commit(data=commit,
                                              parent=parent['revision']))

        # If there were fewer than the requested number of commits fetched,
        # also include the last one in the list so we don't leave off the
        # initial revision.
        if len(commits) < self.COMMITS_PAGE_LIMIT:
            commit = commits[-1]
            results.append(self._build_commit(data=commit))

        return results

    def get_change(
        self,
        revision: str,
    ) -> Commit:
        """Return an individual commit with the given revision.

        This will fetch information on the given commit, if found, including
        its commit message and list of modified files.

        Args:
            revision (str):
                The revision of the commit.

        Returns:
            Commit:
            The resulting commit with the given revision.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                Error retrieving information on this commit.
        """
        commits = self.client.get_log('/', start=revision, limit=2)

        if len(commits) > 1:
            base_revision = commits[1]['revision']
        else:
            base_revision = '0'

        diff = self.client.diff(base_revision, revision)

        commit = self._build_commit(data=commits[0],
                                    parent=base_revision)
        commit.diff = diff

        return commit

    def normalize_patch(
        self,
        patch: bytes,
        filename: str,
        revision: str,
    ) -> bytes:
        """Normalize a diff/patch file before it's applied.

        This will check the patch for any ``$...$`` keywords. If found, the
        repository will be queried for matches, and those will be collapsed
        in the diff. This ensures that the file can be applied on top of a
        normalized source file, and compared to other normalized patches.

        Args:
            patch (bytes):
                The diff/patch file to normalize.

            filename (str):
                The name of the file being changed in the diff.

            revision (str):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        if revision != PRE_CREATION and has_expanded_svn_keywords(patch):
            keywords = self.client.get_keywords(filename, revision)

            if keywords:
                return collapse_svn_keywords(patch, force_bytes(keywords))

        return patch

    def parse_diff_revision(
        self,
        filename: bytes,
        revision: bytes,
        *args,
        **kwargs,
    ) -> Tuple[bytes, Union[bytes, Revision]]:
        """Parse and return a filename and revision from a diff.

        Args:
            filename (bytes):
                The filename as represented in the diff.

            revision (bytes):
                The revision as represented in the diff.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.

        Returns:
            tuple:
            A tuple containing two items:

            Tuple:
                0 (bytes):
                    The normalized filename.

                1 (bytes or reviewboard.scmtools.core.Revision):
                    The normalized revision.
        """
        assert isinstance(filename, bytes), (
            'filename must be a byte string, not %s' % type(filename))
        assert isinstance(filename, bytes), (
            'revision must be a byte string, not %s' % type(revision))

        # Some diffs have additional tabs between the parts of the file
        # revisions
        revision = revision.strip()

        if self.working_copy_re.match(revision):
            return filename, HEAD

        # "(revision )" is generated by a few weird tools (like IntelliJ). If
        # in the +++ line of the diff, it means HEAD, and in the --- line, it
        # means PRE_CREATION. Since the more important use case is parsing the
        # source revision, we treat it as a new file. See bugs 1937 and 2632.
        if revision == b'(revision )':
            return filename, PRE_CREATION

        # Binary diffs don't provide revision information, so we set a fake
        # "(unknown)" in the SVNDiffParser. This will never actually appear
        # in SVN diffs.
        if revision == b'(unknown)':
            return filename, UNKNOWN

        m = self.revision_re.match(revision)

        if not m:
            raise SCMError('Unable to parse diff revision header "%s"'
                           % revision.decode('utf-8'))

        relocated_file = m.group(2)
        norm_revision: Union[bytes, Revision] = m.group(4)

        # group(3) holds the revision string in braces, like '(revision 4)'
        # group(4) only matches the revision number, which might by None when
        # 'nonexistent' is given as the revision string
        if norm_revision in (None, b'0'):
            norm_revision = PRE_CREATION

        if relocated_file:
            if not relocated_file.startswith(b'...'):
                raise SCMError('Unable to parse SVN relocated path "%s"'
                               % relocated_file.decode('utf-8'))

            filename = b'%s/%s' % (relocated_file[4:], filename)

        return filename, norm_revision

    def get_repository_info(self) -> Dict[str, Any]:
        """Return information on the repository.

        Returns:
            dict:
            A dictionary containing information on the repository.

            See :py:class:`reviewboard.scmtools.svn.base.SVNRepositoryInfoDict`
            for contents.

        Raises:
            NotImplementedError:
                Repository information retrieval is not implemented by this
                type of repository. Callers should specifically check for this,
                as it's considered a valid result.
        """
        return self.client.repository_info

    def get_parser(
        self,
        data: bytes,
    ) -> SVNDiffParser:
        """Return a diff parser used to parse diff data.

        The diff parser will be responsible for parsing the contents of the
        diff, and should expect (but validate) that the diff content is
        appropriate for the type of repository.

        Subclasses should override this.

        Args:
            data (bytes):
                The diff data to parse.

        Returns:
            SVNDiffParser:
            The diff parser used to parse this data.
        """
        return SVNDiffParser(data)

    def _create_branch_from_dirent(
        self,
        *,
        name: str,
        dirent: SVNDirEntry,
        default=False,
    ) -> Branch:
        """Return a Branch object from a Subversion directory entry.

        Args:
            name (str):
                The name of the directory entry.

            dirent (reviewboard.scmtools.svn.base.SVNDirEntry):
                The directory entry to parse.

            default (bool, optional):
                Whether this is the default branch.

        Returns:
            reviewboard.scmtools.core.Branch:
            The resulting branch.
        """
        return Branch(
            id=dirent['path'].strip('/'),
            name=name,
            commit=dirent['created_rev'],
            default=default)

    def _build_commit(
        self,
        *,
        data: SVNLogEntry,
        parent: Union[bytes, str] = '',
    ) -> Commit:
        """Return a Commit object from the provided data.

        Args:
            data (reviewboard.scmtools.svn.base.SVNLogEntry):
                The log entry to build the data from.

            parent (bytes or str, optional):
                The parent commit revision.

        Returns:
            reviewboard.scmtools.core.Commit:
            The resulting commit.
        """
        date = data.get('date')
        norm_date: str = ''

        if date:
            norm_date = str(date.isoformat())

        return Commit(
            author_name=force_str(data.get('author', ''), errors='replace'),
            id=force_str(data['revision']),
            date=norm_date,
            message=force_str(data.get('message', ''), errors='replace'),
            parent=force_str(parent))

    @classmethod
    def _ssl_server_trust_prompt(
        cls,
        trust_data: RawSSLTrustDict,
        repository: Optional[Repository],
    ) -> Tuple[bool, int, bool]:
        """Callback for SSL cert verification.

        This will be called when accessing a repository with an SSL cert.
        We will look up a matching cert in the database and see if it's
        accepted.

        Args:
            trust_data (RawSSLTrustDict):
                The Subversion SSL trust data.

            repository (reviewboard.scmtools.models.Repository):
                The repository triggering the SSL cert verification.

        Returns:
            tuple:
            A 3-tuple containing:

            Tuple:
                0 (bool):
                    Whether the certificate is verified.

                1 (int):
                    A bitmask of Subversion SSL trust failure codes.

                2 (bool):
                    Whether to store the trust info within the filesystem.

                    This is always ``False``, since we want to handle this
                    on our end.
        """
        if repository is None:
            return False, 0, False

        saved_cert = repository.extra_data.get('cert', {})
        cert: Dict[str, Any] = cast(Dict[str, Any], trust_data.copy())
        del cert['failures']

        return saved_cert == cert, trust_data['failures'], False

    @staticmethod
    def on_ssl_failure(
        client: Client,
        e: Exception,
        path: str,
        cert_data: Dict[str, Any],
    ) -> None:
        """Handle a SSL certificate failure.

        This will determine if the error contains unverified SSL certificate
        information that needs to be returned. If found, a suitable error
        will be generated and raised.

        Args:
            client (reviewboard.scmtools.svn.base.Client):
                The client talking to Subversion.

            e (Exception):
                The raw exception found during SSL communication.

            path (str):
                The repository path.

            cert_data (RawSSLTrustDict):
                The dictionary containing Subversion SSL certificate
                information.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                There was an error authenticating, rather than an issue with
                the SSL certificate.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                The repository was not found.

            reviewboard.scmtools.errors.UnverifiedCertificateError:
                The certificate was not verified.

                Details are in the error message and associated certificate.
        """
        logger.error('SVN: Failed to get repository information for %s: %s',
                     path, e)

        error = client.normalize_error(e)

        if isinstance(error, AuthenticationError):
            raise error

        if cert_data:
            failures = cert_data['failures']

            reasons: List[str] = []

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
    def check_repository(
        cls,
        path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        local_site_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> None:
        """Check a repository configuration for validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        A failed result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception will
        be thrown.

        Args:
            path (str):
                The repository path.

            username (str, optional):
                The optional username for the repository.

            password (str, optional):
                The optional password for the repository.

            local_site_name (str, optional):
                The name of the Local Site that owns this repository.

            *args (tuple, unused):
                Additional unused positional arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Raises:
            reviewboard.scmtools.errors.AuthenticationError:
                The provided username/password or the configured SSH key could
                not be used to authenticate with the repository.

            reviewboard.scmtools.errors.RepositoryNotFoundError:
                A repository could not be found at the given path.

            reviewboard.scmtools.errors.SCMError:
                There was a generic error with the repository or its
                configuration.  Details will be provided in the error message.

            reviewboard.ssh.errors.BadHostKeyError:
                An SSH path was provided, but the host key for the repository
                did not match the expected key.

            reviewboard.ssh.errors.SSHError:
                An SSH path was provided, but there was an error establishing
                the SSH connection.

            reviewboard.ssh.errors.SSHInvalidPortError:
                An SSH path was provided, but the port specified was not a
                valid number.

            Exception:
                An unexpected exception has occurred. Callers should check
                for this and handle it.
        """
        super().check_repository(
            path=path,
            username=username,
            password=password,
            local_site_name=local_site_name,
            **kwargs)

        if path.startswith('https://'):
            client = cls.build_client(repo_path=path,
                                      username=username,
                                      password=password,
                                      local_site_name=local_site_name)
            client.accept_ssl_certificate(path,
                                          on_failure=cls.on_ssl_failure)

    @classmethod
    def accept_certificate(
        cls,
        path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        local_site_name: Optional[str] = None,
        certificate: Optional[Certificate] = None,
    ) -> Mapping[str, Any]:
        """Accept the HTTPS certificate for the given repository path.

        Args:
            path (str):
                The repository path.

            username (str, optional):
                The username provided for the repository.

            password (str, optional):
                The password provided for the repository.

            local_site_name (str, optional):
                The name of the Local Site used for the repository, if any.

            certificate (reviewboard.scmtools.certs.Certificate):
                The certificate to accept.

        Returns:
            dict:
            Serialized information on the certificate.

        Raises:
            reviewboard.scmtools.errors.SCMError:
                There was an error accepting the certificate.
        """
        client = cls.build_client(repo_path=path,
                                  username=username,
                                  password=password,
                                  local_site_name=local_site_name)

        return client.accept_ssl_certificate(path)

    @classmethod
    def build_client(
        cls,
        *,
        repo_path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        local_site_name: Optional[str] = None,
    ) -> Client:
        """Return a new Subversion client.

        This will determine and create a Subversion directory for the global
        site or Local Site, and then return a configured client.

        Args:
            repo_path (str):
                The URI to the Subversion repository.

            username (str, optional):
                The username used to authenticate with the repository.

            password (str, optional):
                The password used to authenticate with the repository.

            local_site_name (str, optional):
                The name of the Local Site that owns the repository.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (str):
                    The Subversion configuration directory.

                1 (reviewboard.scmtools.svn.base.Client):
                    The resulting client instance.
        """
        if not has_svn_backend:
            raise ImportError(
                _('SVN integration requires PySVN. See %(url)s for '
                  'installation instructions.')
                % {
                    'url': (
                        '%sadmin/installation/linux/#subversion'
                        % get_manual_url()
                    ),
                })

        config_dir = os.path.join(get_data_dir(), '.subversion')

        if local_site_name:
            # LocalSites can have their own Subversion config, used for
            # per-LocalSite SSH keys.
            config_dir = cls._prepare_local_site_config_dir(local_site_name)
        elif not os.path.exists(config_dir):
            cls._create_subversion_dir(config_dir)

        assert _SVNClientBackend is not None
        return _SVNClientBackend(config_dir=config_dir,
                                 repopath=repo_path,
                                 username=username,
                                 password=password)

    @classmethod
    def _create_subversion_dir(
        cls,
        config_dir: str,
    ) -> None:
        """Create a local Subversion directory for data storage.

        Args:
            config_dir (str):
                The absolute path to the new Subversion directory.

        Raises:
            IOError:
                There was an error creating the directory.

                Details are in the error message.
        """
        try:
            os.mkdir(config_dir, 0o700)
        except OSError:
            raise IOError(
                _("Unable to create directory %(dirname)s, which is needed "
                  "for the Subversion configuration. Create this directory "
                  "and set the web server's user as the the owner.")
                % {'dirname': config_dir})

    @classmethod
    def _prepare_local_site_config_dir(
        cls,
        local_site_name: str,
    ) -> str:
        """Prepare a Subversion configuration for a Local Site.

        This will create the directory if it doesn't exist, and then
        prepare a Subversion configuration for linking Review Board up with
        RBSSH.

        Args:
            local_site_name (str):
                The name of the Local Site.

        Returns:
            str:
            The resulting configuration directory.
        """
        config_dir = os.path.join(get_data_dir(), '.subversion')

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
    """Diff parser for Subversion diff files.

    This is designed to be compatible with all variations of the Subversion
    diff format, supporting standard file modifications and property changes.
    """

    BINARY_STRING = b'Cannot display: file marked as a binary type.'

    def parse_diff_header(self, linenum, parsed_file):
        """Parse a standard header before changes made to a file.

        This builds upon the standard behavior to see if the change is to a
        property, rather than a file. Property changes are skipped.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (reviewboard.diffviewer.parser.ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the diff header. This may be a
                corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        lines = self.lines

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
                lines[linenum].startswith(b'--- (') and
                lines[linenum + 1].startswith(b'+++ (') and
                lines[linenum + 2].startswith(b'Property changes on:')
            )
        except IndexError:
            is_property_change = False

        if is_property_change:
            # Subversion diffs with property changes have no really
            # parsable format. The content of a property can easily mimic
            # the property change headers. So we can't rely upon it, and
            # can't easily display it. Instead, skip it, so it at least
            # won't break diffs.
            parsed_file.skip = True
            linenum += 4

            return linenum

        # Handle deleted empty files.
        if (parsed_file.index_header_value and
            parsed_file.index_header_value.endswith(b'\t(deleted)')):
            parsed_file.deleted = True

        linenum = super(SVNDiffParser, self).parse_diff_header(
            linenum, parsed_file)

        if (parsed_file.modified_file_details and
            parsed_file.modified_file_details.endswith(b'(nonexistent)')):
            parsed_file.deleted = True

        return linenum

    def parse_special_header(self, linenum, parsed_file):
        """Parse a special diff header marking the start of a new file's info.

        This will look for:

        * An empty ``Index:`` line, which suggests a change to a property
          rather than a file (in older versions of SVN diffs).
        * A populated ``Index:`` line, which is required for any changes to
          files (and may be present for property changes in newer versions of
          SVN diffs).
        * Changes to binary files, which lack revision information and must
          be populated with defaults.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (reviewboard.diffviewer.parser.ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.

        Raises:
            reviewboard.diffviewer.errors.DiffParserError:
                There was an error parsing the special header. This may be
                a corrupted diff, or an error in the parsing implementation.
                Details are in the error message.
        """
        lines = self.lines

        if linenum + 1 < len(lines) and lines[linenum] == b'Index:':
            # This is an empty Index: line. This might mean we're parsing
            # a property change.
            return linenum + 2

        linenum = super(SVNDiffParser, self).parse_special_header(
            linenum, parsed_file)

        file_index = parsed_file.index_header_value

        if file_index is None:
            return linenum

        try:
            if lines[linenum] == self.BINARY_STRING:
                # Skip this and the svn:mime-type line.
                linenum += 2

                parsed_file.binary = True
                parsed_file.orig_filename = file_index
                parsed_file.modified_filename = file_index

                # We can't get the revision info from this diff header.
                parsed_file.orig_file_details = b'(unknown)'
                parsed_file.modified_file_details = b'(working copy)'
        except IndexError:
            pass

        return linenum

    def parse_after_headers(self, linenum, parsed_file):
        """Parse information after a diff header but before diff data.

        This looks for any property changes after the diff header, starting
        with ``Property changes on:``. If found, the changes will be kept
        only if processing a binary file, as binary files nearly always have
        a property that's relevant (the mimetype). Otherwise, property changes
        are skipped.

        Args:
            linenum (int):
                The line number to begin parsing.

            parsed_file (ParsedDiffFile):
                The file currently being parsed.

        Returns:
            int:
            The next line number to parse.
        """
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
        lines = self.lines

        try:
            if (lines[linenum] == b'' and
                lines[linenum + 1].startswith(b'Property changes on:')):
                # If we're working with binary files, we're going to leave
                # the data here and not skip the entry. SVN diffs may include
                # property changes as part of the binary file entry.
                if not parsed_file.binary:
                    # Skip over the next 3 lines (blank, "Property changes
                    # on:", and the "__________" divider.
                    parsed_file.skip = True

                linenum += 3
        except IndexError:
            pass

        return linenum


def recompute_svn_backend() -> None:
    """Recompute the SVNTool client backend to use.

    Normally, this is only called once, but it may be used to reset the
    backend for use in testing.
    """
    global _SVNClientBackend
    global has_svn_backend

    _SVNClientBackend = None
    has_svn_backend = False

    for backend_path in settings.SVNTOOL_BACKENDS:
        try:
            mod = import_module(backend_path)

            # Check that this is a valid SVN backend.
            if (not hasattr(mod, 'has_svn_backend') or
                not hasattr(mod, 'Client')):
                logger.error('Attempted to load invalid SVN backend %s',
                             backend_path)
                continue

            has_svn_backend = mod.has_svn_backend

            # We want either the winning SVN backend or the first one to show
            # up in the required module dependencies list.
            if has_svn_backend:
                SVNTool.dependencies['modules'] = [mod.Client.required_module]

            if has_svn_backend:
                # We found a suitable backend.
                logger.debug('Using %s backend for SVN', backend_path)
                _SVNClientBackend = mod.Client
                break
        except ImportError:
            logger.exception('Unable to load SVN backend %s', backend_path)


recompute_svn_backend()
