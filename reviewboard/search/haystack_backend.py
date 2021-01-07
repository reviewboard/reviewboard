"""Haystack engine that forwards to dynamically-configured engine."""

from __future__ import unicode_literals

import logging
import threading

from djblets.siteconfig.models import SiteConfiguration
from haystack.backends import BaseEngine
from haystack.utils.loading import load_backend

from reviewboard.search import search_backend_registry


logger = logging.getLogger(__name__)


class BaseForwardingObject(object):
    """Base class for an object that forwards on to a search backend's object.

    This works as a proxy to an object on a configured search backend. The
    appropriate object will be constructed as needed and used for all method
    calls and attribute usage.

    Version Added:
        4.0
    """

    #: The name of the attribute on the engine class referencing the object.
    engine_attr = None

    def __init__(self, forwarding_engine, forwarded_obj=None,
                 forwarded_args=[], forwarded_kwargs={}):
        """Initialize the forwarding object.

        Args:
            forwarding_engine (ForwardingSearchEngine):
                The parent forwarding engine.

            forwarded_obj (object, optional):
                A specific instance of an object to forward to, if one is
                available.

            forwarded_args (tuple, optional):
                Positional arguments used to construct the forwarded object.

            forwarded_kwargs (dict, optional):
                Keyword arguments used to construct the forwarded object.
        """
        self._forwarding_engine = forwarding_engine
        self._forwarded_obj = forwarded_obj
        self._forwarded_args = forwarded_args
        self._forwarded_kwargs = forwarded_kwargs

    @property
    def forwarded_obj(self):
        """The object to forward all access to.

        This will be constructed and cached if not already set.

        Type:
            object
        """
        if self._forwarded_obj is None:
            forwarded_cls = getattr(self._forwarding_engine.forwarded_engine,
                                    self.engine_attr)

            self._forwarded_obj = forwarded_cls(*self._forwarded_args,
                                                **self._forwarded_kwargs)

        return self._forwarded_obj

    def __setattribute__(self, name, value):
        """Set an attribute.

        If the attribute belongs to this class, it will be set directly.
        Otherwise, it will be set on the forwarded object.

        Args:
            name (str):
                The name of the attribute.

            value (object):
                The value to set.
        """
        if name in self.__dict__:
            object.__setattribute__(self, name, value)
        else:
            setattr(self.forwarded_obj, name, value)

    def __getattribute__(self, name):
        """Return an attribute value.

        If the attribute belongs to this class, it will be returend directly.
        Otherwise, it will be returned from the forwarded object.

        Args:
            name (str):
                The name of the attribute.

        Returns:
            object:
            The attribute value.

        Raises:
            AttributeError:
                The attribute could not be found.
        """
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return getattr(self.forwarded_obj, name)

    def __repr__(self):
        """Return a string representation of this object.

        Returns:
            unicode:
            The string representation.
        """
        return '<%s(%r)>' % (type(self).__name__, self.forwarded_obj)


class ForwardingSearchBackend(BaseForwardingObject):
    """A forwarding object for a Haystack search backend.

    This wraps a :py:class:`haystack.backends.BaseSearchBackend`.

    Version Added:
        4.0
    """

    engine_attr = 'backend'


class ForwardingSearchQuery(BaseForwardingObject):
    """A forwarding object for a Haystack search query.

    This wraps a :py:class:`haystack.backends.BaseSearchQuery`.

    Version Added:
        4.0
    """

    engine_attr = 'query'

    def _clone(self, klass=None, using=None):
        """Clone the object.

        This is an implementation of a private method in
        :py:class:`haystack.backends.BaseSearchQuery` to handle cloning of
        a query. It will return the clone wrapped in a forwarding object,
        or return a new forwarding object set up to construct an object if one
        doesn't already exist.

        Args:
            klass (type, optional):
                The desired class to construct for the forwarded query object.

            using (unicode, optional):
                The database backend to use. This is expected to be ``None``
                or "default".

        Returns:
            ForwardingSearchQuery:
            The cloned query object.
        """
        if self._forwarded_obj is not None:
            forwarded_obj = self._forwarded_obj._clone(klass=klass,
                                                       using=using)
        else:
            forwarded_obj = None

        return ForwardingSearchQuery(
            forwarding_engine=self._forwarding_engine,
            forwarded_obj=forwarded_obj,
            forwarded_args=self._forwarded_args,
            forwarded_kwargs=self._forwarded_kwargs)


class ForwardingUnifiedIndex(BaseForwardingObject):
    """A forwarding object for a Haystack search query.

    This wraps a :py:class:`haystack.utils.loading.UnifiedIndex`.

    Version Added:
        4.0
    """

    engine_attr = 'unified_index'


