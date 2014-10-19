from __future__ import unicode_literals

from reviewboard.webapi.tests.mixins import test_template


class ExtraDataListMixin(object):
    @test_template
    def test_post_with_extra_fields(self):
        """Testing the POST <URL> API with extra fields"""
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


class ExtraDataItemMixin(object):
    @test_template
    def test_put_with_extra_fields(self):
        """Testing the PUT <URL> API with extra fields"""
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
