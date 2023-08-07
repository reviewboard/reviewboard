"""Paginators for iterating over API results.

This is pending deprecation. Consumers should update their imports to use
the classes in :py:mod:`reviewboard.hostingsvcs.base.paginator`.
"""

from reviewboard.hostingsvcs.base.paginator import (APIPaginator,
                                                    BasePaginator,
                                                    InvalidPageError,
                                                    ProxyPaginator)


__all__ = [
    'APIPaginator',
    'BasePaginator',
    'InvalidPageError',
    'ProxyPaginator',
]

__autodoc_excludes__ = __all__
