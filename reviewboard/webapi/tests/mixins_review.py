from __future__ import unicode_literals

from reviewboard.webapi.tests.mixins import test_template


class ReviewListMixin(object):
    @test_template
    def test_post_with_rich_text_true(self):
        """Testing the POST <URL> API with rich_text=true"""
        self._test_post_with_rich_text(False)

    @test_template
    def test_post_with_rich_text_false(self):
        """Testing the POST <URL> API with rich_text=false"""
        self._test_post_with_rich_text(False)

    def _test_post_with_rich_text(self, rich_text):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        review_request = objs[0]

        data['body_top'] = body_top
        data['body_bottom'] = body_bottom
        data['rich_text'] = rich_text

        rsp = self.apiPost(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.assertEqual(review_rsp['rich_text'], rich_text)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))


class ReviewItemMixin(object):
    @test_template
    def test_put_with_rich_text_true_all_fields(self):
        """Testing the PUT <URL> API
        with rich_text=true and all fields specified
        """
        self._test_put_with_rich_text_all_fields(True)

    def test_put_with_rich_text_false_all_fields(self):
        """Testing the PUT <URL> API
        with rich_text=false and all fields specified
        """
        self._test_put_with_rich_text_all_fields(False)

    @test_template
    def test_put_with_rich_text_true_escaping_all_fields(self):
        """Testing the PUT <URL> API
        with changing rich_text to true and escaping all fields
        """
        self._test_put_with_rich_text_escaping_all_fields(
            True,
            '`This` is **body_top**',
            '`This` is **body_bottom**',
            r'\`This\` is \*\*body\_top\*\*',
            r'\`This\` is \*\*body\_bottom\*\*')

    @test_template
    def test_put_with_rich_text_false_escaping_all_fields(self):
        """Testing the PUT <URL> API
        with changing rich_text to false and unescaping all fields
        """
        self._test_put_with_rich_text_escaping_all_fields(
            False,
            r'\`This\` is \*\*body\_top\*\*',
            r'\`This\` is \*\*body\_bottom\*\*',
            '`This` is **body_top**',
            '`This` is **body_bottom**')

    @test_template
    def test_put_with_rich_text_true_escaping_unspecified_fields(self):
        """Testing the PUT <URL> API
        with changing rich_text to true and escaping unspecified fields
        """
        self._test_put_with_rich_text_escaping_unspecified_fields(
            True,
            '`This` is **body_top**',
            r'\`This\` is \*\*body\_top\*\*')

    @test_template
    def test_put_with_rich_text_false_escaping_unspecified_fields(self):
        """Testing the PUT <URL> API
        with changing rich_text to false and unescaping unspecified fields
        """
        self._test_put_with_rich_text_escaping_unspecified_fields(
            False,
            r'\`This\` is \*\*body\_top\*\*',
            '`This` is **body_top**')

    @test_template
    def test_put_without_rich_text_and_escaping_provided_fields(self):
        """Testing the PUT <URL> API
        without changing rich_text and with escaping provided fields
        """
        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.rich_text = True
        review.save()

        if 'rich_text' in data:
            del data['rich_text']

        data.update({
            'body_top': '`This` is **body_top**',
            'body_bottom': '`This` is **body_bottom**',
        })

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertTrue(review_rsp['rich_text'])
        self.assertEqual(review_rsp['body_top'],
                         r'\`This\` is \*\*body\_top\*\*')
        self.assertEqual(review_rsp['body_bottom'],
                         r'\`This\` is \*\*body\_bottom\*\*')
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_put_with_rich_text_all_fields(self, rich_text):
        body_top = '`This` is **body_top**'
        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data.update({
            'rich_text': rich_text,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['rich_text'], rich_text)
        self.assertEqual(review_rsp['body_top'], body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_put_with_rich_text_escaping_all_fields(
            self, rich_text, body_top, body_bottom,
            expected_body_top, expected_body_bottom):

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.rich_text = not rich_text
        review.body_top = body_top
        review.body_bottom = body_bottom
        review.save()

        for field in ('body_top', 'body_bottom'):
            if field in data:
                del data[field]

        data['rich_text'] = rich_text

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['rich_text'], rich_text)
        self.assertEqual(review_rsp['body_top'], expected_body_top)
        self.assertEqual(review_rsp['body_bottom'], expected_body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))

    def _test_put_with_rich_text_escaping_unspecified_fields(
            self, rich_text, body_top, expected_body_top):

        body_bottom = '`This` is **body_bottom**'

        url, mimetype, data, review, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        review.rich_text = not rich_text
        review.body_top = body_top
        review.save()

        data['rich_text'] = rich_text
        data['body_bottom'] = body_bottom

        if 'body_top' in data:
            del data['body_top']

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        review_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(review_rsp['rich_text'], rich_text)
        self.assertEqual(review_rsp['body_top'], expected_body_top)
        self.assertEqual(review_rsp['body_bottom'], body_bottom)
        self.compare_item(review_rsp,
                          self.resource.model.objects.get(pk=review_rsp['id']))
