from __future__ import unicode_literals

from reviewboard.webapi.tests.mixins import test_template


class BaseCommentListMixin(object):
    @test_template
    def test_post_with_rich_text_true(self):
        """Testing the POST <URL> API with rich_text=true"""
        self._test_post_with_rich_text(True)

    @test_template
    def test_post_with_rich_text_false(self):
        """Testing the POST <URL> API with rich_text=false"""
        self._test_post_with_rich_text(False)

    def _test_post_with_rich_text(self, rich_text):
        comment_text = '`This` is a **test**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data['text'] = comment_text
        data['rich_text'] = rich_text
        reply = objs[0]

        rsp = self.apiPost(url, data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], comment_text)
        self.assertEqual(comment_rsp['rich_text'], rich_text)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)


class BaseCommentItemMixin(object):
    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)
        self.assertEqual(item_rsp['rich_text'], comment.rich_text)

    @test_template
    def test_put_with_rich_text_true_and_text(self):
        """Testing the PUT <URL> API with rich_text=true and text specified"""
        self._test_put_with_rich_text_and_text(True)

    @test_template
    def test_put_with_rich_text_false_and_text(self):
        """Testing the PUT <URL> API with rich_text=false and text specified"""
        self._test_put_with_rich_text_and_text(False)

    @test_template
    def test_put_with_rich_text_true_and_not_text(self):
        """Testing the PUT <URL> API
        with rich_text=true and text not specified escapes text
        """
        self._test_put_with_rich_text_and_not_text(
            True,
            '`Test` **diff** comment',
            r'\`Test\` \*\*diff\*\* comment')

    @test_template
    def test_put_with_rich_text_false_and_not_text(self):
        """Testing the PUT <URL> API
        with rich_text=false and text not specified
        """
        self._test_put_with_rich_text_and_not_text(
            False,
            r'\`Test\` \*\*diff\*\* comment',
            '`Test` **diff** comment')

    @test_template
    def test_put_without_rich_text_and_escaping_provided_fields(self):
        """Testing the PUT <URL> API
        without changing rich_text and with escaping provided fields
        """
        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        reply_comment.rich_text = True
        reply_comment.save()

        if 'rich_text' in data:
            del data['rich_text']

        data.update({
            'text': '`This` is **text**',
        })

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        comment_rsp = rsp[self.resource.item_result_key]
        self.assertTrue(comment_rsp['rich_text'])
        self.assertEqual(comment_rsp['text'], '\\`This\\` is \\*\\*text\\*\\*')

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def _test_put_with_rich_text_and_text(self, rich_text):
        comment_text = '`Test` **diff** comment'

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data['rich_text'] = rich_text
        data['text'] = comment_text

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], comment_text)
        self.assertEqual(comment_rsp['rich_text'], rich_text)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def _test_put_with_rich_text_and_not_text(self, rich_text, text,
                                              expected_text):
        comment_text = '`Test` **diff** comment'

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        reply_comment.text = text
        reply_comment.rich_text = not rich_text
        reply_comment.save()

        data['rich_text'] = rich_text

        if 'text' in data:
            del data['text']

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], expected_text)
        self.assertEqual(comment_rsp['rich_text'], rich_text)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)


class CommentListMixin(BaseCommentListMixin):
    pass


class CommentItemMixin(BaseCommentItemMixin):
    pass


class CommentReplyListMixin(BaseCommentListMixin):
    pass


class CommentReplyItemMixin(BaseCommentItemMixin):
    pass
