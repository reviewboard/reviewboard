"""Unit tests for reviewboard.extensions.hooks.APIExtraDataAccessHook."""

from __future__ import unicode_literals

from djblets.extensions.extension import ExtensionInfo
from djblets.extensions.models import RegisteredExtension
from djblets.registries.errors import AlreadyRegisteredError, RegistrationError
from kgb import SpyAgency
from mock import Mock

from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import APIExtraDataAccessHook
from reviewboard.extensions.tests.testcases import ExtensionManagerMixin
from reviewboard.webapi.base import ExtraDataAccessLevel, WebAPIResource
from reviewboard.webapi.tests.base import BaseWebAPITestCase


class GenericTestResource(WebAPIResource):
    name = 'test'
    uri_object_key = 'test_id'
    extra_data = {}
    item_mimetype = 'application/vnd.reviewboard.org.test+json'

    fields = {
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the test resource. '
                           'This can be set by the API or extensions.',
        },
    }

    allowed_methods = ('GET', 'PUT')

    def get(self, *args, **kwargs):
        return 200, {
            'test': {
                'extra_data': self.serialize_extra_data_field(self)
            }
        }

    def put(self, request, *args, **kwargs):
        fields = request.POST.dict()
        self.import_extra_data(self, self.extra_data, fields)

        return 200, {
            'test': self.extra_data
        }

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return True


class APIExtraDataAccessHookTests(ExtensionManagerMixin, SpyAgency,
                                  BaseWebAPITestCase):
    """Testing APIExtraDataAccessHook."""

    fixtures = ['test_users']

    class EverythingPrivateHook(APIExtraDataAccessHook):
        """Hook which overrides callable to return all fields as private."""

        def get_extra_data_state(self, key_path):
            self.called = True
            return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE

    class InvalidCallableHook(APIExtraDataAccessHook):
        """Hook which implements an invalid callable"""

        get_extra_data_state = 'not a callable'

    def setUp(self):
        super(APIExtraDataAccessHookTests, self).setUp()

        self.resource_class = GenericTestResource
        self.resource = self.resource_class()

        class DummyExtension(Extension):
            resources = [self.resource]
            registration = RegisteredExtension()

        self.extension_class = DummyExtension

        entry_point = Mock()
        entry_point.load = lambda: self.extension_class
        entry_point.dist = Mock()
        entry_point.dist.project_name = 'TestProjectName'
        entry_point.dist.get_metadata_lines = lambda *args: [
            'Name: Resource Test Extension',
        ]

        self.manager._entrypoint_iterator = lambda: [entry_point]

        self.manager.load()
        self.extension = self.manager.enable_extension(self.extension_class.id)
        self.registered = True

        self.extension_class.info = ExtensionInfo.create_from_entrypoint(
            entry_point, self.extension_class)

        self.url = self.resource.get_item_url(test_id=1)
        self.resource.extra_data = {
            'public': 'foo',
            'private': 'secret',
            'readonly': 'bar',
        }

    def tearDown(self):
        super(APIExtraDataAccessHookTests, self).tearDown()

        if self.registered is True:
            self.manager.disable_extension(self.extension_class.id)

    def test_register(self):
        """Testing APIExtraDataAccessHook registration"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_register_overridden_hook(self):
        """Testing overridden APIExtraDataAccessHook registration"""
        self.EverythingPrivateHook(self.extension, self.resource, [])

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_overridden_hook_get(self):
        """Testing overridden APIExtraDataAccessHook get"""
        hook = self.EverythingPrivateHook(self.extension, self.resource, [])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        # Since the hook registers the callback function on initialization,
        # which stores a pointer to the method, we can't use SpyAgency after
        # the hook has already been initialized. Since SpyAgency's spy_on
        # function requires an instance of a class, we also cannot spy on the
        # hook function before initialization. Therefore, as a workaround,
        # we're setting a variable in the function to ensure that it is in
        # fact being called.
        self.assertTrue(hook.called)
        self.assertNotIn('public', rsp['test']['extra_data'])
        self.assertNotIn('readonly', rsp['test']['extra_data'])
        self.assertNotIn('private', rsp['test']['extra_data'])

    def test_overridden_hook_put(self):
        """Testing overridden APIExtraDataAccessHook put"""
        hook = self.EverythingPrivateHook(self.extension, self.resource, [])

        original_value = self.resource.extra_data['readonly']
        modified_extra_fields = {
            'extra_data.public': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        # Since the hook registers the callback function on initialization,
        # which stores a pointer to the method, we can't use SpyAgency after
        # the hook has already been initialized. Since SpyAgency's spy_on
        # function requires an instance of a class, we also cannot spy on the
        # hook function before initialization. Therefore, as a workaround,
        # we're setting a variable in the function to ensure that it is in
        # fact being called.
        self.assertTrue(hook.called)
        self.assertEqual(original_value, rsp['test']['readonly'])

    def test_register_invalid_hook(self):
        """Testing hook registration with invalid hook"""
        self.registered = False

        with self.assertRaises(RegistrationError):
            self.InvalidCallableHook(self.extension, self.resource, [])

        self.assertSetEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_register_hook_already_registered(self):
        """Testing hook registration with already registered callback"""
        hook = APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        with self.assertRaises(AlreadyRegisteredError):
            hook.resource.extra_data_access_callbacks.register(
                hook.get_extra_data_state)

        self.assertNotEqual(set(),
                            set(self.resource.extra_data_access_callbacks))

    def test_public_state_get(self):
        """Testing APIExtraDataAccessHook public state GET"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertIn('public', rsp['test']['extra_data'])

    def test_public_state_put(self):
        """Testing APIExtraDataAccessHook public state PUT"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        modified_extra_fields = {
            'extra_data.public': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(modified_extra_fields['extra_data.public'],
                         rsp['test']['public'])

    def test_readonly_state_get(self):
        """Testing APIExtraDataAccessHook readonly state get"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('readonly',),
                 ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertIn('readonly', rsp['test']['extra_data'])

    def test_readonly_state_put(self):
        """Testing APIExtraDataAccessHook readonly state put"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('readonly',),
                 ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY)
            ])

        original_value = self.resource.extra_data['readonly']
        modified_extra_fields = {
            'extra_data.readonly': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(original_value, rsp['test']['readonly'])

    def test_private_state_get(self):
        """Testing APIExtraDataAccessHook private state get"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('private',), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE)
            ])

        rsp = self.api_get(self.url,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertNotIn('private', rsp['test']['extra_data'])

    def test_private_state_put(self):
        """Testing APIExtraDataAccessHook private state put"""
        APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('private',), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE)
            ])

        original_value = self.resource.extra_data['private']
        modified_extra_fields = {
            'extra_data.private': 'modified',
        }

        rsp = self.api_put(self.url, modified_extra_fields,
                           expected_mimetype=self.resource.item_mimetype)

        self.assertEqual(original_value, rsp['test']['private'])

    def test_unregister(self):
        """Testing APIExtraDataAccessHook unregistration"""
        hook = APIExtraDataAccessHook(
            self.extension,
            self.resource,
            [
                (('public',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
            ])

        hook.shutdown()

        self.assertSetEqual(set(),
                            set(self.resource.extra_data_access_callbacks))
