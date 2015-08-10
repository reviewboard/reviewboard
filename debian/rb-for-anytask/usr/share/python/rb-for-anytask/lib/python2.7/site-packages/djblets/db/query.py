from __future__ import unicode_literals

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models.manager import Manager
from django.utils import six


class LocalDataQuerySet(object):
    """A QuerySet that operates on generic data provided by the caller.

    This can be used in some circumstances when code requires a QuerySet,
    but where the data doesn't come from the database. The caller can
    instantiate one of these and provide it.

    This doesn't perform full support for all of QuerySet's abilities. It
    does, however, support the following basic functions:

    * all
    * clone
    * count
    * exclude
    * filter
    * get
    * prefetch_related
    * select_related

    As well as the operators expected by consumers of QuerySet, such as
    __len__ and __iter__.

    This is particularly handy with WebAPIResource.
    """
    def __init__(self, data):
        self._data = data

    def all(self):
        """Returns a cloned copy of this queryset."""
        return self.clone()

    def clone(self):
        """Returns a cloned copy of this queryset."""
        return LocalDataQuerySet(list(self._data))

    def count(self):
        """Returns the number of items in this queryset."""
        return len(self._data)

    def exclude(self, **kwargs):
        """Returns a queryset excluding items from this queryset.

        The result will be a LocalDataQuerySet that contains all items from
        this queryset that do not contain attributes with values matching
        those that were passed to this function as keyword arguments.
        """
        return LocalDataQuerySet(
            list(self._filter_or_exclude(return_matches=False, **kwargs)))

    def filter(self, **kwargs):
        """Returns a queryset filtering items from this queryset.

        The result will be a LocalDataQuerySet that contains all items from
        this queryset that contain attributes with values matching those that
        were passed to this function as keyword arguments.
        """
        return LocalDataQuerySet(
            list(self._filter_or_exclude(return_matches=True, **kwargs)))

    def get(self, **kwargs):
        """Returns a single result from this queryset.

        This will return a single result from the list of items in this
        queryset. If keyword arguments are provided, they will be used
        to filter the queryset down.

        There must be only one item in the queryset matching the given
        criteria, or a MultipleObjectsReturned will be raised. If there are
        no items, then an ObjectDoesNotExist will be raised.
        """
        clone = self.filter(**kwargs)
        count = len(clone)

        if count == 1:
            return clone[0]
        elif count == 0:
            raise ObjectDoesNotExist('%s matching query does not exist.'
                                     % self._data.__class__.__name__)
        else:
            raise MultipleObjectsReturned(
                'get() returned more than one %s -- it returned %s!'
                % (self._data.__class__.__name__, count))

    def prefetch_related(self, *args, **kwargs):
        """Stub for compatibility with QuerySet.prefetch_related.

        This will simply return a clone of this queryset.
        """
        return self.clone()

    def select_related(self, *args, **kwargs):
        """Stub for compatibility with QuerySet.select_related.

        This will simply return a clone of this queryset.
        """
        return self.clone()

    def __contains__(self, i):
        return i in self._data

    def __getitem__(self, i):
        return self._data[i]

    def __getslice__(self, i, j):
        return self._data[i:j]

    def __iter__(self):
        for i in self._data:
            yield i

    def __len__(self):
        return len(self._data)

    def _filter_or_exclude(self, return_matches=True, **kwargs):
        for item in self:
            match = True

            for key, value in six.iteritems(kwargs):
                if getattr(item, key) != value:
                    match = False
                    break

            if match == return_matches:
                yield item


def get_object_or_none(klass, *args, **kwargs):
    if isinstance(klass, Manager):
        manager = klass
        klass = manager.model
    else:
        manager = klass._default_manager

    try:
        return manager.get(*args, **kwargs)
    except klass.DoesNotExist:
        return None
