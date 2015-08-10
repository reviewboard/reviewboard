from __future__ import unicode_literals
import warnings

from djblets.db.evolution import FakeChangeFieldType


warnings.warn('djblets.util.dbevolution is deprecated. Use '
              'djblets.db.evolution instead.', DeprecationWarning)


__all__ = ['FakeChangeFieldType']
