#
# testing.py -- Some classes useful for unit testing django-based applications
#
# Copyright (c) 2007-2010  Christian Hammond
# Copyright (c) 2007-2010  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import print_function, unicode_literals

import imp
import re
import socket
import sys
import threading

import django
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers import basehttp
from django.db.models.loading import cache, load_app
from django.template import Node
from django.test import testcases
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule


class StubNodeList(Node):
    def __init__(self, default_text):
        self.default_text = default_text

    def render(self, context):
        return self.default_text


class StubParser:
    def __init__(self, default_text):
        self.default_text = default_text

    def parse(self, until):
        return StubNodeList(self.default_text)

    def delete_first_token(self):
        pass


class TestCase(testcases.TestCase):
    """Base class for test cases.

    Individual tests on this TestCase can use the :py:func:`add_fixtures`
    decorator to add or replace the fixtures used for the test.
    """
    ws_re = re.compile(r'\s+')

    def __call__(self, *args, **kwargs):
        method = getattr(self, self._testMethodName)
        old_fixtures = getattr(self, 'fixtures', [])

        if hasattr(method, '_fixtures'):
            if getattr(method, '_replace_fixtures'):
                self.fixtures = method._fixtures
            else:
                self.fixtures = old_fixtures + method._fixtures

        super(TestCase, self).__call__(*args, **kwargs)

        if old_fixtures:
            self.fixtures = old_fixtures

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc


class TestModelsLoaderMixin(object):
    """Allows unit test moduls to provide models to test against.

    This allows a unit test file to provide models that will be synced to the
    database and flushed after tests. These can be tested against in any unit
    tests.

    Typically, Django requires any test directories to be pre-added to
    INSTALLED_APPS, and a models.py made available (in Django < 1.7), in
    order for models to be created in the test database.

    This mixin works around this by dynamically adding the module to
    INSTALLED_APPS and forcing the database to be synced. It also will
    generate a fake 'models' module to satisfy Django's requirement, if one
    doesn't already exist.

    By default, this will assume that the test class's module is the one that
    should be added to INSTALLED_APPS. This can be changed by overriding
    :py:attr:`tests_app`.
    """
    tests_app = None

    @classmethod
    def setUpClass(cls):
        super(TestModelsLoaderMixin, cls).setUpClass()

        cls._tests_loader_models_mod = None

        if not cls.tests_app:
            cls.tests_app = cls.__module__

        if django.VERSION < (1, 7):
            tests_module = import_module(cls.tests_app)

            if not module_has_submodule(tests_module, 'models'):
                # To satisfy Django < 1.7, we need to have a 'models' module,
                # in order for the app to be considered.
                models_mod_name = '%s.models' % cls.tests_app
                models_mod = imp.new_module(models_mod_name)

                # Django needs a value here. Doesn't matter what it is.
                models_mod.__file__ = ''

                cls._tests_loader_models_mod = models_mod

    @classmethod
    def tearDownClass(cls):
        super(TestModelsLoaderMixin, cls).tearDownClass()

        # Set this free so the garbage collector can eat it.
        cls._tests_loader_models_mod = None

    def setUp(self):
        super(TestModelsLoaderMixin, self).setUp()

        # If we made a fake 'models' module, add it to sys.modules.
        models_mod = self._tests_loader_models_mod

        if models_mod:
            sys.modules[models_mod.__name__] = models_mod

        self._models_loader_old_settings = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + [
            self.tests_app,
        ]

        load_app(self.tests_app)
        call_command('syncdb', verbosity=0, interactive=False)

    def tearDown(self):
        super(TestModelsLoaderMixin, self).tearDown()

        call_command('flush', verbosity=0, interactive=False)

        settings.INSTALLED_APPS = self._models_loader_old_settings

        # If we added a fake 'models' module to sys.modules, remove it.
        models_mod = self._tests_loader_models_mod

        if models_mod:
            del cache.app_store[models_mod]

            try:
                del sys.modules[models_mod.__name__]
            except KeyError:
                pass

        cache._get_models_cache.clear()


class TagTest(TestCase):
    """Base testing setup for custom template tags"""

    def setUp(self):
        self.parser = StubParser(self.getContentText())

    def getContentText(self):
        return "content"


# The following is all based on the code at
# http://trac.getwindmill.com/browser/trunk/windmill/authoring/djangotest.py,
# which is based on the changes submitted for Django in ticket 2879
# (http://code.djangoproject.com/ticket/2879)
#
# A lot of this can go away when/if this patch is committed to Django.

# Code from django_live_server_r8458.diff
#     @ http://code.djangoproject.com/ticket/2879#comment:41
# Editing to monkey patch django rather than be in trunk

class StoppableWSGIServer(basehttp.WSGIServer):
    """
    WSGIServer with short timeout, so that server thread can stop this server.
    """
    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class WSGIRequestHandler(basehttp.WSGIRequestHandler):
    """A custom WSGIRequestHandler that logs all output to stdout.

    Normally, WSGIRequestHandler will color-code messages and log them
    to stderr. It also filters out admin and favicon.ico requests. We don't
    need any of this, and certainly don't want it in stderr, as we'd like
    to only show it on failure.
    """
    def log_message(self, format, *args):
        print(format % args)


class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """
        Sets up test server and database and loops over handling http requests.
        """
        try:
            handler = basehttp.AdminMediaHandler(WSGIHandler())
            server_address = (self.address, self.port)
            httpd = StoppableWSGIServer(server_address,
                                        WSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except basehttp.WSGIServerException as e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        from django.conf import settings

        if hasattr(settings, 'DATABASES'):
            db_engine = settings.DATABASES['default']['ENGINE']
            test_db_name = settings.DATABASES['default']['TEST_NAME']
        else:
            db_engine = settings.DATABASE_ENGINE
            test_db_name = settings.TEST_DATABASE_NAME

        if (db_engine.endswith('sqlite3') and
            (not test_db_name or test_db_name == ':memory:')):
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                testcases.call_command('loaddata', verbosity=0, *self.fixtures)

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)
