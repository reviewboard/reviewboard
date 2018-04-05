"""Support for testing hosting services.

This provides convenience imports for hosting service testing support:

.. autosummary::
   :nosignatures:

   ~reviewboard.hostingsvcs.testing.testcases.HostingServiceTestCase
"""

from __future__ import unicode_literals

from reviewboard.hostingsvcs.testing.testcases import HostingServiceTestCase


__all__ = (
    'HostingServiceTestCase',
)

__autodoc_excludes__ = __all__
