"""Unit tests for reviewboard.certs.utils.

Version Added:
    8.0
"""

from __future__ import annotations

from reviewboard.certs.utils import (get_cert_hostname_matches,
                                     normalize_cert_hostname)
from reviewboard.testing import TestCase


class GetCertHostnameMatchesTests(TestCase):
    """Unit tests for get_cert_hostname_matches.

    Version Added:
        8.0
    """

    def test_with_equal(self) -> None:
        """Testing get_cert_hostname_matches with normalized hostnames equal"""
        self.assertTrue(get_cert_hostname_matches(
            cert_hostname='www.example.COM',
            check_hostname='WWW.EXAMPLE.COM',
        ))
        self.assertTrue(get_cert_hostname_matches(
            cert_hostname='www.example.COM',
            check_hostname='www.example.COM',
            normalize_hostnames=False,
        ))

    def test_with_not_equal(self) -> None:
        """Testing get_cert_hostname_matches with hostnames not equal and
        non-wildcard
        """
        self.assertFalse(get_cert_hostname_matches(
            cert_hostname='example.com',
            check_hostname='www.example.com',
        ))
        self.assertFalse(get_cert_hostname_matches(
            cert_hostname='www.example.com',
            check_hostname='www.example.COM',
            normalize_hostnames=False,
        ))

    def test_with_wildcard(self) -> None:
        """Testing get_cert_hostname_matches with wildcard for full first
        label
        """
        # These should match.
        self.assertTrue(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='www.example.com',
        ))
        self.assertTrue(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='foobar.example.com',
        ))
        self.assertTrue(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='FOOBAR.EXAMPLE.COM',
        ))

        # These should not.
        self.assertFalse(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='example.com',
        ))
        self.assertFalse(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='sub.www.example.com',
        ))
        self.assertFalse(get_cert_hostname_matches(
            cert_hostname='*.example.com',
            check_hostname='FOOBAR.EXAMPLE.COM',
            normalize_hostnames=False,
        ))


class NormalizeCertHostnameTests(TestCase):
    """Unit tests for normalize_cert_hostname.

    Version Added:
        8.0
    """

    def test_with_casing(self) -> None:
        """Testing normalize_cert_hostname with casing differences"""
        self.assertEqual(normalize_cert_hostname('Example.COM'),
                         'example.com')
