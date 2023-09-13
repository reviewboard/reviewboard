"""Mixins for API unit tests that work with SSL certificates.

Version Added:
    6.0
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Literal, Optional, TYPE_CHECKING, Type

import kgb

from djblets.webapi.errors import WebAPIError
from reviewboard.certs.errors import (CertificateVerificationError,
                                      CertificateVerificationFailureCode)
from reviewboard.webapi.errors import UNVERIFIED_HOST_CERT

if TYPE_CHECKING:
    from reviewboard.webapi.tests.base import BaseWebAPITestCase
    MixinParent = BaseWebAPITestCase
else:
    MixinParent = object


class SSLTestsMixin(MixinParent):
    """Mixin for adding SSL-related unit tests.

    Version Added:
        6.0
    """

    def run_ssl_cert_test(
        self,
        *,
        url: str,
        spy_func: Callable,
        spy_owner: Optional[Type] = None,
        method: Literal['post', 'get', 'delete', 'put'] = 'post',
        data: Dict[str, Any] = {},
    ) -> None:
        assert hasattr(self, 'spy_on'), (
            'This test suite must inherit from kgb.SpyAgency.'
        )

        spy_kwargs = {
            'op': kgb.SpyOpRaise(CertificateVerificationError(
                code=CertificateVerificationFailureCode.NOT_TRUSTED,
                certificate=self.create_certificate())),
        }

        if spy_owner is not None:
            spy_kwargs['owner'] = spy_owner

        self.spy_on(spy_func, **spy_kwargs)

        rsp = getattr(self, f'api_{method}')(
            url,
            data,
            expected_status=UNVERIFIED_HOST_CERT.http_status)

        self.assertEqual(
            rsp,
            {
                'certificate': {
                    'fingerprints': {
                        'sha1': (
                            'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:'
                            'DE:36:2F:D5'
                        ),
                        'sha256': (
                            '79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:B1:6A:AD:79:'
                            'FF:F7:28:69:02:5E:C3:6F:B3:C2:B4:FD:84:66:DF:8F'
                        ),
                    },
                    'hostname': 'example.com',
                    'issuer': 'Test Issuer',
                    'port': 443,
                    'subject': 'Test Subject',
                    'valid_from': '2023-07-14T07:50:30Z',
                    'valid_through': '3023-07-14T07:50:30Z',
                },
                'err': {
                    'code': UNVERIFIED_HOST_CERT.code,
                    'msg': (
                        'The SSL certificate provided by example.com has not '
                        'been signed by a trusted Certificate Authority and '
                        'may not be safe. The certificate needs to be '
                        'verified in Review Board before the server can be '
                        'accessed. Certificate details: '
                        'hostname="example.com", port=443, '
                        'issuer="Test Issuer", fingerprints=SHA1='
                        'F2:35:0F:BB:34:40:84:78:8B:20:1D:40:B1:4A:17:0C:DE:'
                        '36:2F:D5; SHA256=79:19:70:AE:A6:1B:EB:BC:35:7C:B8:54:'
                        'B1:6A:AD:79:FF:F7:28:69:02:5E:C3:6F:B3:C2:B4:FD:84:'
                        '66:DF:8F'
                    ),
                    'type': UNVERIFIED_HOST_CERT.error_type,
                },
                'stat': 'fail',
            })
