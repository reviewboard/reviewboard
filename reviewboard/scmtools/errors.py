from django.utils.encoding import force_str
from django.utils.translation import gettext as _

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
        """Initialize the exception.

        Args:
            path (bytes or unicode):
                The path the revision was for.

            revision (bytes or unicode):
                The revision that was invalid.

            detail (unicode, optional):
                Additional detail to display after the standard error message.
        """
        path = force_str(path)
        revision = force_str(revision)

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
    """An error indicating a file was not found in a repository.

    Attributes:
        base_commit_id (unicode):
            The optional ID of the base commit the file and revision belonged
            to.

        context (reviewboard.scmtools.core.FileLookupContext, optional):
            Extra context used to help look up the file.

            Version Added:
                4.0.5

        detail (unicode):
            Additional details for the error message.

        path (unicode):
            The path in the repository.

        revision (reviewboard.scmtools.core.Revision or unicode):
            The revision in the repository.
    """

    def __init__(self, path, revision=None, detail=None, base_commit_id=None,
                 context=None):
        """Initialize the error.

        Args:
            path (unicode):
                The path in the repository.

            revision (reviewboard.scmtools.core.Revision or unicode, optional):
                The revision in the repository.

            detail (unicode, optional):
                Additional details for the error message.

            base_commit_id (unicode, optional):
                The optional ID of the base commit the file and revision
                belonged to.

            context (reviewboard.scmtools.core.FileLookupContext, optional):
                Extra context used to help look up the file.

                Version Added:
                    4.0.5
        """
        from reviewboard.scmtools.core import HEAD

        if isinstance(path, bytes):
            path = path.decode('utf-8', 'ignore')

        if base_commit_id is None and context is not None:
            base_commit_id = context.base_commit_id

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
        self.context = context
        self.path = path
        self.detail = detail


class RepositoryNotFoundError(SCMError):
    """An error indicating that a given path is not a valid repository.

    Version Changed:
        4.0.11:
        Added :py:attr:`form_field_id` and an equivalent argument to the
        constructor.

    Attributes:
        form_field_id (unicode):
            The ID of the form field that this error corresponds to.

            This may be ``None`` if this error isn't about a specific field.

            Version Added:
                4.0.11
    """

    def __init__(self, msg=None, form_field_id=None):
        """Initialize the error.

        Version Changed:
            4.0.11:
            This now takes optional ``msg`` and ``form_field_id`` parameters.

        Args:
            msg (unicode, optional):
                The optional custom message to display.

            form_field_id (unicode, optional):
                The optional ID of the form field that this error corresponds
                to.
        """
        super(RepositoryNotFoundError, self).__init__(
            msg or
            _('A repository was not found. Please check the configuration '
              'to make sure the details are correct and that it allows '
              'access using any credentials you may have provided.'))

        self.form_field_id = form_field_id


class AuthenticationError(SSHAuthenticationError, SCMError):
    """An error representing a failed authentication for a repository.

    This takes a list of authentication types that are allowed. These
    are dependent on the backend, but are loosely based on SSH authentication
    mechanisms. Primarily, we respond to "password" and "publickey".

    This may also take the user's SSH key that was tried, if any.
    """
    pass


class UnverifiedCertificateError(SCMError):
    """An error representing an unverified SSL certificate.

    Attributes:
        reviewboard.scmtools.certs.Certificate:
        The certificate this error pertains to.
    """

    def __init__(self, certificate):
        """Initialize the error message.

        Args:
            certificate (reviewboard.scmtools.certs.Certificate):
                The certificate this error pertains to.
        """
        info = []

        if certificate.hostname:
            info.append(_('hostname "%s"') % certificate.hostname)

        if certificate.fingerprint:
            info.append(_('fingerprint "%s"') % certificate.fingerprint)

        if certificate and certificate.fingerprint:
            msg = _(
                'The SSL certificate for this repository (%s) was not '
                'verified and might not be safe. This certificate needs to '
                'be verified before the repository can be accessed.'
            ) % (', '.join(info))
        else:
            msg = _(
                'The SSL certificate for this repository was not verified '
                'and might not be safe. This certificate needs to be '
                'verified before the repository can be accessed.'
            )

        super(SCMError, self).__init__(msg)
        self.certificate = certificate
