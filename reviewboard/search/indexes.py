from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from haystack import indexes


class BaseSearchIndex(indexes.SearchIndex):
    """Base class for a search index.

    This sets up a few common fields we want all indexes to include.
    """

    #: The model to index.
    model = None

    #: The local site attribute on the model.
    #:
    #: For ForeignKeys, this should be the name of the ID field, as in
    #: 'local_site_id'. For ManyToManyFields, it should be the standar field
    #: name.
    local_site_attr = None

    # Common fields for all search indexes.
    text = indexes.CharField(document=True, use_template=True)
    local_sites = indexes.MultiValueField(null=True)

    NO_LOCAL_SITE_ID = 0

    def get_model(self):
        """Return the model for this index."""
        return self.model

    def prepare_local_sites(self, obj):
        """Prepare the list of local sites for the search index.

        This will take any associated local sites on the object and store
        them in the index as a list. The search view can then easily look up
        values in the list, regardless of the type of object.

        If the object is not a part of a local site, the list will be
        ``[0]``, indicating no local site.
        """
        if not self.local_site_attr:
            raise ImproperlyConfigured('local_site_attr must be set on %r'
                                       % self.__class__)

        if not hasattr(obj, self.local_site_attr):
            raise ImproperlyConfigured(
                '"%s" is not a valid local site attribute on %r'
                % (self.local_site_attr, obj.__class__))

        local_sites = getattr(obj, self.local_site_attr, None)

        if self.local_site_attr.endswith('_id'):
            # This is from a ForeignKey. We're working with a numeric ID.
            if local_sites is not None:
                return [local_sites]
            else:
                return [self.NO_LOCAL_SITE_ID]
        else:
            # This is most likely a ManyToManyField. Anything else is an
            # error.
            return (list(local_sites.values_list('pk', flat=True)) or
                    [self.NO_LOCAL_SITE_ID])
