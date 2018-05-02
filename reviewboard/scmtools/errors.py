from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from reviewboard.ssh.errors import SSHAuthenticationError


class SCMError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ChangeSetError(SCMError):
    pass


class InvalidChangeNumberError(ChangeSetError):
    def __init__(self):
        ChangeSetError.__init__(self, None)


class ChangeNumberInUseError(ChangeSetError):
    def __init__(self, review_request=None):
        ChangeSetError.__init__(self, None)
        self.review_request = review_request


class EmptyChangeSetError(ChangeSetError):
    def __init__(self, changenum):
        ChangeSetError.__init__(self, _('Changeset %s is empty') % changenum)


class InvalidRevisionFormatError(SCMError):
    """Indicates that a revision isn't in a recognizable format."""
    def __init__(self, path, revision, detail=None):
        msg = _("The revision '%(revision)s' for '%(path)s' isn't in a valid "
                "format") % {
            'revision': revision,
            'path': path,
        }

        if detail:
            msg += ': ' + detail

        SCMError.__init__(self, msg)

        self.path = path
        self.revision = revision
        self.detail = detail


class FileNotFoundError(SCMError):
    def __init__(self, path, revision=None, detail=None, base_commit_id=None):
        from reviewboard.scmtools.core import HEAD

        if isinstance(path, bytes):
            path = path.decode('utf-8', 'ignore')

        if revision is None or revision == HEAD and base_commit_id is None:
            msg = (_("The file '%s' could not be found in the repository")
                   % path)
        elif base_commit_id is not None and base_commit_id != revision:
            msg = _('The file "%(path)s" (revision %(revision)s, commit '
                    '%(base_commit_id)s) could not be found in the '
                    'repository') % {
                'path': path,
                'revision': revision,
                'base_commit_id': base_commit_id,
            }
        else:
            msg = _('The file "%(path)s" (revision %(revision)s) could not be '
                    'found in the repository') % {
                'path': path,
                'revision': revision,
            }

        if detail:
            msg += ': ' + detail

        Exception.__init__(self, msg)

        self.revision = revision
        self.base_commit_id = base_commit_id
        self.path = path
        self.detail = detail


class RepositoryNotFoundError(SCMError):
    """An error indicating that a given path is not a valid repository."""
    def __init__(self):
        SCMError.__init__(self, _('A repository was not found at the '
                                  'specified path.'))


class AuthenticationError(SSHAuthenticationError, SCMError):
    """An error representing a failed authentication for a repository.

    This takes a list of authentication types that are allowed. These
    are dependant on the backend, but are loosely based on SSH authentication
    mechanisms. Primarily, we respond to "password" and "publickey".

    This may also take the user's SSH key that was tried, if any.
    """
    pass


class UnverifiedCertificateError(SCMError):
    """An error representing an unverified SSL certificate."""
    def __init__(self, certificate):
        SCMError.__init__(self, _('A verified SSL certificate is required '
                                  'to connect to this repository.'))
        self.certificate = certificate
