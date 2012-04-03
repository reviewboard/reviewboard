#!/usr/bin/env python

import os
import sys

from django.core.management import call_command, setup_environ


if __name__ == '__main__':
    scripts_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(scripts_dir, '..', '..')))
    sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

    os.putenv('FORCE_BUILD_MEDIA', '1')

    import reviewboard.settings
    setup_environ(reviewboard.settings)

    ret = call_command('collectstatic', interactive=False, verbosity=2)
    sys.exit(ret)
