import re
import socket

try:
    import cmemcache as memcache
except ImportError:
    try:
        import memcache
    except:
        memcache = None

from django.conf import settings


def get_memcached_hosts():
    """
    Returns the hosts currently configured for memcached.
    """
    if not memcache:
        return None

    m = re.match("memcached://([.\w]+:\d+;?)", settings.CACHE_BACKEND)

    if m:
        return m.group(1).split(";")

    return None


def get_has_cache_stats():
    """
    Returns whether or not cache stats are supported.
    """
    return get_memcached_hosts() != None


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
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host, port = hostname.split(":")

        try:
            s.connect((host, int(port)))
        except socket.error:
            s.close()
            continue

        s.send("stats\r\n")
        data = s.recv(1024)
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
