from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.template import Context, RequestContext, Template
from django.test import RequestFactory
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.accounts.trophies import TrophyType, trophies_registry
from reviewboard.deprecation import RemovedInReviewBoard40Warning
from reviewboard.reviews.fields import (BaseReviewRequestField,
                                        BaseReviewRequestFieldSet,
                                        register_review_request_fieldset,
                                        unregister_review_request_fieldset)
from reviewboard.reviews.models import Comment
from reviewboard.testing import TestCase


class DisplayReviewRequestTrophiesTests(TestCase):
    fixtures = ['test_users']

    @classmethod
    def setUpClass(cls):
        super(DisplayReviewRequestTrophiesTests, cls).setUpClass()

        cls._request_factory = RequestFactory()

    def tearDown(self):
        super(DisplayReviewRequestTrophiesTests, self).tearDown()

        trophies_registry.reset()

    def test_new_style_trophy(self):
        """Testing {% display_review_request_trophies %} for new-style
        TrophyType
        """
        class SomeTrophy(TrophyType):
            category = 'trophy'
            image_width = 1
            image_height = 1

            display_format_str = 'Trophy get!'

            def qualifies(self, review_request):
                return True

        trophies_registry.register(SomeTrophy)

        review_request = self.create_review_request(publish=True)

        t = Template(
            '{% load reviewtags %}'
            '{% display_review_request_trophies review_request %}')

        request = self._request_factory.get('/')
        request.user = review_request.submitter

        text = t.render(RequestContext(request, {
            'review_request': review_request,
        }))

        self.assertIn('Trophy get!', text)


class ForReviewRequestFieldTests(SpyAgency, TestCase):
    """Tests for the for_review_request_field template tag."""

    @add_fixtures(['test_users'])
    def test_render_instantiated_fields(self):
        """Testing for_review_request_field does not try to render
        uninstantiated fields
        """
        # exception_id will be a unique value (the ID of the field set) that
        # causes the exception; no other exception should have this value.
        exception_id = None

        class TestField(BaseReviewRequestField):
            field_id = 'test_field'

            def __init__(self, *args, **kwargs):
                raise Exception(exception_id)

        class TestFieldSet(BaseReviewRequestFieldSet):
            fieldset_id = 'test_fieldset'

        register_review_request_fieldset(TestFieldSet)
        TestFieldSet.add_field(TestField)

        review_request = self.create_review_request()

        from reviewboard.reviews.templatetags.reviewtags import logger

        self.spy_on(logger.exception)

        fieldset = TestFieldSet(review_request)
        exception_id = id(fieldset)

        try:
            t = Template(
                '{% load reviewtags %}'
                '{% for_review_request_field review_request fieldset %}'
                'Never reached.'
                '{% end_for_review_request_field %}'
            )

            result = t.render(Context({
                'review_request': review_request,
                'fieldset': TestFieldSet(review_request),
            }))

            self.assertEqual(result, '')
        finally:
            unregister_review_request_fieldset(TestFieldSet)

        # There should only be one logging.exception call, from the failed
        # instantiation of the TestField.
        self.assertEqual(len(logger.exception.spy.calls), 1)
        self.assertEqual(len(logger.exception.spy.calls[0].args), 3)
        self.assertEqual(
            logger.exception.spy.calls[0].args[2].args,
            (exception_id,))


