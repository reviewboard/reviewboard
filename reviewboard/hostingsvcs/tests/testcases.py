from __future__ import unicode_literals

import warnings

from reviewboard.deprecation import RemovedInReviewBoard40Warning
from reviewboard.hostingsvcs.testing import HostingServiceTestCase


class ServiceTests(HostingServiceTestCase):
    """Legacy base class for hosting service tests.

    .. deprecated:: 3.0.4

       This is an old class and should no longer be used as the base class
       for hosting service test suites. Use :py:class:`HostingServiceTestCase`
       instead.
    """

    @classmethod
    def setUpClass(cls):
        warnings.warn('ServiceTests is deprecated. Subclass '
                      'HostingServiceTestCase instead.',
                      RemovedInReviewBoard40Warning)

        super(ServiceTests, cls).setUpClass()

    # Legacy private functions previously used by subclasses.
    #
    # These have never been documented and still aren't. They shouldn't be
    # used, technically, and will go away in time.
    def _get_form(self, *args, **kwargs):
        warnings.warn(
            'ServiceTests._get_form() is deprecated. Use '
            'HostingServiceTestCase.get_form() instead.',
            RemovedInReviewBoard40Warning)

        return self.get_form(*args, **kwargs)

    def _get_hosting_account(self, *args, **kwargs):
        warnings.warn(
            'ServiceTests._get_hosting_account() is deprecated. Use '
            'HostingServiceTestCase.create_hosting_account() instead.',
            RemovedInReviewBoard40Warning)

        kwargs['data'] = {}
        return self.create_hosting_account(*args, **kwargs)

    def _get_repository_fields(self, *args, **kwargs):
        warnings.warn(
            'ServiceTests._get_repository_fields() is deprecated. Use '
            'HostingServiceTestCase.get_repository_fields() instead.',
            RemovedInReviewBoard40Warning)

        return self.get_repository_fields(*args, **kwargs)
