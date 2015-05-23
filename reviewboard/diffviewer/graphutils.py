from __future__ import unicode_literals

import heapq
import itertools
from collections import defaultdict

from django.utils import six


def find_shortest_distances(vertex, graph):
    """Find the shortest distances from the given vertex to all other vertices.

    This is implemented with Dijkstra's algorithm.

    :param vertex: The vertex to determine the distances from. This should be a
    key in the graph.

    :param graph: The graph to use. This should be an adjacency list as a dict,
    where the keys are vertices in the graph and the values are list of
    adjacent vertices.

    :return: A dict where the keys are vertices in the graph and the values
    are the distances from ``vertex`` to that vertex. If there is not a path
    from ``vertex`` to  some other vertex ``u`` then the value corresponding to
    the key ``u`` is positive infinity.
    """
    distance = defaultdict(lambda: float('inf'))
    distance[vertex] = 0

    # Not all vertices appear in either the keys or the values.
    vertices = set(itertools.chain(six.iterkeys(graph),
                                   *six.itervalues(graph)))

    queue = [(distance[v], v) for v in vertices]
    heapq.heapify(queue)

    while queue:
        dist, vertex = heapq.heappop(queue)

        if vertex in graph:
            for adjacent in graph[vertex]:
                new_distance = dist + 1
                old_distance = distance[adjacent]

                if new_distance < old_distance:
                    distance[adjacent] = new_distance

                    for i, entry in enumerate(queue):
                        if entry[1] == adjacent:
                            queue[i] = (new_distance, entry[1])
                            heapq.heapify(queue)
                            break

    # Prevent the default factory from generating more items.
    distance.default_factory = None

    return distance
