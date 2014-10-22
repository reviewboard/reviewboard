from __future__ import unicode_literals

import logging
import socket

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except:
        memcache = None

from django.conf import settings
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS


def get_memcached_hosts():
    """Returns the hosts currently configured for memcached."""
    if not memcache:
        return None

    cache_info = settings.CACHES[DEFAULT_FORWARD_CACHE_ALIAS]
    backend = cache_info['BACKEND']
    locations = cache_info.get('LOCATION', [])

    if (not backend.startswith('django.core.cache.backends.memcached') or
            not locations):
        return []

    if not isinstance(locations, list):
        locations = [locations]

    return locations


def get_has_cache_stats():
    """
    Returns whether or not cache stats are supported.
    """
    return get_memcached_hosts() is not None


def get_cache_stats():
    """
    Returns a dictionary containing information on the current cache stats.
    This only supports memcache.
    """
    hostnames = get_memcached_hosts()

    if not hostnames:
        return None

    all_stats = []

    for hostname in hostnames:
        try:
            host, port = hostname.split(":")
        except ValueError:
            logging.error('Invalid cache hostname "%s"' % hostname)
            continue

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, int(port)))
        except socket.error:
            s.close()
            continue

        s.send(b"stats\r\n")
        data = s.recv(2048).decode('ascii')
        s.close()

        stats = {}

        for line in data.splitlines():
            info = line.split(" ")

            if info[0] == "STAT":
                try:
                    value = int(info[2])
                except ValueError:
                    value = info[2]

                stats[info[1]] = value

        if stats['cmd_get'] == 0:
            stats['hit_rate'] = 0
            stats['miss_rate'] = 0
        else:
            stats['hit_rate'] = 100 * stats['get_hits'] / stats['cmd_get']
            stats['miss_rate'] = 100 * stats['get_misses'] / stats['cmd_get']

        all_stats.append((hostname, stats))

    return all_stats
