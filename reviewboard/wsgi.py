"""WSGI application for Review Board.

This is the main WSGI entrypoint for loading Review Board. This SHOULD NOT
be modified from the version shipped with Review Board!

To use this, make sure you set the :envvar:`REVIEWBOARD_SITEDIR` environment
variable to point to the absolute path of the Review Board site directory.
"""

from __future__ import unicode_literals

import os
import sys


sitedir = os.environ.get('REVIEWBOARD_SITEDIR')

if not sitedir:
    raise RuntimeError(
        'The REVIEWBOARD_SITEDIR environment variable must be set to the '
        'Review Board site directory.')

conf_dir = os.path.join(sitedir, 'conf')

os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'
os.environ['PYTHON_EGG_CACHE'] = os.path.join(sitedir, 'tmp', 'egg_cache')
os.environ['HOME'] = os.path.join(sitedir, 'data')
os.environ['PYTHONPATH'] = '%s:%s' % (conf_dir,
                                      os.environ.get('PYTHONPATH', ''))

sys.path.insert(0, conf_dir)


from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