class ForwardingSearchEngine(BaseEngine):
    """A Haystack search engine that forwards to another engine.

    This is set as the default search engine for Haystack, and forwards all
    requests to a dynamically-configured search engine backend.

    A forwarding setup is necessary for dynamic configuration with Haystack,
    as it normally computes all backend state on import, and assumes it will
    never change.

    Along with this, some classes (like
    :py:class:`haystack.generic_views.SearchMixin`) set class-level instances
    that store permanent backend state. These must also be overridden to set
    this state per-request in order to gain the full benefits of this engine.

    Version Added:
        4.0
    """

    backend = ForwardingSearchBackend
    query = ForwardingSearchQuery
    unified_index = ForwardingUnifiedIndex

    def __init__(self, *args, **kwargs):
        """Initialize the forwarding engine.

        Args:
            *args (tuple):
                Positional arguments to pass to the parent class.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        super(ForwardingSearchEngine, self).__init__(*args, **kwargs)

        self._forwarded_engine = None
        self._load_lock = threading.Lock()
        self._load_gen = 0
        self._backend = None
        self._index = None
        self._engine_options = None

    @property
    def forwarded_engine(self):
        """The Haystack search engine requests are forwarded to.

        Type:
            haystack.backends.BaseEngine
        """
        if self._forwarded_engine is None:
            self._load_forwarded_engine()

        return self._forwarded_engine

    @property
    def forwarded_options(self):
        """The options for the forwarded Haystack search engine.

        Type:
            dict
        """
        if self._forwarded_engine is None:
            self._load_forwarded_engine()

        assert self._forwarded_options is not None
        return self._forwarded_options

    def get_backend(self):
        """Return the Haystack search backend.

        This will construct a backend object that forwards on to the configured
        Haystack search engine's version.

        Results are cached until the search configuration changes.

        Returns:
            ForwardingSearchBackend:
            The forwarding search backend.
        """
        if self._backend is None:
            self._backend = self.backend(
                forwarding_engine=self,
                forwarded_args=(self.using,),
                forwarded_kwargs=self.forwarded_options)

        return self._backend

    def get_query(self):
        """Return a Haystack search query.

        This will construct a query object that forwards on to the configured
        Haystack search engine's version.

        Results are not cached. This will construct a new instance each time,
        as per Haystack's default behavior.

        Returns:
            ForwardingSearchQuery:
            The forwarding search query.
        """
        return self.query(
            forwarding_engine=self,
            forwarded_kwargs={
                'using': self.using,
            })

    def get_unified_index(self):
        """Return the Haystack unified index object.

        This will construct a unified index object that forwards on to the
        configured Haystack search engine's version.

        Results are cached until the search configuration changes.

        Returns:
            ForwardingUnifiedIndex:
            The forwarding unified index.
        """
        if self._index is None:
            self._index = self.unified_index(
                forwarding_engine=self,
                forwarded_args=(
                    self.forwarded_options.get('EXCLUDED_INDEXES'),
                ))

        return self._index

    def reset_forwarding(self):
        """Reset the forwarding state.

        This should be used whenever we're applying a new search configuration.
        It will clear out any search sessions, the forwarding engine, and any
        cached objects, so that new state can be set on next use.
        """
        self._backend = None
        self._forwarded_engine = None
        self._forwarded_options = None
        self._index = None

        self.reset_sessions()

    def _load_forwarded_engine(self):
        """Load a forwarded Haystack search engine.

        This will look up the current site configuration and determine the
        proper Review Board and Haystack search backends to load, setting any
        forwarding state.

        IF there's an issue at all with loading the search backends, an error
        will be logged and search will be disabled.

        This is thread-safe.
        """
        cur_load_gen = self._load_gen

        with self._load_lock:
            if self._load_gen == cur_load_gen:
                self.reset_forwarding()

                siteconfig = SiteConfiguration.objects.get_current()
                search_backend_id = siteconfig.get('search_backend_id')
                search_backend = search_backend_registry.get_search_backend(
                    search_backend_id)

                if search_backend is None:
                    logger.error('The search engine "%s" could not be found. '
                                 'If this is provided by an extension, you '
                                 'will have to make sure that extension is '
                                 'enabled. Disabling search.',
                                 search_backend_id)
                    engine = None
                else:
                    try:
                        engine_cls = load_backend(
                            search_backend.haystack_backend_name)
                        engine = engine_cls(using=self.using)
                    except Exception as e:
                        logger.error('Error loading the search engine "%s": '
                                     '%s',
                                     search_backend_id, e)
                        engine = None

                if engine is None:
                    # Disable search, since it's useless at this point.
                    siteconfig.set('search_enable', False)
                    siteconfig.save(update_fields=('settings',))
                else:
                    self._forwarded_engine = engine
                    self._search_backend = None
                    self._forwarded_options = search_backend.configuration

                self._load_gen = cur_load_gen + 1
