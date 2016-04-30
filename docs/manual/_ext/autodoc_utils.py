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


def _filter_members(app, what, name, obj, skip, options):
    """Filter members out of the documentation.

    This will look up the name in the ``autodoc_excludes`` table under the
    ``what`` and under ``'*'`` keys. If an entry is listed, it will be
    excluded from the documentation.
    """
    excludes = app.config['autodoc_excludes']

    for key in (what, '*'):
        if key in excludes and name in excludes.get(key, []):
            return True

    return skip


def setup(app):
    Promise.__repr__ = _repr_promise

    app.add_config_value('autodoc_excludes', {}, True)
    app.connect(b'autodoc-skip-member', _filter_members)
