"""Utilities for certificate and SSL/TLS usage.

Version Added:
    8.0
"""

from __future__ import annotations


def get_cert_hostname_matches(
    *,
    cert_hostname: str,
    check_hostname: str,
    normalize_hostnames: bool = True,
) -> bool:
    """Return whether a certificate's hostname matches the provided hostname.

    A certificate is a match if any of the following conditions are true:

    * The hostnames are a direct match (ignoring case).
    * The first label of a cert hostname is a wildcard (``*``) and matches
      the first label of the hostname, and the remaining labels are
      a direct match (ignoring case).

    Partial wildcards (e.g., ``foo*.example.com``, ``*bar.example.com``, or
    ``foo*bar.example.com``) are not supported. Most Certificate Authorities
    no longer support these, and major browsers (including Chrome) consider
    them security risks.

    This is not intended to be used with IP addresses, only hostnames.

    Version Added:
        8.0

    Args:
        cert_hostname (str):
            A certificate-provided hostname.

        check_hostname (str):
            The hostname to check.

        normalize_hostnames (bool, optional):
            Whether to normalize hostnames before comparison.

            Callers should set this to ``False`` if they're already
            handling normalization.

    Returns:
        bool:
        ``True`` if the hostname is a match for the certificate hostname.
        ``False`` if it is not.
    """
    if normalize_hostnames:
        check_hostname = normalize_cert_hostname(check_hostname)
        cert_hostname = normalize_cert_hostname(cert_hostname)

    if check_hostname == cert_hostname:
        return True

    # We'll check for a wildcard. Start by parsing the labels of the
    # hostnames. If either is bare, consisting of only one label, no further
    # matching will be performed.
    try:
        check_label, check_rest = check_hostname.split('.', 1)
        cert_label, cert_rest = cert_hostname.split('.', 1)
    except ValueError:
        # One of these is a bare name, which cannot match a wildcard or
        # be used to match a hostname.
        return False

    # Wildcards can only match the first label in a hostname. The rest
    # must be a direct match.
    return cert_label == '*' and check_rest == cert_rest


def normalize_cert_hostname(
    hostname: str,
) -> str:
    """Return a normalized version of the cert hostname.

    This requires a hostname or wildcard hostname pattern that is considered
    valid on its own (no whitespace or invalid characters). Both the
    pre-normalized and normalized values must be considered interchangeable for
    the purpose of resolving a domain (or, in the case of wildcards, must be
    able to match the same domain).

    The normalized value will be case-folded for comparison or storage
    purposes.

    Version Added:
        8.0

    Args:
        hostname (str):
            The valid hostname to normalize.

    Returns:
        str:
        The normalized hostname.
    """
    return hostname.casefold()
