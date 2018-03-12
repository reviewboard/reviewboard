from __future__ import unicode_literals


class Certificate(object):
    """A representation of an HTTPS certificate."""

    def __init__(self, pem_data='', valid_from='', valid_until='', hostname='',
                 realm='', fingerprint='', issuer='', failures=[]):
        """Initialize the certificate.

        Args:
            pem_data (unicode):
                The PEM-encoded certificate, if available.

            valid_from (unicode):
                A user-readable representation of the initiation date of the
                certificate.

            valid_until (unicode):
                A user-readable representation of the expiration date of the
                certificate.

            hostname (unicode):
                The hostname that this certificate is tied to.

            realm (unicode):
                An authentication realm (used with SVN).

            fingerprint (unicode):
                The fingerprint of the certificate. This can be in various
                formats depending on the backend which is dealing with the
                certificate, but ideally should be a SHA256-sum of the
                DER-encoded certificate.

            issuer (unicode):
                The common name of the issuer of the certificate.

            failures (list of unicode):
                A list of the verification failures, if available.
        """
        self.pem_data = pem_data
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.hostname = hostname
        self.realm = realm
        self.fingerprint = fingerprint
        self.issuer = issuer
        self.failures = failures
