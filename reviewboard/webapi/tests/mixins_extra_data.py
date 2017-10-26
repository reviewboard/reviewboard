"""Mixins for adding extra_data unit tests for API resources."""

from __future__ import unicode_literals

import json

from djblets.features.testing import override_feature_checks
from djblets.webapi.errors import INVALID_FORM_DATA
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.base import ExtraDataAccessLevel


class ExtraDataListMixin(object):
    """Mixin for adding extra_data tests for list resources."""

    @webapi_test_template
    def test_post_with_extra_data_simple(self):
        """Testing the POST <URL> API with extra_data.key=value"""
        self.load_fixtures(self.basic_post_fixtures)

        if self.basic_post_use_admin:
            self._login_user(admin=True)

        extra_fields = {
            'extra_data.foo': 123,
            'extra_data.bar': 456,
            'extra_data.baz': '',
            'ignored': 'foo',
        }

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data.update(extra_fields)

        with override_feature_checks(self.override_features):
            rsp = self.api_post(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('foo', obj.extra_data)
        self.assertIn('bar', obj.extra_data)
        self.assertNotIn('baz', obj.extra_data)
        self.assertNotIn('ignored', obj.extra_data)
        self.assertEqual(obj.extra_data['foo'], extra_fields['extra_data.foo'])
        self.assertEqual(obj.extra_data['bar'], extra_fields['extra_data.bar'])

    @webapi_test_template
    def test_post_with_extra_data_json(self):
        """Testing the POST <URL> API with extra_data:json"""
        self.load_fixtures(self.basic_post_fixtures)

        if self.basic_post_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data['extra_data:json'] = json.dumps({
            'foo': {
                'bar': {
                    'num': 123,
                    'string': 'hi!',
                    'bool': True,
                },
            },
            'test': [1, 2, 3],
            'not_saved': None,
        })

        with override_feature_checks(self.override_features):
            rsp = self.api_post(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('foo', obj.extra_data)
        self.assertIn('test', obj.extra_data)
        self.assertNotIn('not_saved', obj.extra_data)
        self.assertEqual(obj.extra_data['foo'], {
            'bar': {
                'num': 123,
                'string': 'hi!',
                'bool': True,
            },
        })
        self.assertEqual(obj.extra_data['test'], [1, 2, 3])

    @webapi_test_template
    def test_post_with_extra_data_json_patch(self):
        """Testing the POST <URL> API with extra_data:json-patch"""
        self.load_fixtures(self.basic_post_fixtures)

        if self.basic_post_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data['extra_data:json-patch'] = json.dumps([
            {
                'op': 'add',
                'path': '/a',
                'value': {
                    'array': [1, 2, 3],
                },
            },
            {
                'op': 'add',
                'path': '/a/b',
                'value': 'test',
            },
            {
                'op': 'add',
                'path': '/c',
                'value': None,
            },
        ])

        with override_feature_checks(self.override_features):
            rsp = self.api_post(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('a', obj.extra_data)
        self.assertIn('c', obj.extra_data)
        self.assertEqual(obj.extra_data['a'], {
            'array': [1, 2, 3],
            'b': 'test',
        })
        self.assertIsNone(obj.extra_data['c'])

    @webapi_test_template
    def test_post_with_private_extra_data_simple(self):
        """Testing the POST <URL> API with private extra_data.__key=value"""
        self.load_fixtures(self.basic_post_fixtures)

        if self.basic_post_use_admin:
            self._login_user(admin=True)

        extra_fields = {
            'extra_data.__private_key': 'private_data',
        }

        url, mimetype, data, objs = self.setup_basic_post_test(
            self.user, False, None, True)
        data.update(extra_fields)

        with override_feature_checks(self.override_features):
            rsp = self.api_post(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])

        self.assertNotIn('__private_key', obj.extra_data)


class ExtraDataItemMixin(object):
    """Mixin for adding extra_data tests for item resources."""

    @webapi_test_template
    def test_put_with_extra_data_in_simple_form(self):
        """Testing the PUT <URL> API with extra_data.key=value"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        extra_fields = {
            'extra_data.foo': 123,
            'extra_data.bar': 456,
            'extra_data.baz': '',
            'ignored': 'foo',
        }

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        data.update(extra_fields)

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('foo', obj.extra_data)
        self.assertIn('bar', obj.extra_data)
        self.assertNotIn('baz', obj.extra_data)
        self.assertNotIn('ignored', obj.extra_data)
        self.assertEqual(obj.extra_data['foo'], extra_fields['extra_data.foo'])
        self.assertEqual(obj.extra_data['bar'], extra_fields['extra_data.bar'])

    @webapi_test_template
    def test_put_with_private_extra_data_in_simple_form(self):
        """Testing the PUT <URL> API with private extra_data.__key=value"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        extra_fields = {
            'extra_data.__private_key': 'private_data',
        }

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        data.update(extra_fields)

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])

        self.assertNotIn('__private_key', obj.extra_data)

    @webapi_test_template
    def test_put_with_extra_data_json(self):
        """Testing the PUT <URL> API with extra_data:json"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data['removed'] = 'test'

        data = {
            'extra_data:json': json.dumps({
                'foo': {
                    'bar': {
                        'num': 123,
                        'string': 'hi!',
                        'bool': True,
                    },
                },
                'test': [1, 2, 3],
                'removed': None,
            }),
        }

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('foo', obj.extra_data)
        self.assertIn('test', obj.extra_data)
        self.assertNotIn('removed', obj.extra_data)
        self.assertEqual(obj.extra_data['foo'], {
            'bar': {
                'num': 123,
                'string': 'hi!',
                'bool': True,
            },
        })
        self.assertEqual(obj.extra_data['test'], [1, 2, 3])

    @webapi_test_template
    def test_put_with_extra_data_json_with_private_keys(self):
        """Testing the PUT <URL> API with extra_data:json with private keys"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data['extra_data:json'] = json.dumps({
            'foo': {
                '__bar': {
                    'num': 123,
                    'string': 'hi!',
                    'bool': True,
                },
                'baz': 456,
            },
        })

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertIn('foo', obj.extra_data)
        self.assertEqual(obj.extra_data['foo'], {
            'baz': 456,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_with_access_levels(self):
        """Testing the PUT <URL> API with extra_data:json with access levels"""
        def _access_cb(path):
            if path == ('parent', 'private'):
                return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE
            elif path == ('public-readonly',):
                return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY
            else:
                return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC

        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'public-readonly': 'orig',
        }
        obj.save()

        try:
            self.resource.extra_data_access_callbacks.register(_access_cb)

            data = {
                'extra_data:json': json.dumps({
                    'parent': {
                        'private': 1,
                    },
                    'public-readonly': 2,
                    'test': 3,
                })
            }

            with override_feature_checks(self.override_features):
                rsp = self.api_put(url, data, expected_mimetype=mimetype)
        finally:
            self.resource.extra_data_access_callbacks.unregister(_access_cb)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertEqual(obj.extra_data, {
            'parent': {},
            'public-readonly': 'orig',
            'test': 3,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_with_override_root(self):
        """Testing the PUT <URL> API with extra_data:json with attempting to
        override root of extra_data
        """
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
            'b': 2,
        }
        obj.save()

        data['extra_data:json'] = json.dumps([1, 2, 3])

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err'], {
            'code': INVALID_FORM_DATA.code,
            'msg': 'One or more fields had errors',
        })
        self.assertEqual(rsp['fields'], {
            'extra_data': [
                'extra_data:json cannot replace extra_data with a '
                'non-dictionary type',
            ],
        })

        obj = self.resource.model.objects.get(pk=obj.pk)
        self.assertEqual(obj.extra_data, {
            'a': 1,
            'b': 2,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_patch(self):
        """Testing the PUT <URL> API with extra_data:json-patch"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
            'b': {
                'c': 2,
            },
        }
        obj.save()

        data = {
            'extra_data:json-patch': json.dumps([
                {
                    'op': 'add',
                    'path': '/b/d',
                    'value': 3,
                },
                {
                    'op': 'remove',
                    'path': '/a',
                },
                {
                    'op': 'copy',
                    'from': '/b/c',
                    'path': '/e',
                },
            ]),
        }

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

        item_rsp = rsp[self.resource.item_result_key]

        obj = self.resource.model.objects.get(pk=item_rsp['id'])
        self.assertEqual(obj.extra_data, {
            'b': {
                'c': 2,
                'd': 3,
            },
            'e': 2,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_patch_with_private_keys(self):
        """Testing the PUT <URL> API with extra_data:json-patch with private
        keys
        """
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
            'b': {
                '__c': 2,
            },
        }
        obj.save()

        data['extra_data:json-patch'] = json.dumps([
            {
                'op': 'remove',
                'path': '/b/__c',
            },
        ])

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err'], {
            'code': INVALID_FORM_DATA.code,
            'msg': 'One or more fields had errors',
        })
        self.assertEqual(rsp['fields'], {
            'extra_data': [
                'Failed to patch JSON data: Cannot write to path "/b/__c" '
                'for patch entry 0',
            ],
        })

        obj = self.resource.model.objects.get(pk=obj.pk)
        self.assertEqual(obj.extra_data, {
            'a': 1,
            'b': {
                '__c': 2,
            },
        })

    @webapi_test_template
    def test_put_with_extra_data_json_patch_with_private_access_level(self):
        """Testing the PUT <URL> API with extra_data:json-patch with private
        access level
        """
        def _access_cb(path):
            if path == ('a',):
                return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE

            return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC

        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
        }
        obj.save()

        try:
            self.resource.extra_data_access_callbacks.register(_access_cb)

            data['extra_data:json-patch'] = json.dumps([
                {
                    'op': 'add',
                    'path': '/b',
                    'value': 1,
                },
                {
                    'op': 'remove',
                    'path': '/a',
                },
            ])

            with override_feature_checks(self.override_features):
                rsp = self.api_put(url, data, expected_status=400)
        finally:
            self.resource.extra_data_access_callbacks.unregister(_access_cb)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err'], {
            'code': INVALID_FORM_DATA.code,
            'msg': 'One or more fields had errors',
        })
        self.assertEqual(rsp['fields'], {
            'extra_data': [
                'Failed to patch JSON data: Cannot write to path "/a" '
                'for patch entry 1',
            ],
        })

        obj = self.resource.model.objects.get(pk=obj.pk)
        self.assertEqual(obj.extra_data, {
            'a': 1,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_patch_with_read_only_access_level(self):
        """Testing the PUT <URL> API with extra_data:json-patch with read-only
        access level
        """
        def _access_cb(path):
            if path == ('a',):
                return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY

            return ExtraDataAccessLevel.ACCESS_STATE_PUBLIC

        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
        }
        obj.save()

        try:
            self.resource.extra_data_access_callbacks.register(_access_cb)

            data['extra_data:json-patch'] = json.dumps([
                {
                    'op': 'test',
                    'path': '/a',
                    'value': 1,
                },
                {
                    'op': 'copy',
                    'from': '/a',
                    'path': '/b',
                },
                {
                    'op': 'remove',
                    'path': '/a',
                },
            ])

            with override_feature_checks(self.override_features):
                rsp = self.api_put(url, data, expected_status=400)
        finally:
            self.resource.extra_data_access_callbacks.unregister(_access_cb)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err'], {
            'code': INVALID_FORM_DATA.code,
            'msg': 'One or more fields had errors',
        })
        self.assertEqual(rsp['fields'], {
            'extra_data': [
                'Failed to patch JSON data: Cannot write to path "/a" '
                'for patch entry 2',
            ],
        })

        obj = self.resource.model.objects.get(pk=obj.pk)
        self.assertEqual(obj.extra_data, {
            'a': 1,
        })

    @webapi_test_template
    def test_put_with_extra_data_json_patch_with_override_root(self):
        """Testing the PUT <URL> API with extra_data:json-patch with
        attempting to override root of extra_data
        """
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_put_use_admin:
            self._login_user(admin=True)

        url, mimetype, data, obj, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        obj.extra_data = {
            'a': 1,
            'b': 2,
        }
        obj.save()

        data['extra_data:json-patch'] = json.dumps([
            {
                'op': 'replace',
                'path': '',
                'value': {
                    'new': 'values',
                },
            },
        ])

        with override_feature_checks(self.override_features):
            rsp = self.api_put(url, data, expected_status=400)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err'], {
            'code': INVALID_FORM_DATA.code,
            'msg': 'One or more fields had errors',
        })
        self.assertEqual(rsp['fields'], {
            'extra_data': [
                'Failed to patch JSON data: Cannot write to path "" '
                'for patch entry 0',
            ],
        })

        obj = self.resource.model.objects.get(pk=obj.pk)
        self.assertEqual(obj.extra_data, {
            'a': 1,
            'b': 2,
        })

    @webapi_test_template
    def test_get_with_private_extra_data_in_key_form(self):
        """Testing the GET <URL> API with private extra_data in __key form"""
        self.load_fixtures(getattr(self, 'basic_put_fixtures', []))

        if self.basic_get_use_admin:
            self._login_user(admin=True)

        extra_fields = {
            '__private_key': 'private_data',
            'public_key': {
                '__another_private_key': 'foo',
                'another_public_key': 'bar',
            },
        }

        url, mimetype, item = self.setup_basic_get_test(self.user, False, None)

        obj = self.resource.model.objects.get(pk=item.id)
        obj.extra_data = extra_fields
        obj.save(update_fields=['extra_data'])

        with override_feature_checks(self.override_features):
            rsp = self.api_get(url,
                               expected_mimetype=mimetype,
                               expected_json=self.basic_get_returns_json)

        item_rsp = rsp[self.resource.item_result_key]

        self.assertNotIn('__private_key', item_rsp['extra_data'])
        self.assertNotIn('__another_private_key',
                         item_rsp['extra_data']['public_key'])
        self.assertIn('another_public_key',
                      item_rsp['extra_data']['public_key'])
