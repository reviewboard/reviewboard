#
# decorators.py -- Decorators used for webapi views
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
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

from __future__ import unicode_literals

from django.http import HttpRequest
from django.utils import six

from djblets.webapi.errors import (NOT_LOGGED_IN, PERMISSION_DENIED,
                                   INVALID_FORM_DATA)


SPECIAL_PARAMS = ('api_format', 'callback', '_method', 'expand')


def _find_httprequest(args):
    if isinstance(args[0], HttpRequest):
        request = args[0]
    else:
        # This should be in a class then.
        assert len(args) > 1
        request = args[1]
        assert isinstance(request, HttpRequest)

    return request


def copy_webapi_decorator_data(from_func, to_func):
    """Copies and merges data from one decorated function to another.

    This will copy over the standard function information (name, docs,
    and dictionary data), but will also handle intelligently merging
    together data set by webapi decorators, such as the list of
    possible errors.
    """
    had_errors = (hasattr(to_func, 'response_errors') or
                  hasattr(from_func, 'response_errors'))
    had_fields = (hasattr(to_func, 'required_fields') or
                  hasattr(from_func, 'required_fields'))

    from_errors = getattr(from_func, 'response_errors', set())
    to_errors = getattr(to_func, 'response_errors', set())
    from_required_fields = getattr(from_func, 'required_fields', {}).copy()
    from_optional_fields = getattr(from_func, 'optional_fields', {}).copy()
    to_required_fields = getattr(to_func, 'required_fields', {}).copy()
    to_optional_fields = getattr(to_func, 'optional_fields', {}).copy()

    to_func.__name__ = from_func.__name__
    to_func.__doc__ = from_func.__doc__
    to_func.__dict__.update(from_func.__dict__)

    # Only copy if one of the two functions had this already.
    if had_errors:
        to_func.response_errors = to_errors.union(from_errors)

    if had_fields:
        to_func.required_fields = from_required_fields
        to_func.required_fields.update(to_required_fields)
        to_func.optional_fields = from_optional_fields
        to_func.optional_fields.update(to_optional_fields)

    return to_func


def webapi_decorator(decorator):
    """Decorator for simple webapi decorators.

    This is meant to be used for other webapi decorators in order to
    intelligently preserve information, like the possible response
    errors. It handles merging lists of errors and other information
    instead of overwriting one list with another, as simple_decorator
    would do.
    """
    return copy_webapi_decorator_data(
        decorator,
        lambda f: copy_webapi_decorator_data(f, decorator(f)))


@webapi_decorator
def webapi(view_func):
    """Indicates that a view is a Web API handler."""
    return view_func


def webapi_response_errors(*errors):
    """Specifies the type of errors that the response may return.

    This can be used for generating documentation or schemas that cover
    the possible error responses of methods on a resource.
    """
    @webapi_decorator
    def _dec(view_func):
        def _call(*args, **kwargs):
            return view_func(*args, **kwargs)

        _call.response_errors = set(errors)

        return _call

    return _dec


@webapi_decorator
def webapi_login_required(view_func):
    """
    Checks that the user is logged in before invoking the view. If the user
    is not logged in, a NOT_LOGGED_IN error (HTTP 401 Unauthorized) is
    returned.
    """
    @webapi_response_errors(NOT_LOGGED_IN)
    def _checklogin(*args, **kwargs):
        request = _find_httprequest(args)

        if request.user.is_authenticated():
            return view_func(*args, **kwargs)
        else:
            return NOT_LOGGED_IN

    _checklogin.login_required = True

    return _checklogin


def webapi_permission_required(perm):
    """
    Checks that the user is logged in and has the appropriate permissions
    to access this view. A PERMISSION_DENIED error is returned if the user
    does not have the proper permissions.
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED)
        def _checkpermissions(*args, **kwargs):
            request = _find_httprequest(args)

            if not request.user.is_authenticated():
                response = NOT_LOGGED_IN
            elif not request.user.has_perm(perm):
                response = PERMISSION_DENIED
            else:
                response = view_func(*args, **kwargs)

            return response

        return _checkpermissions

    return _dec


def webapi_request_fields(required={}, optional={}, allow_unknown=False):
    """Validates incoming fields for a request.

    This is a helpful decorator for ensuring that the fields in the request
    match what the caller expects.

    If any field is set in the request that is not in either ``required``
    or ``optional`` and ``allow_unknown`` is True, the response will be an
    INVALID_FORM_DATA error. The exceptions are the special fields
    ``method`` and ``callback``.

    If any field in ``required`` is not passed in the request, these will
    also be listed in the INVALID_FORM_DATA response.

    The ``required`` and ``optional`` parameters are dictionaries
    mapping field name to an info dictionary, which contains the following
    keys:

      * ``type`` - The data type for the field.
      * ```description`` - A description of the field.

    For example:

        @webapi_request_fields(required={
            'name': {
                'type': str,
                'description': 'The name of the object',
            }
        })
    """
    @webapi_decorator
    def _dec(view_func):
        @webapi_response_errors(INVALID_FORM_DATA)
        def _validate(*args, **kwargs):
            request = _find_httprequest(args)

            if request.method == 'GET':
                request_fields = request.GET
            else:
                request_fields = request.POST

            extra_fields = {}
            invalid_fields = {}
            supported_fields = required.copy()
            supported_fields.update(optional)

            for field_name, value in six.iteritems(request_fields):
                if field_name in SPECIAL_PARAMS:
                    # These are special names and can be ignored.
                    continue

                if field_name not in supported_fields:
                    if allow_unknown:
                        extra_fields[field_name] = value
                    else:
                        invalid_fields[field_name] = ['Field is not supported']

            for field_name, info in six.iteritems(required):
                temp_fields = request_fields

                if info['type'] == file:
                    temp_fields = request.FILES

                if temp_fields.get(field_name, None) is None:
                    invalid_fields[field_name] = ['This field is required']

            new_kwargs = kwargs.copy()
            new_kwargs['extra_fields'] = extra_fields

            for field_name, info in six.iteritems(supported_fields):
                if isinstance(info['type'], file):
                    continue

                value = request_fields.get(field_name, None)

                if value is not None:
                    if type(info['type']) in (list, tuple):
                        # This is a multiple-choice. Make sure the value is
                        # valid.
                        choices = info['type']

                        if value not in choices:
                            invalid_fields[field_name] = [
                                '"%s" is not a valid value. Valid values '
                                'are: %s' % (
                                    value,
                                    ', '.join(['"%s"' % choice
                                               for choice in choices])
                                )
                            ]
                    else:
                        try:
                            if issubclass(info['type'], bool):
                                value = value in (1, "1", True, "True", "true")
                            elif issubclass(info['type'], int):
                                try:
                                    value = int(value)
                                except ValueError:
                                    invalid_fields[field_name] = [
                                        '"%s" is not an integer' % value
                                    ]
                        except TypeError:
                            # The field isn't a class type. This is a
                            # coding error on the developer's side.
                            raise TypeError('"%s" is not a valid field type' %
                                            info['type'])

                    new_kwargs[field_name] = value

            if invalid_fields:
                return INVALID_FORM_DATA, {
                    'fields': invalid_fields,
                }

            return view_func(*args, **new_kwargs)

        _validate.required_fields = required.copy()
        _validate.optional_fields = optional.copy()

        if hasattr(view_func, 'required_fields'):
            _validate.required_fields.update(view_func.required_fields)

        if hasattr(view_func, 'optional_fields'):
            _validate.optional_fields.update(view_func.optional_fields)

        return _validate

    return _dec
