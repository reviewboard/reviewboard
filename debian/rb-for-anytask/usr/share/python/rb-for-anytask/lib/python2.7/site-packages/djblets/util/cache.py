from __future__ import unicode_literals
import warnings

from djblets.cache.backend_compat import normalize_cache_backend


warnings.warn('djblets.util.cache is deprecated. Use '
              'djblets.cache.backend_compat.', DeprecationWarning)


__all__ = ['normalize_cache_backend']
