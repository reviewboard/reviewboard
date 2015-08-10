from __future__ import unicode_literals
import logging

from django.core.cache import (DEFAULT_CACHE_ALIAS, parse_backend_uri,
                               InvalidCacheBackendError)


BACKEND_CLASSES = {
    'db': 'db.DatabaseCache',
    'dummy': 'dummy.DummyCache',
    'file': 'filebased.FileBasedCache',
    'locmem': 'locmem.LocMemCache',
    'memcached': 'memcached.MemcachedCache',
}

RENAMED_BACKENDS = {
    'django.core.cache.backends.memcached.CacheClass':
        'django.core.cache.backends.memcached.MemcachedCache',
}


def normalize_cache_backend(cache_backend, cache_name=DEFAULT_CACHE_ALIAS):
    """Returns a new-style CACHES dictionary from any given cache_backend.

    Django has supported two formats for a cache backend. The old-style
    CACHE_BACKEND string, and the new-style CACHES dictionary.

    This function will accept either as input and return a cahe backend in the
    form of a CACHES dictionary as a result. The result won't be a full-on
    CACHES, with named cache entries inside. Rather, it will be a cache entry.

    If a CACHES dictionary is passed, the "default" cache will be the result.
    """
    if not cache_backend:
        return {}

    if isinstance(cache_backend, dict):
        backend_info = cache_backend.get(cache_name, {})
        backend_name = backend_info.get('BACKEND')

        if backend_name in RENAMED_BACKENDS:
            backend_info['BACKEND'] = RENAMED_BACKENDS[backend_name]

        return backend_info

    try:
        engine, host, params = parse_backend_uri(cache_backend)
    except InvalidCacheBackendError as e:
        logging.error('Invalid cache backend (%s) found while loading '
                      'siteconfig: %s' % (cache_backend, e))
        return {}

    if engine in BACKEND_CLASSES:
        engine = 'django.core.cache.backends.%s' % BACKEND_CLASSES[engine]
    else:
        engine = '%s.CacheClass' % engine

    defaults = {
        'BACKEND': engine,
        'LOCATION': host,
    }
    defaults.update(params)

    return defaults
