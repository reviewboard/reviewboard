"""Base support for writing hosting services.

.. autosummary::
   :nosignatures:

   ~reviewboard.hostingsvcs.base.bug_tracker.BaseBugTracker
   ~reviewboard.hostingsvcs.base.client.HostingServiceClient
   ~reviewboard.hostingsvcs.base.hosting_service.BaseHostingService
   ~reviewboard.hostingsvcs.base.http.HostingServiceHTTPRequest
   ~reviewboard.hostingsvcs.base.http.HostingServiceHTTPResponse
   ~reviewboard.hostingsvcs.base.registry.hosting_service_registry
   ~reviewboard.hostingsvcs.base.repository.RemoteRepository

Version Added:
    6.0
"""

from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.base.client import HostingServiceClient
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.hostingsvcs.base.http import (HostingServiceHTTPRequest,
                                               HostingServiceHTTPResponse)
from reviewboard.hostingsvcs.base.registry import hosting_service_registry
from reviewboard.hostingsvcs.base.repository import RemoteRepository


__all__ = [
    'BaseBugTracker',
    'BaseHostingService',
    'HostingServiceClient',
    'HostingServiceHTTPRequest',
    'HostingServiceHTTPResponse',
    'RemoteRepository',
    'hosting_service_registry',
]

__autodoc_excludes__ = __all__
