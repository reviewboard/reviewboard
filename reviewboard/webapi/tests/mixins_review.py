from __future__ import unicode_literals

from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)


class ReviewListMixin(ExtraDataListMixin):
    @webapi_test_template
    def test_post_with_text_type_markdown(self):
        """Testing the POST <URL> API with text_type=markdown"""
        self._test_post_with_text_types(
            text_type_field='text_type',
            text_type_value='markdown',
            expected_body_top_text_type='markdown',
            expected_body_bottom_text_type='markdown')

    @webapi_test_template
    def test_post_with_text_type_plain(self):
        """Testing the POST <URL> API with text_type=plain"""
        self._test_post_with_text_types(
            text_type_field='text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_post_with_body_top_text_type_markdown(self):
        """Testing the POST <URL> API with body_top_text_type=markdown"""
        self._test_post_with_text_types(
            text_type_field='body_top_text_type',
            text_type_value='markdown',
            expected_body_top_text_type='markdown',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_post_with_body_top_text_type_plain(self):
        """Testing the POST <URL> API with body_top_text_type=plain"""
        self._test_post_with_text_types(
            text_type_field='body_top_text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_post_with_body_bottom_text_type_markdown(self):
        """Testing the POST <URL> API with body_bottom_text_type=markdown"""
        self._test_post_with_text_types(
            text_type_field='body_bottom_text_type',
            text_type_value='markdown',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='markdown')

    @webapi_test_template
    def test_post_with_body_bottom_text_type_plain(self):
        """Testing the POST <URL> API with body_bottom_text_type=plain"""
        self._test_post_with_text_types(
            text_type_field='body_bottom_text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    def _test_post_with_text_types(self, text_type_field, text_type_value,
                                   expected_body_top_text_type,
                                   expected_body_bottom_text_type):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)

        rsp = self.api_post(
            url,
            {
                'body_top': body_top,
                'body_bottom': body_bottom,
                text_type_field: text_type_value,
            },
            expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.assertEqual(review_rsp['body_top_text_type'],
                         expected_body_top_text_type)
        self.assertEqual(review_rsp['body_bottom_text_type'],
                         expected_body_bottom_text_type)

        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))


class ReviewItemMixin(ExtraDataItemMixin):
    @webapi_test_template
    def test_get_with_markdown_and_force_text_type_markdown(self):
        """Testing the GET <URL> API with text_type=markdown and
        ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='markdown',
            expected_text=r'\# `This` is a **test**')

    @webapi_test_template
    def test_get_with_markdown_and_force_text_type_plain(self):
        """Testing the GET <URL> API with text_type=markdown and
        ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='plain',
            expected_text='# `This` is a **test**')

    @webapi_test_template
    def test_get_with_markdown_and_force_text_type_html(self):
        """Testing the GET <URL> API with text_type=markdown and
        ?force-text-type=html
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='html',
            expected_text='<p># <code>This</code> is a '
                          '<strong>test</strong></p>')

    @webapi_test_template
    def test_get_with_plain_and_force_text_type_markdown(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='markdown',
            expected_text=r'\#<\`This\` is a \*\*test\*\*>')

    @webapi_test_template
    def test_get_with_plain_and_force_text_type_plain(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='plain',
            expected_text='#<`This` is a **test**>')

    @webapi_test_template
    def test_get_with_plain_and_force_text_type_html(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=html
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='html',
            expected_text='#&lt;`This` is a **test**&gt;')

    @webapi_test_template
    def test_put_with_text_type_markdown(self):
        """Testing the PUT <URL> API with text_type=markdown"""
        self._test_put_with_text_types(
            text_type_field='text_type',
            text_type_value='markdown',
            expected_body_top_text_type='markdown',
            expected_body_bottom_text_type='markdown')

    @webapi_test_template
    def test_put_with_text_type_plain(self):
        """Testing the PUT <URL> API with text_type=plain"""
        self._test_put_with_text_types(
            text_type_field='text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_put_with_body_top_text_type_markdown(self):
        """Testing the PUT <URL> API with body_top_text_type=markdown"""
        self._test_put_with_text_types(
            text_type_field='body_top_text_type',
            text_type_value='markdown',
            expected_body_top_text_type='markdown',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_put_with_body_top_text_type_plain(self):
        """Testing the PUT <URL> API with body_top_text_type=plain"""
        self._test_put_with_text_types(
            text_type_field='body_top_text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    @webapi_test_template
    def test_put_with_body_bottom_text_type_markdown(self):
        """Testing the PUT <URL> API with body_bottom_text_type=markdown"""
        self._test_put_with_text_types(
            text_type_field='body_bottom_text_type',
            text_type_value='markdown',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='markdown')

    @webapi_test_template
    def test_put_with_body_bottom_text_type_plain(self):
        """Testing the PUT <URL> API with body_bottom_text_type=plain"""
        self._test_put_with_text_types(
            text_type_field='body_bottom_text_type',
            text_type_value='plain',
            expected_body_top_text_type='plain',
            expected_body_bottom_text_type='plain')

    def _test_get_with_force_text_type(self, text, rich_text,
                                       force_text_type, expected_text):
        url, mimetype, review = \
            self.setup_basic_get_test(self.user, False, None)

        review.body_top = text
        review.body_bottom = text
        review.body_top_rich_text = rich_text
        review.body_bottom_rich_text = rich_text
        review.save()

        rsp = self.api_get(url + '?force-text-type=%s' % force_text_type,
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['body_top_text_type'], force_text_type)
        self.assertEqual(review_rsp['body_bottom_text_type'], force_text_type)
        self.assertEqual(review_rsp['body_top'], expected_text)
        self.assertEqual(review_rsp['body_bottom'], expected_text)
        self.assertNotIn('raw_text_fields', review_rsp)

        rsp = self.api_get('%s?force-text-type=%s&include-text-types=raw'
                           % (url, force_text_type),
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        review_rsp = rsp[self.resource.item_result_key]
        self.assertIn('raw_text_fields', review_rsp)
        raw_text_fields = review_rsp['raw_text_fields']
        self.assertEqual(raw_text_fields['body_top'], text)
        self.assertEqual(raw_text_fields['body_bottom'], text)

    def _test_put_with_text_types(self, text_type_field, text_type_value,
                                  expected_body_top_text_type,
                                  expected_body_bottom_text_type):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data.update({
            'body_top': body_top,
            'body_bottom': body_bottom,
            text_type_field: text_type_value,
        })

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.assertEqual(review_rsp['body_top_text_type'],
                         expected_body_top_text_type)
        self.assertEqual(review_rsp['body_bottom_text_type'],
                         expected_body_bottom_text_type)

        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))
