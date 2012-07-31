import socket

from django.utils.translation import ugettext as _
from djblets.util.humanize import humanize_list


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
        msg = "The revision '%s' for '%s' isn't in a valid format" % \
              (revision, path)

        if detail:
            msg += ': ' + detail

        SCMError.__init__(self, msg)

        self.path = path
        self.revision = revision
        self.detail = detail


class FileNotFoundError(SCMError):
    def __init__(self, path, revision=None, detail=None):
        from reviewboard.scmtools.core import HEAD

        if revision == None or revision == HEAD:
            msg = "The file '%s' could not be found in the repository" % path
        else:
            msg = "The file '%s' (r%s) could not be found in the repository" \
                % (path, revision)
        if detail:
            msg += ': ' + detail
        Exception.__init__(self, msg)

        self.revision = revision
        self.path = path
        self.detail = detail


class RepositoryNotFoundError(SCMError):
    """An error indicating that a path does not represent a valid repository."""
    def __init__(self):
        SCMError.__init__(self, _('A repository was not found at the '
                                  'specified path.'))


class AuthenticationError(SCMError):
    """An error representing a failed authentication for a repository.

    This takes a list of authentication types that are allowed. These
    are dependant on the backend, but are loosely based on SSH authentication
    mechanisms. Primarily, we respond to "password" and "publickey".

    This may also take the user's SSH key that was tried, if any.
    """
    def __init__(self, allowed_types=[], msg=None, user_key=None):
        if allowed_types:
            msg = _('Unable to authenticate against this repository using one '
                    'of the supported authentication types '
                    '(%(allowed_types)s).') % {
                'allowed_types': humanize_list(allowed_types),
            }
        elif not msg:
            msg = _('Unable to authenticate against this repository using one '
                    'of the supported authentication types.')

        SCMError.__init__(self, msg)
        self.allowed_types = allowed_types
        self.user_key = user_key


class UnverifiedCertificateError(SCMError):
    """An error representing an unverified HTTPS certificate."""
    def __init__(self, certificate):
        SCMError.__init__(self, _('A verified HTTPS certificate is required '
                                  'to connect to this repository.'))
        self.certificate = certificate


class UnsupportedSSHKeyError(SCMError):
    """An error representing an unsupported type of SSH key."""
    def __init__(self):
        SCMError.__init__(self,
                          _('This SSH key is not a valid RSA or DSS key.'))


class SSHKeyError(SCMError):
    """An error involving a host key on an SSH connection."""
    def __init__(self, hostname, key, message):
        from reviewboard.scmtools.sshutils import humanize_key

        SCMError.__init__(self, message)
        self.hostname = hostname
        self.key = humanize_key(key)
        self.raw_key = key


class BadHostKeyError(SSHKeyError):
    """An error representing a bad or malicious key for an SSH connection."""
    def __init__(self, hostname, key, expected_key):
        from reviewboard.scmtools.sshutils import humanize_key

        SSHKeyError.__init__(
            self, hostname, key,
            _("Warning! The host key for server %(hostname)s does not match "
              "the expected key.\n"
              "It's possible that someone is performing a man-in-the-middle "
              "attack. It's also possible that the RSA host key has just "
              "been changed. Please contact your system administrator if "
              "you're not sure. Do not accept this host key unless you're "
              "certain it's safe!")
            % {
                'hostname': hostname,
                'ip_address': socket.gethostbyname(hostname),
            })
        self.expected_key = humanize_key(expected_key)
        self.raw_expected_key = expected_key


class UnknownHostKeyError(SSHKeyError):
    """An error representing an unknown host key for an SSH connection."""
    def __init__(self, hostname, key):
        SSHKeyError.__init__(
            self, hostname, key,
            _("The authenticity of the host '%(hostname)s (%(ip)s)' "
              "couldn't be determined.") % {
                'hostname': hostname,
                'ip': socket.gethostbyname(hostname),
            }
        )
