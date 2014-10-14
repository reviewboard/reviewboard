from __future__ import unicode_literals

from reviewboard.webapi.tests.mixins import test_template
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)


class ReviewListMixin(ExtraDataListMixin):
    @test_template
    def test_post_with_text_type_markdown(self):
        """Testing the POST <URL> API with text_type=markdown"""
        self._test_post_with_text_type('markdown')

    @test_template
    def test_post_with_text_type_plain(self):
        """Testing the POST <URL> API with text_type=plain"""
        self._test_post_with_text_type('plain')

    def _test_post_with_text_type(self, text_type):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)

        data['body_top'] = body_top
        data['body_bottom'] = body_bottom
        data['text_type'] = text_type

        rsp = self.api_post(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.assertEqual(review_rsp['text_type'], text_type)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))


class ReviewItemMixin(ExtraDataItemMixin):
    @test_template
    def test_get_with_markdown_and_force_text_type_markdown(self):
        """Testing the GET <URL> API with text_type=markdown and
        ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='markdown',
            expected_text=r'\# `This` is a **test**')

    @test_template
    def test_get_with_markdown_and_force_text_type_plain(self):
        """Testing the GET <URL> API with text_type=markdown and
        ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text=r'\# `This` is a **test**',
            rich_text=True,
            force_text_type='plain',
            expected_text='# `This` is a **test**')

    @test_template
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

    @test_template
    def test_get_with_plain_and_force_text_type_markdown(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=markdown
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='markdown',
            expected_text=r'\#<\`This\` is a \*\*test\*\*\>')

    @test_template
    def test_get_with_plain_and_force_text_type_plain(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=plain
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='plain',
            expected_text='#<`This` is a **test**>')

    @test_template
    def test_get_with_plain_and_force_text_type_html(self):
        """Testing the GET <URL> API with text_type=plain and
        ?force-text-type=html
        """
        self._test_get_with_force_text_type(
            text='#<`This` is a **test**>',
            rich_text=False,
            force_text_type='html',
            expected_text='#&lt;`This` is a **test**&gt;')

    @test_template
    def test_put_with_text_type_markdown_all_fields(self):
        """Testing the PUT <URL> API
        with text_type=markdown and all fields specified
        """
        self._test_put_with_text_type_all_fields('markdown')

    def test_put_with_text_type_plain_all_fields(self):
        """Testing the PUT <URL> API
        with text_type=plain and all fields specified
        """
        self._test_put_with_text_type_all_fields('plain')

    @test_template
    def test_put_with_text_type_markdown_escaping_all_fields(self):
        """Testing the PUT <URL> API
        with changing text_type to markdown and escaping all fields
        """
        self._test_put_with_text_type_escaping_all_fields(
            'markdown',
            '`This` is **body_top**',
            '`This` is **body_bottom**',
            r'\`This\` is \*\*body_top\*\*',
            r'\`This\` is \*\*body_bottom\*\*')

    @test_template
    def test_put_with_text_type_plain_escaping_all_fields(self):
        """Testing the PUT <URL> API
        with changing text_type to plain and unescaping all fields
        """
        self._test_put_with_text_type_escaping_all_fields(
            'plain',
            r'\`This\` is \*\*body_top\*\*',
            r'\`This\` is \*\*body_bottom\*\*',
            '`This` is **body_top**',
            '`This` is **body_bottom**')

    @test_template
    def test_put_with_text_type_markdown_escaping_unspecified_fields(self):
        """Testing the PUT <URL> API
        with changing text_type to markdown and escaping unspecified fields
        """
        self._test_put_with_text_type_escaping_unspecified_fields(
            'markdown',
            '`This` is **body_top**',
            r'\`This\` is \*\*body_top\*\*')

    @test_template
    def test_put_with_text_type_plain_escaping_unspecified_fields(self):
        """Testing the PUT <URL> API
        with changing text_type to plain and unescaping unspecified fields
        """
        self._test_put_with_text_type_escaping_unspecified_fields(
            'plain',
            r'\`This\` is \*\*body_top\*\*',
            '`This` is **body_top**')

    @test_template
    def test_put_without_text_type_and_escaping_provided_fields(self):
        """Testing the PUT <URL> API
        without changing text_type and with escaping provided fields
        """
        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.rich_text = True
        review.save()

        if 'text_type' in data:
            del data['text_type']

        data.update({
            'body_top': '`This` is **body_top**',
            'body_bottom': '`This` is **body_bottom**',
        })

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['text_type'], 'markdown')
        self.assertEqual(review_rsp['body_top'],
                         r'\`This\` is \*\*body_top\*\*')
        self.assertEqual(review_rsp['body_bottom'],
                         r'\`This\` is \*\*body_bottom\*\*')
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_get_with_force_text_type(self, text, rich_text,
                                       force_text_type, expected_text):
        url, mimetype, review = \
            self.setup_basic_get_test(self.user, False, None)

        review.body_top = text
        review.body_bottom = text
        review.rich_text = rich_text
        review.save()

        rsp = self.api_get(url + '?force-text-type=%s' % force_text_type,
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['text_type'], force_text_type)
        self.assertEqual(review_rsp['body_top'], expected_text)
        self.assertEqual(review_rsp['body_bottom'], expected_text)
        self.assertNotIn('raw_text_fields', review_rsp)

        rsp = self.api_get('%s?force-text-type=%s&include-raw-text-fields=1'
                           % (url, force_text_type),
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')

        review_rsp = rsp[self.resource.item_result_key]
        self.assertIn('raw_text_fields', review_rsp)
        raw_text_fields = review_rsp['raw_text_fields']
        self.assertEqual(raw_text_fields['body_top'], text)
        self.assertEqual(raw_text_fields['body_bottom'], text)

    def _test_put_with_text_type_all_fields(self, text_type):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data.update({
            'text_type': text_type,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['text_type'], text_type)
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_put_with_text_type_escaping_all_fields(
            self, text_type, body_top, body_bottom,
            expected_body_top, expected_body_bottom):
        self.assertIn(text_type, ('markdown', 'plain'))

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.body_top = body_top
        review.body_bottom = body_bottom

        if text_type == 'markdown':
            review.rich_text = False
        elif text_type == 'plain':
            review.rich_text = True

        review.save()

        for field in ('body_top', 'body_bottom'):
            if field in data:
                del data[field]

        data['text_type'] = text_type

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['text_type'], text_type)
        self.assertEqual(review_rsp['body_top'], expected_body_top)
        self.assertEqual(review_rsp['body_bottom'], expected_body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_put_with_text_type_escaping_unspecified_fields(
            self, text_type, body_top, expected_body_top):
        self.assertIn(text_type, ('markdown', 'plain'))

        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.body_top = body_top

        if text_type == 'markdown':
            review.rich_text = False
        elif text_type == 'plain':
            review.rich_text = True

        review.save()

        data['text_type'] = text_type
        data['body_bottom'] = body_bottom

        if 'body_top' in data:
            del data['body_top']

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['text_type'], text_type)
        self.assertEqual(review_rsp['body_top'], expected_body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))
