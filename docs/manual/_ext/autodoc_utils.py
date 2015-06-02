from __future__ import unicode_literals

from django.utils import six
from django.utils.functional import Promise


def _repr_promise(promise):
    """Return a sane representation of a lazy localized string.

    If the promise is a result of ugettext_lazy(), it will be converted into
    a Unicode string before generating a representation.
    """
    if hasattr(promise, '_proxy____text_cast'):
        return '_(%s)' % repr(six.text_type(promise))

    return super(promise.__class__, promise).__repr__(promise)


def setup(app):
    Promise.__repr__ = _repr_promise
