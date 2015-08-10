from __future__ import unicode_literals
import warnings

from djblets.urls.resolvers import DynamicURLResolver


warnings.warn('djblets.util.urlresolvers is deprecated. See '
              'djblets.urls.resolvers.', DeprecationWarning)


__all__ = ['DynamicURLResolver']
