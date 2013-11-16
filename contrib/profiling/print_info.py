#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import pstats
import sys


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: %s [file.prof]" % sys.argv[0])
        sys.exit(1)

    s = pstats.Stats(sys.argv[1])
    s.sort_stats('time')

    print('==== Largest 10% ====')
    s.print_stats(.1)

    print('==== Largest 1% of Callers ====')
    s.print_callers(.01)