class DiffCommentLineNumbersTests(TestCase):
    """Tests for the diff_comment_line_numbers template tag."""

    def test_delete_single_lines(self):
        """Testing diff_comment_line_numbers with delete chunk and single
        commented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Line 30 (original)')

    def test_delete_mutiple_lines(self):
        """Testing diff_comment_line_numbers with delete chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (original)')

    def test_replace_single_line(self):
        """Testing diff_comment_line_numbers with replace chunk and single
        commented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'replace',
                    'lines': [
                        (10, 20, 'foo', [], 20, 'replaced line', [], False),
                        # ...
                        (50, 60, 'foo', [], 60, 'replaced line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result,
                         'Line 30 (original), 30 (patched)')

    def test_replace_multiple_lines(self):
        """Testing diff_comment_line_numbers with replace chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'replace',
                    'lines': [
                        (10, 20, 'foo', [], 20, 'replaced line', [], False),
                        # ...
                        (50, 60, 'foo', [], 60, 'replaced line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result,
                         'Lines 30-31 (original), 30-31 (patched)')

    def test_insert_single_line(self):
        """Testing diff_comment_line_numbers with insert chunk and single
        comented line
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=1),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30 (patched)')

    def test_insert_multiple_lines(self):
        """Testing diff_comment_line_numbers with insert chunk and multiple
        commented lines
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (patched)')

    def test_fake_equal_orig(self):
        """Testing diff_comment_line_numbers with fake equal from original
        side of interdiff
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'equal',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (patched)')

    def test_fake_equal_patched(self):
        """Testing diff_comment_line_numbers with fake equal from patched
        side of interdiff
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=2),
            'chunks': [
                {
                    'change': 'equal',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-31 (original)')

    def test_spanning_inserts_deletes(self):
        """Testing diff_comment_line_numbers with spanning delete and insert"""
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'insert',
                    'lines': [
                        (51, '', '', [], 61, 'inserted line', [], False),
                        # ...
                        (100, '', '', [], 110, 'inserted line', [], False),
                    ],
                },
                {
                    'change': 'equal',
                    'lines': [
                        (101, 61, 'equal line', [], 111, 'equal line', [],
                         False),
                        # ...
                        (200, 160, 'equal line', [], 210, 'equal line', [],
                         False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-60 (original), 61-79 (patched)')

    def test_spanning_deletes_inserts(self):
        """Testing diff_comment_line_numbers with spanning insert and delete"""
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'insert',
                    'lines': [
                        (10, '', '', [], 20, 'inserted line', [], False),
                        # ...
                        (50, '', '', [], 60, 'inserted line', [], False),
                    ],
                },
                {
                    'change': 'delete',
                    'lines': [
                        (51, 61, 'inserted line', [], '', '', [], False),
                        # ...
                        (100, 110, 'inserted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'equal',
                    'lines': [
                        (101, 111, 'equal line', [], 61, 'equal line', [],
                         False),
                        # ...
                        (200, 210, 'equal line', [], 160, 'equal line', [],
                         False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 61-79 (original), 30-60 (patched)')

    def test_spanning_last_chunk(self):
        """Testing diff_comment_line_numbers with spanning chunks through last
        chunk
        """
        t = Template(
            '{% load reviewtags %}'
            '{% diff_comment_line_numbers chunks comment %}'
        )

        result = t.render(Context({
            'comment': Comment(first_line=20, num_lines=50),
            'chunks': [
                {
                    'change': 'delete',
                    'lines': [
                        (10, 20, 'deleted line', [], '', '', [], False),
                        # ...
                        (50, 60, 'deleted line', [], '', '', [], False),
                    ],
                },
                {
                    'change': 'insert',
                    'lines': [
                        (51, '', '', [], 61, 'inserted line', [], False),
                        # ...
                        (100, '', '', [], 110, 'inserted line', [], False),
                    ],
                },
            ],
        }))

        self.assertEqual(result, 'Lines 30-60 (original), 61-79 (patched)')


class ReplySectionTests(TestCase):
    """Unit tests for the {% reply_section %} template tag."""

    fixtures = ['test_users']

    def test_with_body_top(self):
        """Testing {% reply_section %} with body_top"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        self.create_reply(review,
                          body_top_reply_to=review,
                          publish=True)

        self._test_reply_section(context_type='body_top',
                                 context_id='rcbt',
                                 review=review,
                                 expected_context_id='rcbt',
                                 expected_reply_anchor_prefix='header-reply')

    def test_with_body_bottom(self):
        """Testing {% reply_section %} with body_bottom"""
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        self.create_reply(review,
                          body_bottom_reply_to=review,
                          publish=True)

        self._test_reply_section(context_type='body_bottom',
                                 context_id='rcbb',
                                 review=review,
                                 expected_context_id='rcbb',
                                 expected_reply_anchor_prefix='footer-reply')

    @add_fixtures(['test_scmtools'])
    def test_with_diff_comment(self):
        """Testing {% reply_section %} with diff comment"""
        review_request = self.create_review_request(publish=True,
                                                    create_repository=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff)

        reply = self.create_reply(review, publish=True)
        self.create_diff_comment(reply, filediff,
                                 reply_to=comment)

        self._test_reply_section(context_type='diff_comments',
                                 context_id='rc',
                                 review=review,
                                 comment=comment,
                                 expected_context_id='rc%s' % comment.pk,
                                 expected_reply_anchor_prefix='comment')

    def test_with_general_comment(self):
        """Testing {% reply_section %} with general comment"""
        review_request = self.create_review_request(publish=True)

        review = self.create_review(review_request, publish=True)
        comment = self.create_general_comment(review)

        reply = self.create_reply(review, publish=True)
        self.create_general_comment(reply,
                                    reply_to=comment)

        self._test_reply_section(context_type='general_comments',
                                 context_id='rc',
                                 review=review,
                                 comment=comment,
                                 expected_context_id='rcg%s' % comment.pk,
                                 expected_reply_anchor_prefix='gcomment')

    def test_with_file_attachment_comment(self):
        """Testing {% reply_section %} with file attachment comment"""
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)

        review = self.create_review(review_request, publish=True)
        comment = self.create_file_attachment_comment(review, file_attachment)

        reply = self.create_reply(review, publish=True)
        self.create_file_attachment_comment(reply, file_attachment,
                                            reply_to=comment)

        self._test_reply_section(context_type='file_attachment_comments',
                                 context_id='rc',
                                 review=review,
                                 comment=comment,
                                 expected_context_id='rcf%s' % comment.pk,
                                 expected_reply_anchor_prefix='fcomment')

    def test_with_screenshot_comment(self):
        """Testing {% reply_section %} with screenshot comment"""
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        review = self.create_review(review_request, publish=True)
        comment = self.create_screenshot_comment(review, screenshot)

        reply = self.create_reply(review, publish=True)
        self.create_screenshot_comment(reply, screenshot,
                                       reply_to=comment)

        self._test_reply_section(context_type='screenshot_comments',
                                 context_id='rc',
                                 review=review,
                                 comment=comment,
                                 expected_context_id='rcs%s' % comment.pk,
                                 expected_reply_anchor_prefix='scomment')

    def _test_reply_section(self, context_type, context_id, review,
                            expected_context_id, expected_reply_anchor_prefix,
                            comment=None):
        """Render the template tag and check the output.

        Args:
            context_type (unicode):
                The context type to pass to the template tag.

            context_id (unicode):
                The context ID to pass to the template tag.

            review (reviewboard.reviews.models.review.Review):
                The review being replied to.

            expected_context_id (unicode):
                The expected rendered context ID (found in the element ID).

            expected_reply_anchor_prefix (unicode):
                The expected reply anchor (found in the
                ``data-reply-anchor-prefix=`` attribute).

            comment (reviewboard.reviews.models.base_comment.BaseComment,
                     optional):
                The comment being replied to, if replying to a comment.

        Raises:
            AssertionError:
                The rendered content didn't match the expected criteria.
        """
        request = self.create_http_request()

        t = Template(
            r'{% load reviewtags %}'
            r'{% reply_section review comment context_type context_id %}'
        )
        html = t.render(RequestContext(request, {
            'review': review,
            'comment': comment,
            'context_type': context_type,
            'context_id': context_id,
        }))

        s = [
            '<div id="%s-%s"\\s+'
            'class="comment-section"\\s+'
            'data-context-type="%s"\\s+'
            'data-reply-anchor-prefix="%s"\\s+'
            % (expected_context_id, review.pk, context_type,
               expected_reply_anchor_prefix)
        ]

        if comment:
            s.append('data-context-id="%s"' % comment.pk)

        s.append('>')

        self.assertRegexpMatches(html, ''.join(s))


class CommentRepliesTests(TestCase):
    """Unit tests for the comment_replies template tag."""

    fixtures = ['test_users']

    @add_fixtures(['test_scmtools'])
    def test_diff_comments(self):
        """Testing comment_replies for diff comments"""
        self._test_diff_comments(user_is_owner=False)

    @add_fixtures(['test_scmtools'])
    def test_diff_comments_with_draft(self):
        """Testing comment_replies for diff comments with draft"""
        self._test_diff_comments(user_is_owner=True)

    def test_general_comments(self):
        """Testing comment_replies for general comments"""
        self._test_general_comments(user_is_owner=False)

    def test_general_comments_with_draft(self):
        """Testing comment_replies for general comments with draft"""
        self._test_general_comments(user_is_owner=True)

    def test_file_attachment_comments(self):
        """Testing comment_replies for file attachment comments"""
        self._test_file_attachment_comments(user_is_owner=False)

    def test_file_attachment_comments_with_draft(self):
        """Testing comment_replies for file attachment comments with draft"""
        self._test_file_attachment_comments(user_is_owner=True)

    def test_screenshot_comments(self):
        """Testing comment_replies for screenshot comments"""
        self._test_screenshot_comments(user_is_owner=False)

    def test_screenshot_comments_with_draft(self):
        """Testing comment_replies for screenshot comments with draft"""
        self._test_screenshot_comments(user_is_owner=True)

    def _test_diff_comments(self, user_is_owner):
        review_request = self.create_review_request(publish=True,
                                                    create_repository=True)
        diffset = self.create_diffset(review_request)
        filediff = self.create_filediff(diffset)

        review = self.create_review(review_request, publish=True)
        comment = self.create_diff_comment(review, filediff)

        self._check_replies(
            review,
            comment,
            self.create_diff_comment,
            {
                'filediff': filediff,
            },
            user_is_owner)

    def _test_general_comments(self, user_is_owner):
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)
        comment = self.create_general_comment(review)

        self._check_replies(
            review,
            comment,
            self.create_general_comment,
            {},
            user_is_owner)

    def _test_file_attachment_comments(self, user_is_owner):
        review_request = self.create_review_request(publish=True)
        file_attachment = self.create_file_attachment(review_request)

        review = self.create_review(review_request, publish=True)
        comment = self.create_file_attachment_comment(review, file_attachment)

        self._check_replies(
            review,
            comment,
            self.create_file_attachment_comment,
            {
                'file_attachment': file_attachment,
            },
            user_is_owner)

    def _test_screenshot_comments(self, user_is_owner):
        review_request = self.create_review_request(publish=True)
        screenshot = self.create_screenshot(review_request)

        review = self.create_review(review_request, publish=True)
        comment = self.create_screenshot_comment(review, screenshot)

        self._check_replies(
            review,
            comment,
            self.create_screenshot_comment,
            {
                'screenshot': screenshot,
            },
            user_is_owner)

    def _check_replies(self, review, comment, create_comment_func,
                       create_comment_kwargs, user_is_owner):
        reply_kwargs = {
            'review': review,
            'user': review.user,
        }

        create_comment_kwargs['reply_to'] = comment

        reply1 = self.create_reply(publish=True, **reply_kwargs)
        reply_comment1 = create_comment_func(reply1, **create_comment_kwargs)
        reply_comment2 = create_comment_func(reply1, **create_comment_kwargs)

        reply2 = self.create_reply(publish=True, **reply_kwargs)
        reply_comment3 = create_comment_func(reply2, **create_comment_kwargs)

        reply3 = self.create_reply(publish=False, **reply_kwargs)
        reply_comment4 = create_comment_func(reply3, **create_comment_kwargs)

        t = Template(
            '{% load reviewtags %}'
            '{% comment_replies review comment "123" %}'
        )

        request = RequestFactory().request()

        if user_is_owner:
            request.user = review.user
        else:
            request.user = User.objects.create_user(username='test-user',
                                                    email='user@example.com')

        html = t.render(RequestContext(request, {
            'comment': comment,
            'review': review,
        }))

        self.assertIn('data-comment-id="%s"' % reply_comment1.pk, html)
        self.assertIn('data-comment-id="%s"' % reply_comment2.pk, html)
        self.assertIn('data-comment-id="%s"' % reply_comment3.pk, html)

        if user_is_owner:
            self.assertIn('<li class="draft" data-comment-id="%s"'
                          % reply_comment4.pk,
                          html)
        else:
            self.assertNotIn('data-comment-id="%s"' % reply_comment4.pk, html)


class ReviewBodyRepliesTests(TestCase):
    """Unit tests for the review_body_replies template tag."""

    fixtures = ['test_users']

    def test_body_top(self):
        """Testing review_body_replies for body_top"""
        self._test_body_field('body_top', user_is_owner=False)

    def test_body_top_with_draft(self):
        """Testing review_body_replies for body_top with draft"""
        self._test_body_field('body_top', user_is_owner=True)

    def test_body_bottom(self):
        """Testing review_body_replies for body_bottom"""
        self._test_body_field('body_bottom', user_is_owner=False)

    def test_body_bottom_with_draft(self):
        """Testing review_body_replies for body_bottom with draft"""
        self._test_body_field('body_bottom', user_is_owner=True)

    def _test_body_field(self, body_field, user_is_owner):
        review_request = self.create_review_request(publish=True)
        review = self.create_review(review_request, publish=True)

        reply_kwargs = {
            'review': review,
            'user': review.user,
            '%s_reply_to' % body_field: review,
            body_field: 'Some reply',
        }

        reply1 = self.create_reply(publish=True, **reply_kwargs)
        reply2 = self.create_reply(publish=True, **reply_kwargs)
        reply3 = self.create_reply(publish=False, **reply_kwargs)

        t = Template(
            '{%% load reviewtags %%}'
            '{%% review_body_replies review "%s" "123" %%}'
            % body_field
        )

        request = RequestFactory().request()

        if user_is_owner:
            request.user = review.user
        else:
            request.user = User.objects.create_user(username='test-user',
                                                    email='user@example.com')

        html = t.render(RequestContext(request, {
            'review': review,
        }))

        self.assertIn('id="comment_123-%s"' % reply1.pk, html)
        self.assertIn('id="comment_123-%s"' % reply2.pk, html)

        if user_is_owner:
            self.assertIn('id="draftcomment_123-%s"' % reply3.pk, html)
        else:
            self.assertNotIn('id="comment_123-%s"' % reply3.pk, html)
            self.assertNotIn('id="draftcomment_123-%s"' % reply3.pk, html)
