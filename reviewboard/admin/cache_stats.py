from __future__ import unicode_literals

import logging
import socket

from django.conf import settings
from djblets.cache.forwarding_backend import DEFAULT_FORWARD_CACHE_ALIAS


logger = logging.getLogger(__name__)


def get_memcached_hosts():
    """Return the hosts currently configured for memcached.

    Returns:
        list of unicode:
        A list of memcached hostnames or UNIX paths.
    """
    cache_info = settings.CACHES[DEFAULT_FORWARD_CACHE_ALIAS]
    backend = cache_info['BACKEND']
    locations = cache_info.get('LOCATION', [])

    if 'memcached' not in backend or not locations:
        locations = []
    elif not isinstance(locations, list):
        locations = [locations]

    return locations


def get_has_cache_stats():
    """Return whether or not cache stats are supported.

    Returns:
        bool:
        ``True`` if cache stats are supported for the current cache setup.
        ``False`` if cache stats are not supported.
    """
    return len(get_memcached_hosts()) > 0


def get_cache_stats():
    """Return statistics for all supported cache backends.

    This only supports memcached backends.

    Returns:
        list of tuple:
        Each list item corresponds to one configured memcached server.
        The item is a tuple in the form of ``(hostname, stats)``, where
        ``stats`` is a dictionary with statistics from the cache server.

        If no memcached servers are configured, this will return ``None``
        instead.
    """
    hostnames = get_memcached_hosts()

    if not hostnames:
        return None

    all_stats = []

    for hostname in hostnames:
        try:
            host, port = hostname.split(':')
        except ValueError:
            # Assume this is a hostname without a port.
            socket_af = socket.AF_INET
            host = hostname
            port = 11211

        if host == 'unix':
            socket_af = socket.AF_UNIX
            connect_param = port
        else:
            socket_af = socket.AF_INET
            connect_param = (host, int(port))

        s = socket.socket(socket_af, socket.SOCK_STREAM)

        try:
            s.connect(connect_param)
        except socket.error:
            logger.error('Unable to connect to "%s"' % hostname)
            s.close()
            continue

        s.send(b'stats\r\n')
        data = s.recv(2048).decode('ascii')
        s.close()

        stats = {}

        for line in data.splitlines():
            info = line.split(' ')

            if info[0] == 'STAT' and len(info) == 3:
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
