from __future__ import unicode_literals

from reviewboard.webapi.tests.mixins import test_template
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)


class BaseCommentListMixin(object):
    @test_template
    def test_post_with_text_type_markdown(self):
        """Testing the POST <URL> API with text_type=markdown"""
        self._test_post_with_text_type('markdown')

    @test_template
    def test_post_with_text_type_plain(self):
        """Testing the POST <URL> API with text_type=plain"""
        self._test_post_with_text_type('plain')

    def _test_post_with_text_type(self, text_type):
        comment_text = '`This` is a **test**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data['text'] = comment_text
        data['text_type'] = text_type
        reply = objs[0]

        rsp = self.apiPost(url, data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], comment_text)
        self.assertEqual(comment_rsp['text_type'], text_type)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)


class BaseCommentItemMixin(object):
    def compare_item(self, item_rsp, comment):
        self.assertEqual(item_rsp['id'], comment.pk)
        self.assertEqual(item_rsp['text'], comment.text)

        if comment.rich_text:
            self.assertEqual(item_rsp['rich_text'], 'markdown')
        else:
            self.assertEqual(item_rsp['rich_text'], 'plain')

    @test_template
    def test_put_with_text_type_markdown_and_text(self):
        """Testing the PUT <URL> API with text_type=markdown and text specified"""
        self._test_put_with_text_type_and_text('markdown')

    @test_template
    def test_put_with_text_type_plain_and_text(self):
        """Testing the PUT <URL> API with text_type=plain and text specified"""
        self._test_put_with_text_type_and_text('plain')

    @test_template
    def test_put_with_text_type_markdown_and_not_text(self):
        """Testing the PUT <URL> API
        with text_type=markdown and text not specified escapes text
        """
        self._test_put_with_text_type_and_not_text(
            'markdown',
            '`Test` **diff** comment',
            r'\`Test\` \*\*diff\*\* comment')

    @test_template
    def test_put_with_text_type_plain_and_not_text(self):
        """Testing the PUT <URL> API
        with text_type=plain and text not specified
        """
        self._test_put_with_text_type_and_not_text(
            'plain',
            r'\`Test\` \*\*diff\*\* comment',
            '`Test` **diff** comment')

    @test_template
    def test_put_without_text_type_and_escaping_provided_fields(self):
        """Testing the PUT <URL> API
        without changing text_type and with escaping provided fields
        """
        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        reply_comment.rich_text = True
        reply_comment.save()

        if 'text_type' in data:
            del data['text_type']

        data.update({
            'text': '`This` is **text**',
        })

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text_type'], 'markdown')
        self.assertEqual(comment_rsp['text'], '\\`This\\` is \\*\\*text\\*\\*')

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def _test_put_with_text_type_and_text(self, text_type):
        comment_text = '`Test` **diff** comment'

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data['text_type'] = text_type
        data['text'] = comment_text

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], comment_text)
        self.assertEqual(comment_rsp['text_type'], text_type)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def _test_put_with_text_type_and_not_text(self, text_type, text,
                                              expected_text):
        self.assertIn(text_type, ('markdown', 'plain'))

        rich_text = (text_type == 'markdown')

        comment_text = '`Test` **diff** comment'

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        reply_comment.text = text
        reply_comment.rich_text = not rich_text
        reply_comment.save()

        data['text_type'] = text_type

        if 'text' in data:
            del data['text']

        rsp = self.apiPut(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertTrue(self.resource.item_result_key in rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], expected_text)
        self.assertEqual(comment_rsp['text_type'], text_type)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)


class CommentListMixin(ExtraDataListMixin, BaseCommentListMixin):
    pass


class CommentItemMixin(ExtraDataItemMixin, BaseCommentItemMixin):
    pass


class CommentReplyListMixin(BaseCommentListMixin):
    pass


class CommentReplyItemMixin(BaseCommentItemMixin):
    pass
