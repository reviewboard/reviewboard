from __future__ import annotations

from typing import Generic, TYPE_CHECKING

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from haystack import indexes
from typing_extensions import TypeVar

from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Final


_TModel = TypeVar('_TModel',
                  bound=Model,
                  default=Model)


class BaseSearchIndex(Generic[_TModel], indexes.SearchIndex):
    """Base class for a search index.

    This sets up a few common fields we want all indexes to include.

    Version Changed:
        8.0:
        This now supports a generic type for the indexed model.
    """

    #: The model to index.
    model: type[_TModel]

    #: The local site attribute on the model.
    #:
    #: For ForeignKeys, this should be the name of the ID field, as in
    #: 'local_site_id'. For ManyToManyFields, it should be the standard field
    #: name.
    local_site_attr: (str | None) = None

    # Common fields for all search indexes.
    text = indexes.CharField(document=True, use_template=True)
    local_sites = indexes.MultiValueField(null=True)

    #: A constant indicating no Local Site ID on an object.
    NO_LOCAL_SITE_ID: Final[int] = 0

    def get_model(self) -> type[_TModel]:
        """Return the model for this index.

        Returns:
            type:
            The type of model.

        Raises:
            AttributeError:
                :py:attr:`model` was not set on the subclass.
        """
        model = getattr(self, 'model', None)

        if model is None:
            raise AttributeError(
                f'{self.__class__.__name__}.model must be set.'
            )

        return model

    def prepare_local_sites(
        self,
        obj: _TModel,
    ) -> Sequence[str]:
        """Prepare the list of local sites for the search index.

        This will take any associated local sites on the object and store
        them in the index as a list. The search view can then easily look up
        values in the list, regardless of the type of object.

        If the object is not a part of a local site, the list will be
        ``[0]``, indicating no local site.

        Args:
            obj (django.db.models.Model):
                The model instance to prepare.

        Returns:
            list of str:
            The list of of model Local Site IDs as strings, or ``[0]`` if
            there are no Local Sites.

        Raises:
            django.core.exceptions.ImproperlyConfigured:
                One or more attributes were not set on the subclass.
        """
        if not self.local_site_attr:
            raise ImproperlyConfigured('local_site_attr must be set on %r'
                                       % self.__class__)

        if not hasattr(obj, self.local_site_attr):
            raise ImproperlyConfigured(
                '"%s" is not a valid local site attribute on %r'
                % (self.local_site_attr, obj.__class__))

        if not LocalSite.objects.has_local_sites():
            # There aren't any Local Sites on the server, so there's nothing
            # to process.
            return [str(self.NO_LOCAL_SITE_ID)]

        local_sites = getattr(obj, self.local_site_attr, None)

        if self.local_site_attr.endswith('_id'):
            # This is from a ForeignKey. We're working with a numeric ID.
            if local_sites is not None:
                results = [local_sites]
            else:
                results = [self.NO_LOCAL_SITE_ID]
        else:
            # This is most likely a ManyToManyField. Anything else is an
            # error.
            #
            # We want to loop through the actual entries and not the primary
            # keys. The caller is responsible for doing a prefetch_related().
            results = [
                local_site.pk
                for local_site in local_sites.all()
            ] or [self.NO_LOCAL_SITE_ID]

        # Convert these all to strings. This is what MultiValueField would
        # normally do if we didn't prepare it, and is needed for the kinds of
        # comparisons we perform when using Elasticsearch 7.x+.
        return [str(_pk) for _pk in results]
