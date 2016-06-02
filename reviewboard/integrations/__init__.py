"""Integrations support for Review Board.

This module provides the Review Board functionality needed to create
integrations for third-party services. It builds upon Djblets's integrations
foundation, offering some additional utilities for more easily creating
manageable integrations.

This module provides imports for:

.. autosummary::
   :nosignatures:

   ~reviewboard.integrations.base.get_integration_manager
   ~reviewboard.integrations.base.Integration
"""

from __future__ import unicode_literals

from reviewboard.integrations.base import get_integration_manager, Integration


__all__ = [
    'get_integration_manager',
    'Integration',
]
