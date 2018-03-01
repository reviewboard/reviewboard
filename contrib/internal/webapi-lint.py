#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import inspect
import os
import re
import sys

scripts_dir = os.path.abspath(os.path.dirname(__file__))
rb_dir = os.path.abspath(os.path.join(scripts_dir, '..', '..'))

sys.path.insert(0, rb_dir)
sys.path.insert(0, os.path.join(scripts_dir, 'conf'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

from django.utils import six
from djblets.webapi.errors import (DOES_NOT_EXIST, NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from djblets.webapi.fields import BaseAPIFieldType
from reviewboard.webapi.resources import resources

# We have to fetch this first in order to build the tree, before accessing
# subclasses.
root_resource = resources.root
root_resource.get_url_patterns()

from reviewboard.webapi.resources import WebAPIResource
from reviewboard.webapi.resources.review_request import (
    ReviewRequestDraftResource,
    ReviewRequestResource)


resource_instances = {}
counts = {
    'warnings': 0,
    'errors': 0,
    'criticals': 0,
}


class Linter(object):
    def warning(self, text):
        print('[W] %s' % self.build_log_text(text))
        counts['warnings'] += 1

    def error(self, text):
        print('[E] %s' % self.build_log_text(text))
        counts['errors'] += 1

    def critical(self, text):
        print('[C] %s' % self.build_log_text(text))
        counts['criticals'] += 1

    def build_log_text(self, text):
        return text


class ResourceLinter(Linter):
    def __init__(self, resource):
        self.resource = resource

    def lint(self):
        if isinstance(self.resource.fields, tuple):
            self.warning('fields should be a dictionary')

        if not self.has_docs(self.resource):
            self.error('Missing a class docstring')

        self.lint_fields(self.resource.fields, '%s.fields' %
                         self.resource.__name__)

        # Check that the HTTP method handlers contain everything we need.
        if not self.resource.singleton:
            self.lint_http_method_handler('GET', 'get_list',
                                          need_check_login_required=True)

        self.lint_http_method_handler('GET', 'get',
                                      need_check_login_required=True)
        self.lint_http_method_handler('PUT', 'update',
                                      need_login_required=True,
                                      need_request_fields=True,
                                      need_response_errors=True)
        self.lint_http_method_handler('POST', 'create',
                                      need_login_required=True,
                                      need_request_fields=True,
                                      need_response_errors=True)
        self.lint_http_method_handler('DELETE', 'delete',
                                      need_login_required=True)

        if self.resource.model:
            # Check that we have all the permission checking functions we need.
            # Even if they'd use default behavior from WebAPIResource, they
            # should be defined explicitly in the resource class.
            if (self.resource.has_access_permissions.im_func is
                WebAPIResource.has_access_permissions.im_func):
                self.error("Missing custom 'has_access_permissions' method")

            if ('PUT' in self.resource.allowed_methods and
                (self.resource.has_modify_permissions.im_func is
                 WebAPIResource.has_modify_permissions.im_func)):
                self.error("Missing custom 'has_modify_permissions' method")

            if ('DELETE' in self.resource.allowed_methods and
                (self.resource.has_delete_permissions.im_func is
                 WebAPIResource.has_delete_permissions.im_func)):
                self.error("Missing custom 'has_delete_permissions' method")

    def lint_http_method_handler(self, http_method, func_name,
                                 need_login_decorator=True,
                                 need_check_login_required=False,
                                 need_login_required=False,
                                 need_check_local_site=True,
                                 need_response_errors=False,
                                 need_request_fields=False):
        if http_method not in self.resource.allowed_methods:
            return

        func = getattr(self.resource, func_name)
        assert func

        if not self.has_docs(func):
            self.warning("'%s' method is missing a docstring" % func_name)

        if need_login_decorator:
            has_login_required = hasattr(func, 'login_required')
            has_check_login_required = hasattr(func, 'checks_login_required')

            if need_login_required and not has_login_required:
                self.error("'%s' method missing @webapi_login_required "
                           "decorator"
                           % func_name)
            elif (need_check_login_required and
                  not has_check_login_required and
                  not has_login_required):
                self.error("'%s' method missing @webapi_check_login_required "
                           "decorator"
                           % func_name)
            elif not has_login_required and not has_check_login_required:
                self.error("'%s' method missing @webapi_login_required or "
                           "@webapi_check_login_required decorator"
                           % func_name)

        if need_check_local_site and not hasattr(func, 'checks_local_site'):
            self.error("'%s' method missing @webapi_check_local_site "
                       "decorator"
                       % func_name)

        if need_response_errors and not hasattr(func, 'response_errors'):
            self.warning("'%s' method missing @webapi_response_errors "
                         "decorator"
                         % func_name)

        if (need_request_fields and
            not hasattr(func, 'required_fields') and
            not hasattr(func, 'optional_fields')):
            self.warning("'%s' method missing @webapi_request_fields decorator"
                         % func_name)

        if hasattr(func, 'response_errors'):
            if (not self.resource.singleton and
                DOES_NOT_EXIST not in func.response_errors):
                self.warning("'%s' method missing DOES_NOT_EXIST in "
                             "@webapi_response_errors"
                             % func_name)

            if ((need_check_local_site or need_login_decorator) and
                PERMISSION_DENIED not in func.response_errors):
                self.warning("'%s' method missing PERMISSION_DENIED in "
                             "@webapi_response_errors"
                             % func_name)

            if (need_login_decorator and
                NOT_LOGGED_IN not in func.response_errors):
                self.warning("'%s' method missing NOT_LOGGED_IN in "
                             "@webapi_response_errors"
                             % func_name)

        where = "'%s' method" % func_name

        if hasattr(func, 'required_fields'):
            self.lint_fields(func.required_fields, where)

        if hasattr(func, 'optional_fields'):
            self.lint_fields(func.optional_fields, where)

    def lint_fields(self, fields, where):
        """Check that a list of fields can be introspected properly.

        Args:
            fields (list of dict):
                The list of field information dictionaries.

            where (unicode):
                A string indicating where this list of fields lives,
                for use in error messages.
        """
        for field_name, field_info in six.iteritems(fields):
            try:
                field_type = field_info['type']
            except KeyError:
                self.error("Missing 'type' field for field '%s' on %s"
                           % (field_name, where))

            if (inspect.isclass(field_type) and
                issubclass(field_type, BaseAPIFieldType)):
                # Make sure the class can be instantiated.
                try:
                    field_type(field_info)
                except Exception as e:
                    self.critical("Error instantiating field type %r for "
                                  "field '%s' on %s: %s"
                                  % (field_type, field_name, where, e))
            else:
                self.warning("Field type %r for field '%s' on %s needs to "
                             "be updated to a modern field type"
                             % (field_type, field_name, where))

    def build_log_text(self, text):
        return '%s: %s' % (self.resource.__name__, text)

    def has_docs(self, func_or_class):
        doc = func_or_class.__doc__

        return doc is not None and doc.strip() != ''


class UnitTestLinter(Linter):
    CLASS_NAME_RE = re.compile(' ([A-Z][A-Za-z]+Resource)')

    def __init__(self, filename):
        self.filename = filename

    def lint(self):
        module_name = os.path.splitext(self.filename)[0]

        if isinstance(module_name, six.text_type):
            module_name = module_name.encode('utf-8')

        try:
            module = __import__('reviewboard.webapi.tests',
                                {}, {}, [module_name])
            module = getattr(module, module_name)
        except ImportError as e:
            self.critical('Unable to import %s: %s' % (self.filename, e))
            return

        has_resource_item_tests = hasattr(module, 'ResourceItemTests')
        has_resource_list_tests = hasattr(module, 'ResourceListTests')
        has_resource_tests = hasattr(module, 'ResourceTests')

        if (not has_resource_item_tests and
            not has_resource_list_tests and
            not has_resource_tests):
            self.error("Couldn't find test suites named ResourceItemTests, "
                       "ResourceListTests, or ResourceTests")
        elif has_resource_list_tests and not has_resource_item_tests:
            self.error('Missing ResourceItemTests')
        elif has_resource_item_tests and not has_resource_list_tests:
            self.error('Missing ResourceListTests')

        if has_resource_list_tests:
            self.lint_test_class(getattr(module, 'ResourceListTests'),
                                 list_suite=True)

        if has_resource_item_tests:
            self.lint_test_class(getattr(module, 'ResourceItemTests'),
                                 item_suite=True)

        if has_resource_tests:
            self.lint_test_class(getattr(module, 'ResourceTests'),
                                 singleton_suite=True)

    def lint_test_class(self, test_class, list_suite=False, item_suite=False,
                        singleton_suite=False):
        if test_class is None:
            # This has been explicitly set to None in the test file to
            # let the linter know it's aware of the check for the class,
            # but won't provide one.
            return

        resource = self.get_resource_class(test_class)

        if resource is None:
            # The error is already handled.
            return

        test_class_name = test_class.__name__

        if singleton_suite and not resource.singleton:
            self.error("Non-singleton resource has test suite named "
                       "'%s'" % test_class_name)
            return
        elif not singleton_suite and resource.singleton:
            self.error("Singleton resource has test suite named "
                       "'%s'" % test_class_name)
            return

        test_http_methods = getattr(test_class, 'test_http_methods',
                                    ('DELETE', 'GET', 'POST', 'PUT'))

        if 'GET' in test_http_methods:
            if 'GET' in resource.allowed_methods:
                self.lint_test_function(test_class, 'test_get')
                self.lint_test_function(test_class, 'test_get_with_site')
                self.lint_test_function(test_class,
                                        'test_get_with_site_no_access')

                if self.should_test_private_review_requests(resource):
                    self.lint_test_function(
                        test_class, 'test_get_with_private_group')
                    self.lint_test_function(
                        test_class, 'test_get_with_private_group_no_access')
                    self.lint_test_function(
                        test_class, 'test_get_with_private_repo')
                    self.lint_test_function(
                        test_class, 'test_get_with_private_repo_no_access')
            else:
                self.lint_test_function(test_class,
                                        'test_get_method_not_allowed',
                                        important=False)

        if not item_suite and 'POST' in test_http_methods:
            # These should be checked against list and singleton resources.
            if 'POST' in resource.allowed_methods:
                self.lint_test_function(test_class, 'test_post')
                self.lint_test_function(test_class, 'test_post_with_site')
                self.lint_test_function(test_class,
                                        'test_post_with_site_no_access')
            else:
                self.lint_test_function(test_class,
                                        'test_post_method_not_allowed',
                                        important=False)

        if not list_suite:
            # These should be checked against item and singleton resources.
            if 'DELETE' in test_http_methods:
                if 'DELETE' in resource.allowed_methods:
                    self.lint_test_function(test_class, 'test_delete')
                    self.lint_test_function(test_class,
                                            'test_delete_with_site')
                    self.lint_test_function(test_class,
                                            'test_delete_with_site_no_access')
                    self.lint_test_function(test_class,
                                            'test_delete_not_owner')
                else:
                    self.lint_test_function(test_class,
                                            'test_delete_method_not_allowed',
                                            important=False)

            if 'PUT' in test_http_methods:
                if 'PUT' in resource.allowed_methods:
                    self.lint_test_function(test_class, 'test_put')
                    self.lint_test_function(test_class, 'test_put_with_site')
                    self.lint_test_function(test_class,
                                            'test_put_with_site_no_access')
                    self.lint_test_function(test_class,
                                            'test_put_not_owner')
                else:
                    self.lint_test_function(test_class,
                                            'test_put_method_not_allowed',
                                            important=False)

    def lint_test_function(self, test_class, func_name, important=True):
        func = getattr(test_class, func_name, None)

        if not func:
            msg = ("Missing test function '%s.%s'"
                   % (test_class.__name__, func_name))

            if important:
                self.error(msg)
            else:
                self.warning(msg)

            return

    def should_test_private_review_requests(self, resource):
        return (resource is not ReviewRequestResource and
                self.has_review_request_ancestor(resource) and
                not self.has_review_request_draft_ancestor(resource))

    def has_review_request_ancestor(self, resource_class):
        def _check_resource(resource):
            if resource.__class__ is ReviewRequestResource:
                return True
            elif resource._parent_resource:
                return _check_resource(resource._parent_resource)
            else:
                return None

        return _check_resource(resource_instances[resource_class.__name__])

    def has_review_request_draft_ancestor(self, resource_class):
        def _check_resource(resource):
            if resource.__class__ is ReviewRequestDraftResource:
                return True
            elif resource._parent_resource:
                return _check_resource(resource._parent_resource)
            else:
                return None

        return _check_resource(resource_instances[resource_class.__name__])

    def build_log_text(self, text):
        return '%s: %s' % (self.filename, text)

    def get_resource_class(self, test_class):
        m = self.CLASS_NAME_RE.search(test_class.__doc__ or '')

        if m:
            resource_class_name = m.group(1)
            resource_instance = resource_instances.get(resource_class_name)

            if resource_instance is None:
                self.critical("Unable to find resource class '%s' for '%s'"
                              % (resource_class_name, test_class.__name__))
                return None

            return resource_instance.__class__

        self.critical("Unable to find resource class in docstring for '%s'"
                      % test_class.__name__)

        return None


def walk_resources(resource):
    resource_instances[resource.__class__.__name__] = resource

    linter = ResourceLinter(resource)
    linter.lint()

    for child in resource.list_child_resources:
        walk_resources(child)

    for child in resource.item_child_resources:
        walk_resources(child)


def main():
    walk_resources(root_resource)

    webapi_dir = os.path.join(rb_dir, 'reviewboard', 'webapi')
    tests_dir = os.path.join(webapi_dir, 'tests')

    for filename in os.listdir(tests_dir):
        if filename.startswith('test_') and filename.endswith('.py'):
            linter = UnitTestLinter(filename)
            linter.lint()

    if counts['warnings'] or counts['errors']:
        print()
        print('%(warnings)s warnings, %(errors)s errors, '
              '%(criticals)s criticals' % counts)
    else:
        print('All tests pass.')

if __name__ == '__main__':
    main()
