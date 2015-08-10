from __future__ import unicode_literals
from hashlib import md5
import logging
import zlib

from django.conf import settings
from django.core.cache import cache
from django.contrib.sites.models import Site
from django.utils.six.moves import (cPickle as pickle,
                                    cStringIO as StringIO)

from djblets.cache.errors import MissingChunkError


DEFAULT_EXPIRATION_TIME = 60 * 60 * 24 * 30  # 1 month
CACHE_CHUNK_SIZE = 2 ** 20 - 1024  # almost 1M (memcached's slab limit)

# memcached key size constraint (typically 250, but leave a few bytes for the
# large data handling)
MAX_KEY_SIZE = 240


def _cache_fetch_large_data(cache, key, compress_large_data):
    chunk_count = cache.get(make_cache_key(key))
    data = []

    chunk_keys = [make_cache_key('%s-%d' % (key, i))
                  for i in range(int(chunk_count))]
    chunks = cache.get_many(chunk_keys)
    for chunk_key in chunk_keys:
        try:
            data.append(chunks[chunk_key][0])
        except KeyError:
            logging.debug('Cache miss for key %s.' % chunk_key)
            raise MissingChunkError

    data = b''.join(data)

    if compress_large_data:
        data = zlib.decompress(data)

    try:
        unpickler = pickle.Unpickler(StringIO(data))
        data = unpickler.load()
    except Exception as e:
        logging.warning('Unpickle error for cache key "%s": %s.' % (key, e))
        raise e

    return data


def _cache_store_large_data(cache, key, data, expiration, compress_large_data):
    # We store large data in the cache broken into chunks that are 1M in size.
    # To do this easily, we first pickle the data and compress it with zlib.
    # This gives us a string which can be chunked easily. These are then stored
    # individually in the cache as single-element lists (so the cache backend
    # doesn't try to convert binary data to utf8). The number of chunks needed
    # is stored in the cache under the unadorned key
    file = StringIO()
    pickler = pickle.Pickler(file)
    pickler.dump(data)
    data = file.getvalue()

    if compress_large_data:
        data = zlib.compress(data)

    i = 0
    while len(data) > CACHE_CHUNK_SIZE:
        chunk = data[0:CACHE_CHUNK_SIZE]
        data = data[CACHE_CHUNK_SIZE:]
        cache.set(make_cache_key('%s-%d' % (key, i)), [chunk], expiration)
        i += 1
    cache.set(make_cache_key('%s-%d' % (key, i)), [data], expiration)

    cache.set(make_cache_key(key), '%d' % (i + 1), expiration)


def cache_memoize(key, lookup_callable,
                  expiration=getattr(settings, 'CACHE_EXPIRATION_TIME',
                                     DEFAULT_EXPIRATION_TIME),
                  force_overwrite=False,
                  large_data=False,
                  compress_large_data=True):
    """Memoize the results of a callable inside the configured cache.

    Keyword arguments:
    expiration          -- The expiration time for the key.
    force_overwrite     -- If True, the value will always be computed and
                           stored regardless of whether it exists in the cache
                           already.
    large_data          -- If True, the resulting data will be pickled,
                           gzipped, and (potentially) split up into
                           megabyte-sized chunks. This is useful for very
                           large, computationally intensive hunks of data which
                           we don't want to store in a database due to the way
                           things are accessed.
    compress_large_data -- Compresses the data with zlib compression when
                           large_data is True.
    """
    if large_data:
        if not force_overwrite and make_cache_key(key) in cache:
            try:
                data = _cache_fetch_large_data(cache, key, compress_large_data)
                return data
            except Exception as e:
                logging.warning('Failed to fetch large data from cache for '
                                'key %s: %s.' % (key, e))
        else:
            logging.debug('Cache miss for key %s.' % key)

        data = lookup_callable()
        _cache_store_large_data(cache, key, data, expiration,
                                compress_large_data)
        return data

    else:
        key = make_cache_key(key)
        if not force_overwrite and key in cache:
            return cache.get(key)
        data = lookup_callable()

        # Most people will be using memcached, and memcached has a limit of
        # 1MB. Data this big should be broken up somehow, so let's warn
        # about this. Users should hopefully be using large_data=True in this
        # case.
        #
        # XXX - since 'data' may be a sequence that's not a string/unicode,
        #       this can fail. len(data) might be something like '6' but the
        #       data could exceed a megabyte. The best way to catch this would
        #       be an exception, but while python-memcached defines an
        #       exception type for this, it never uses it, choosing instead to
        #       fail silently. WTF.
        if len(data) >= CACHE_CHUNK_SIZE:
            logging.warning('Cache data for key "%s" (length %s) may be too '
                            'big for the cache.' % (key, len(data)))

        try:
            cache.set(key, data, expiration)
        except:
            pass
        return data


def make_cache_key(key):
    """Creates a cache key guaranteed to avoid conflicts and size limits.

    The cache key will be prefixed by the site's domain, and will be
    changed to an MD5SUM if it's larger than the maximum key size.
    """
    try:
        site = Site.objects.get_current()

        # The install has a Site app, so prefix the domain to the key.
        # If a SITE_ROOT is defined, also include that, to allow for multiple
        # instances on the same host.
        site_root = getattr(settings, 'SITE_ROOT', None)

        if site_root:
            key = '%s:%s:%s' % (site.domain, site_root, key)
        else:
            key = '%s:%s' % (site.domain, key)
    except:
        # The install doesn't have a Site app, so use the key as-is.
        pass

    # Strip out any characters that memcached doesn't like in keys
    key = ''.join(ch for ch in key if ch not in ' \t\n\r')

    # Adhere to memcached key size limit
    if len(key) > MAX_KEY_SIZE:
        digest = md5(key.encode('utf-8')).hexdigest()

        # Replace the excess part of the key with a digest of the key
        key = key[:MAX_KEY_SIZE - len(digest)] + digest

    # Make sure this is a non-unicode string, in order to prevent errors
    # with some backends.
    key = key.encode('utf-8')

    return key
