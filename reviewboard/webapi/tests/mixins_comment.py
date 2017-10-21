from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.webapi.testing.decorators import webapi_test_template

from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin,
                                                        ExtraDataListMixin)


class BaseCommentListMixin(object):
    @webapi_test_template
    def test_post_with_text_type_markdown(self):
        """Testing the POST <URL> API with text_type=markdown"""
        self._test_post_with_text_type('markdown')

    @webapi_test_template
    def test_post_with_text_type_plain(self):
        """Testing the POST <URL> API with text_type=plain"""
        self._test_post_with_text_type('plain')

    def _test_post_with_text_type(self, text_type):
        comment_text = '`This` is a **test**'

        url, mimetype, data, objs = \
            self.setup_basic_post_test(self.user, False, None, True)
        data['text'] = comment_text
        data['text_type'] = text_type

        rsp = self.api_post(url, data, expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

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
    def test_put_with_text_type_markdown_and_text(self):
        """Testing the PUT <URL> API
        with text_type=markdown and text specified
        """
        self._test_put_with_text_type_and_text('markdown')

    @webapi_test_template
    def test_put_with_text_type_plain_and_text(self):
        """Testing the PUT <URL> API with text_type=plain and text specified"""
        self._test_put_with_text_type_and_text('plain')

    @webapi_test_template
    def test_put_with_text_type_markdown_and_not_text(self):
        """Testing the PUT <URL> API
        with text_type=markdown and text not specified escapes text
        """
        self._test_put_with_text_type_and_not_text(
            'markdown',
            '`Test` **diff** comment',
            r'\`Test\` \*\*diff\*\* comment')

    @webapi_test_template
    def test_put_with_text_type_plain_and_not_text(self):
        """Testing the PUT <URL> API
        with text_type=plain and text not specified
        """
        self._test_put_with_text_type_and_not_text(
            'plain',
            r'\`Test\` \*\*diff\*\* comment',
            '`Test` **diff** comment')

    @webapi_test_template
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

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text_type'], 'markdown')
        self.assertEqual(comment_rsp['text'], '\\`This\\` is \\*\\*text\\*\\*')

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    @webapi_test_template
    def test_put_with_multiple_include_text_types(self):
        """Testing the PUT <URL> API with multiple include-text-types"""
        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data.update({
            'include_text_types': 'raw,plain,markdown,html',
            'text': 'Foo',
        })

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    @webapi_test_template
    def test_put_with_issue_verification_success(self):
        """Testing the PUT <URL> API with issue verification success"""
        url, mimetype, data, comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        comment.require_verification = True
        comment.save()

        rsp = self.api_put(
            url,
            {'issue_status': 'resolved'},
            expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')

    @webapi_test_template
    def test_put_with_issue_verification_permission_denied(self):
        """Testing the PUT <URL> API with issue verification permission denied
        """
        user = User.objects.get(username='doc')
        self.assertNotEqual(user, self.user)

        url, mimetype, data, comment, objs = \
            self.setup_basic_put_test(user, False, None, True)

        comment.require_verification = True
        comment.save()

        rsp = self.api_put(
            url,
            {'issue_status': 'resolved'},
            expected_status=self.not_owner_status_code)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], self.not_owner_error.code)

    def _test_get_with_force_text_type(self, text, rich_text,
                                       force_text_type, expected_text):
        url, mimetype, comment = \
            self.setup_basic_get_test(self.user, False, None)

        comment.text = text
        comment.rich_text = rich_text
        comment.save()

        rsp = self.api_get(url + '?force-text-type=%s' % force_text_type,
                           expected_mimetype=mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text_type'], force_text_type)
        self.assertEqual(comment_rsp['text'], expected_text)
        self.assertNotIn('raw_text_fields', comment_rsp)

        rsp = self.api_get('%s?force-text-type=%s&include-text-types=raw'
                           % (url, force_text_type),
                           expected_mimetype=mimetype)
        comment_rsp = rsp[self.resource.item_result_key]
        self.assertIn('raw_text_fields', comment_rsp)
        self.assertEqual(comment_rsp['raw_text_fields']['text'], text)

    def _test_put_with_text_type_and_text(self, text_type):
        comment_text = '`Test` **diff** comment'

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)

        data['text_type'] = text_type
        data['text'] = comment_text

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

        comment_rsp = rsp[self.resource.item_result_key]
        self.assertEqual(comment_rsp['text'], comment_text)
        self.assertEqual(comment_rsp['text_type'], text_type)

        comment = self.resource.model.objects.get(pk=comment_rsp['id'])
        self.compare_item(comment_rsp, comment)

    def _test_put_with_text_type_and_not_text(self, text_type, text,
                                              expected_text):
        self.assertIn(text_type, ('markdown', 'plain'))

        rich_text = (text_type == 'markdown')

        url, mimetype, data, reply_comment, objs = \
            self.setup_basic_put_test(self.user, False, None, True)
        reply_comment.text = text
        reply_comment.rich_text = not rich_text
        reply_comment.save()

        data['text_type'] = text_type

        if 'text' in data:
            del data['text']

        rsp = self.api_put(url, data, expected_mimetype=mimetype)

        self.assertEqual(rsp['stat'], 'ok')
        self.assertIn(self.resource.item_result_key, rsp)

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
