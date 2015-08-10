from __future__ import unicode_literals
import warnings

from djblets.urls.root import urlpatterns


warnings.warn('djblets.util.rooturl is deprecated. Use '
              'djblets.urls.root instead.', DeprecationWarning)


__all__ = ['urlpatterns']
