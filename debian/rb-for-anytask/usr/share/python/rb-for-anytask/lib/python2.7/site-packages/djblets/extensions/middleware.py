#
# middleware.py -- Middleware for extensions.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
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

from __future__ import unicode_literals

import threading

from django.conf import settings
from djblets.extensions.manager import get_extension_managers


class ExtensionsMiddleware(object):
    """Middleware to manage extension lifecycles and data."""
    def __init__(self, *args, **kwargs):
        super(ExtensionsMiddleware, self).__init__(*args, **kwargs)

        self.do_expiration_checks = not getattr(settings, 'RUNNING_TEST',
                                                False)
        self._lock = threading.Lock()

    def process_request(self, request):
        if self.do_expiration_checks:
            self._check_expired()

    def process_view(self, request, view, args, kwargs):
        request._djblets_extensions_kwargs = kwargs

    def _check_expired(self):
        """Checks each ExtensionManager for expired extension state.

        When the list of extensions on an ExtensionManager changes, or when
        the configuration of an extension changes, any other threads/processes
        holding onto extensions and configuration will go stale. This function
        will check each of those to see if they need to re-load their
        state.

        This is meant to be called before every HTTP request.
        """
        for extension_manager in get_extension_managers():
            # We're going to check the expiration, and then only lock if it's
            # expired. Following that, we'll check again.
            #
            # We do this in order to prevent locking unnecessarily, which could
            # impact performance or cause a problem if a thread is stuck.
            #
            # We're checking the expiration twice to prevent every blocked
            # thread from making its own attempt to reload the extensions once
            # the first thread holding the lock finishes the reload.
            if extension_manager.is_expired():
                with self._lock:
                    # Check again, since another thread may have already
                    # reloaded.
                    if extension_manager.is_expired():
                        extension_manager.load(full_reload=True)


class ExtensionsMiddlewareRunner(object):
    """Middleware to execute middleware from extensions.

    The process_*() methods iterate over all extensions' middleware, calling
    the given method if it exists. The semantics of how Django executes each
    method are preserved.

    This middleware should be loaded after the main extension middleware
    (djblets.extensions.middleware.ExtensionsMiddleware). It's probably
    a good idea to have it be at the very end so that everything else in the
    core that needs to be initialized is done before any extension's
    middleware is run.
    """

    def process_request(self, request):
        return self._call_until('process_request', False, request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        return self._call_until('process_view', False, request, view_func,
                                view_args, view_kwargs)

    def process_template_response(self, request, response):
        return self._call_chain_response('process_template_response', request,
                                         response)

    def process_response(self, request, response):
        return self._call_chain_response('process_response', request, response)

    def process_exception(self, request, exception):
        return self._call_until('process_exception', True, request, exception)

    def _call_until(self, func_name, reverse, *args, **kwargs):
        """Call extension middleware until a truthy value is returned."""
        r = None

        for f in self._middleware_funcs(func_name, reverse):
            r = f(*args, **kwargs)

            if r:
                break

        return r

    def _call_chain_response(self, func_name, request, response):
        """Call extension middleware, passing response from one to the next."""
        for f in self._middleware_funcs(func_name, True):
            response = f(request, response)

        return response

    def _middleware_funcs(self, func_name, reverse=False):
        """Generator yielding the given middleware function for all extensions.

        If an extension's middleware does not implement 'func_name', it is
        skipped.
        """
        middleware = []

        for mgr in get_extension_managers():
            middleware.extend(mgr.middleware)

        if reverse:
            middleware.reverse()

        for m in middleware:
            f = getattr(m, func_name, None)

            if f:
                yield f
