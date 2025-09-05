"""Unit tests for reviewboard.reviews.ui.base.ReviewUI."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.utils.safestring import SafeText
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.reviews.models import FileAttachmentComment
from reviewboard.reviews.ui.base import ReviewUI
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from reviewboard.reviews.models.base_comment import BaseComment


class DummyReviewableObject(object):
    pass


class MyReviewUI(ReviewUI):
    """A basic file attachment Review UI used for testing."""

    supported_mimetypes = ['application/rbtest']
    supports_diffing = True
    supports_file_attachments = True
    js_model_class: str = 'RB.Test.ReviewUI'
    js_view_class: str = 'RB.Test.ReviewUIView'
    js_bundle_names = [
        'admin',
    ]
    css_bundle_names = [
        'js-tests',
    ]

    def get_caption(self, draft=None) -> str:
        return 'Test Caption'

    def get_comments(self) -> list[BaseComment]:
        return list(FileAttachmentComment.objects.order_by('pk'))

    def get_page_cover_image_url(self) -> str:
        return '/cover-image.png'

    def get_extra_context(self, request) -> dict[str, Any]:
        return {
            'custom_key': '123',
        }


class ReviewUITests(SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.ui.base.ReviewUI."""

    fixtures = ['test_users']

    def setUp(self) -> None:
        super().setUp()

        self.review_request = self.create_review_request()
        self.attachment = self.create_file_attachment(self.review_request)
        self.review = self.create_review(self.review_request, public=False)
        self.create_file_attachment_comment(self.review,
                                            self.attachment,
                                            text='Comment 1')
        self.create_file_attachment_comment(self.review,
                                            self.attachment,
                                            text='Comment 2',
                                            issue_opened=True)

    def test_build_render_context(self) -> None:
        """Testing ReviewUI.build_render_context"""
        reviewable_obj1 = DummyReviewableObject()
        reviewable_obj2 = DummyReviewableObject()

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=reviewable_obj2)
        review_ui.set_diff_against(reviewable_obj1)

        request = self.create_http_request(user=self.review.user)
        context = review_ui.build_render_context(request=request)

        self.assertEqual(context['base_template'], 'reviews/ui/base.html')
        self.assertEqual(context['caption'], 'Test Caption')
        self.assertEqual(context['social_page_image_url'], '/cover-image.png')
        self.assertEqual(context['social_page_title'],
                         'Reviewable for Review Request #1: Test Caption')
        self.assertEqual(context['review_request'], self.review_request)
        self.assertEqual(context['review_request_details'],
                         self.review_request)
        self.assertEqual(context['review'], self.review)
        self.assertFalse(context['review_ui_inline'])
        self.assertFalse(context['skip_static_media'])
        self.assertFalse(context['draft'])
        self.assertIs(context['review_ui'], review_ui)
        self.assertIs(context['obj'], reviewable_obj2)
        self.assertIs(context['diff_against_obj'], reviewable_obj1)
        self.assertIn('close_description', context)
        self.assertIn('close_description_rich_text', context)
        self.assertIn('last_activity_time', context)
        self.assertIn('review_ui_uuid', context)
        self.assertEqual(context['custom_key'], '123')

        self.assertEqual(len(context['comments']), 2)
        self.assertEqual(context['comments'][0].text, 'Comment 1')
        self.assertEqual(context['comments'][1].text, 'Comment 2')

    def test_build_render_context_with_inline_true(self) -> None:
        """Testing ReviewUI.build_render_context with inline=1"""
        reviewable_obj1 = DummyReviewableObject()
        reviewable_obj2 = DummyReviewableObject()

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=reviewable_obj2)
        review_ui.set_diff_against(reviewable_obj1)

        request = self.create_http_request()
        context = review_ui.build_render_context(request=request,
                                                 inline=True)

        self.assertEqual(context['base_template'],
                         'reviews/ui/base_inline.html')
        self.assertEqual(context['caption'], 'Test Caption')
        self.assertEqual(context['social_page_image_url'], '/cover-image.png')
        self.assertEqual(context['social_page_title'],
                         'Reviewable for Review Request #1: Test Caption')
        self.assertEqual(context['review_request'], self.review_request)
        self.assertEqual(context['review_request_details'],
                         self.review_request)
        self.assertTrue(context['review_ui_inline'])
        self.assertFalse(context['skip_static_media'])
        self.assertFalse(context['draft'])
        self.assertIs(context['review_ui'], review_ui)
        self.assertIs(context['obj'], reviewable_obj2)
        self.assertIs(context['diff_against_obj'], reviewable_obj1)
        self.assertIn('close_description', context)
        self.assertIn('close_description_rich_text', context)
        self.assertIn('last_activity_time', context)
        self.assertIn('social_page_image_url', context)
        self.assertIn('review_ui_uuid', context)
        self.assertNotIn('review', context)
        self.assertEqual(context['custom_key'], '123')

        self.assertEqual(len(context['comments']), 2)
        self.assertEqual(context['comments'][0].text, 'Comment 1')
        self.assertEqual(context['comments'][1].text, 'Comment 2')

    def test_build_render_context_with_skip_static_media_true(self) -> None:
        """Testing ReviewUI.build_render_context with skip_static_media=1"""
        reviewable_obj1 = DummyReviewableObject()
        reviewable_obj2 = DummyReviewableObject()

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=reviewable_obj2)
        review_ui.set_diff_against(reviewable_obj1)

        request = self.create_http_request(data={
            'skip-static-media': '1',
        })
        context = review_ui.build_render_context(request=request,
                                                 inline=True)

        self.assertEqual(context['base_template'],
                         'reviews/ui/base_inline.html')
        self.assertEqual(context['caption'], 'Test Caption')
        self.assertEqual(context['social_page_image_url'], '/cover-image.png')
        self.assertEqual(context['social_page_title'],
                         'Reviewable for Review Request #1: Test Caption')
        self.assertEqual(context['review_request'], self.review_request)
        self.assertEqual(context['review_request_details'],
                         self.review_request)
        self.assertTrue(context['review_ui_inline'])
        self.assertTrue(context['skip_static_media'])
        self.assertFalse(context['draft'])
        self.assertIs(context['review_ui'], review_ui)
        self.assertIs(context['obj'], reviewable_obj2)
        self.assertIs(context['diff_against_obj'], reviewable_obj1)
        self.assertIn('close_description', context)
        self.assertIn('close_description_rich_text', context)
        self.assertIn('last_activity_time', context)
        self.assertIn('social_page_image_url', context)
        self.assertIn('review_ui_uuid', context)
        self.assertNotIn('review', context)
        self.assertEqual(context['custom_key'], '123')

        self.assertEqual(len(context['comments']), 2)
        self.assertEqual(context['comments'][0].text, 'Comment 1')
        self.assertEqual(context['comments'][1].text, 'Comment 2')

    def test_get_comments_json(self) -> None:
        """Testing ReviewUI.get_comments_json"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=self.review.user)

        comments_json = review_ui.get_comments_json()

        self.assertJSONEqual(
            comments_json,
            {
                '0': [
                    {
                        'comment_id': 1,
                        'html': 'Comment 1',
                        'issue_opened': False,
                        'issue_status': '',
                        'localdraft': True,
                        'reply_to_id': None,
                        'review_id': 1,
                        'review_request_id': 1,
                        'rich_text': False,
                        'text': 'Comment 1',
                        'url': '/r/1/#fcomment1',
                        'user': {
                            'name': 'Dopey Dwarf',
                            'username': 'dopey',
                        },
                    },
                ],
                '1': [
                    {
                        'comment_id': 2,
                        'html': 'Comment 2',
                        'issue_opened': True,
                        'issue_status': 'open',
                        'localdraft': True,
                        'reply_to_id': None,
                        'review_id': 1,
                        'review_request_id': 1,
                        'rich_text': False,
                        'text': 'Comment 2',
                        'url': '/r/1/#fcomment2',
                        'user': {
                            'name': 'Dopey Dwarf',
                            'username': 'dopey',
                        },
                    },
                ],
            })

    def test_render_to_response_with_inline_false(self) -> None:
        """Testing ReviewUI.render_to_response with inline=0"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'inline': '0',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'model: new RB.Test.ReviewUI(',
                      response.content)
        self.assertIn(b'view = new RB.Test.ReviewUIView(',
                      response.content)
        self.assertIn(b'renderedInline: false', response.content)

    def test_render_to_response_with_inline_true(self) -> None:
        """Testing ReviewUI.render_to_response with inline=1"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'inline': '1',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'model: new RB.Test.ReviewUI(',
                      response.content)
        self.assertIn(b'view = new RB.Test.ReviewUIView(',
                      response.content)
        self.assertIn(b'renderedInline: true', response.content)

    def test_render_to_string_with_inline_false(self) -> None:
        """Testing ReviewUI.render_to_string with inline=False"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request()

        content = review_ui.render_to_string(request, inline=False)
        self.assertIsInstance(content, SafeText)
        self.assertIn('model: new RB.Test.ReviewUI(', content)
        self.assertIn('view = new RB.Test.ReviewUIView(', content)
        self.assertIn('renderedInline: false', content)

    def test_render_to_string_with_inline_true(self) -> None:
        """Testing ReviewUI.render_to_string with inline=True"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request()

        content = review_ui.render_to_string(request, inline=True)
        self.assertIsInstance(content, SafeText)
        self.assertIn('model: new RB.Test.ReviewUI(', content)
        self.assertIn('view = new RB.Test.ReviewUIView(', content)
        self.assertIn('renderedInline: true', content)

    def test_render_to_response_with_skip_static_media_false(self) -> None:
        """Testing ReviewUI.render_to_response with skip_static_media=0"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'skip-static-media': '0',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b'link href="/static/rb/css/js-tests.min.css" '
            b'rel="stylesheet" type="text/css"',
            response.content)
        self.assertIn(
            b'script type="text/javascript" src="/static/rb/js/admin.min.js"',
            response.content)

    def test_render_to_response_with_skip_static_media_true(self) -> None:
        """Testing ReviewUI.render_to_response with skip_static_media=1"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'skip-static-media': '1',
        })

        response = review_ui.render_to_response(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            b'link href="/static/rb/css/js-tests.min.css" '
            b'rel="stylesheet" type="text/css"',
            response.content)
        self.assertNotIn(
            b'script type="text/javascript" src="/static/rb/js/admin.min.js"',
            response.content)

    def test_render_to_string_with_skip_static_media_false(self) -> None:
        """Testing ReviewUI.render_to_response with skip_static_media=0"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'skip-static-media': '0',
        })

        content = review_ui.render_to_string(request)
        self.assertIn(
            'link href="/static/rb/css/js-tests.min.css" '
            'rel="stylesheet" type="text/css"',
            content)
        self.assertIn(
            'script type="text/javascript" src="/static/rb/js/admin.min.js"',
            content)

    def test_render_to_string_with_skip_static_media_true(self) -> None:
        """Testing ReviewUI.render_to_response with skip_static_media=1"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        request = self.create_http_request(data={
            'skip-static-media': '1',
        })

        content = review_ui.render_to_string(request)
        self.assertNotIn(
            'link href="/static/rb/css/js-tests.min.css" '
            'rel="stylesheet" type="text/css"',
            content)
        self.assertNotIn(
            'script type="text/javascript" src="/static/rb/js/admin.min.js"',
            content)

    def test_serialize_comments(self) -> None:
        """Testing ReviewUI.serialize_comments"""
        # Note that this test is factoring in both the user-owned draft
        # review created in setUp() and the ones created in this test.
        #
        # Comments from review1 and review2 will be included in the results.
        review1 = self.review

        review2 = self.create_review(self.review_request)
        self.create_file_attachment_comment(review2, self.attachment,
                                            text='Comment 3')

        # This will not be included.
        review3 = self.create_review(self.review_request,
                                     user=self.create_user('user2'),
                                     public=False)
        self.create_file_attachment_comment(review3, self.attachment,
                                            text='Comment 4')

        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=review1.user)

        comments = review_ui.serialize_comments(list(review_ui.get_comments()))

        self.assertEqual(len(comments), 3)
        self.assertEqual(comments['0'][0]['text'], 'Comment 1')
        self.assertEqual(comments['1'][0]['text'], 'Comment 2')
        self.assertEqual(comments['2'][0]['text'], 'Comment 3')

    def test_serialize_comment(self) -> None:
        """Testing ReviewUI.serialize_comment"""
        review_ui = MyReviewUI(review_request=self.review_request,
                               obj=DummyReviewableObject())
        review_ui.request = self.create_http_request(user=self.review.user)

        self.assertEqual(
            review_ui.serialize_comment(review_ui.get_comments()[0]),
            {
                'comment_id': 1,
                'html': 'Comment 1',
                'issue_opened': False,
                'issue_status': '',
                'localdraft': True,
                'reply_to_id': None,
                'review_id': 1,
                'review_request_id': 1,
                'rich_text': False,
                'text': 'Comment 1',
                'url': '/r/1/#fcomment1',
                'user': {'name': 'Dopey Dwarf', 'username': 'dopey'}
            })

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_url_diff(self) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to a diff
        """
        review_request = self.create_review_request(
            publish=True,
            create_repository=True)
        diffset = self.create_diffset(review_request=review_request)
        filediff = self.create_filediff(diffset=diffset, binary=True)

        attachment = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=filediff)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1/#file{filediff.pk}')

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_url_interdiff(self) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to an interdiff
        """
        review_request = self.create_review_request(
            publish=True,
            create_repository=True)

        diffset1 = self.create_diffset(review_request=review_request)
        filediff1 = self.create_filediff(diffset=diffset1, binary=True)
        attachment1 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=filediff1)

        diffset2 = self.create_diffset(
            review_request=review_request,
            revision=2)
        filediff2 = self.create_filediff(diffset=diffset2, binary=True)
        attachment2 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=filediff2)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment2,
            diff_against_file_attachment=attachment1)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment2)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1-2/#file{filediff2.pk}')

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_diff_with_commits(self) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to a diff that has commit history
        """
        review_request = self.create_review_request(
            publish=True, create_repository=True)

        diffset = self.create_diffset(review_request=review_request)

        cumulative_filediff = self.create_filediff(
            diffset=diffset,
            binary=True)

        commit = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False)
        commit_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit)

        attachment = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit_filediff)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1/#file{cumulative_filediff.pk}')

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_diff_with_commits_base_commit_id(self) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to a diff that has commit history with a specified base commit
        """
        review_request = self.create_review_request(
            publish=True, create_repository=True)

        diffset = self.create_diffset(review_request=review_request)

        # Cumulative filediff
        self.create_filediff(
            diffset=diffset,
            binary=True)

        commit1 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r1',
            parent_id='r0')
        commit1_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit1)
        self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit1_filediff)

        commit2 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r2',
            parent_id='r1')
        commit2_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit2)
        attachment2 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit2_filediff)

        commit3 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r3',
            parent_id='r2')
        commit3_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit3)
        attachment3 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit3_filediff)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment3,
            diff_against_file_attachment=attachment2)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment3)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1/?base-commit-id={commit2.pk}'
                         f'#file{commit3_filediff.pk}')

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_diff_with_commits_tip_commit_id(self) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to a diff that has commit history with a specified tip commit
        """
        review_request = self.create_review_request(
            publish=True, create_repository=True)

        diffset = self.create_diffset(review_request=review_request)

        # Cumulative filediff
        self.create_filediff(
            diffset=diffset,
            binary=True)

        upstream_attachment = self.create_file_attachment(
            review_request=review_request,
            repository=review_request.repository,
            with_history=False,
            repo_path='/test-file',
            repo_revision='r0')

        commit1 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r1',
            parent_id='r0')
        commit1_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit1)
        self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit1_filediff)

        commit2 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r2',
            parent_id='r1')
        commit2_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit2)
        attachment2 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit2_filediff)

        commit3 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r3',
            parent_id='r2')
        commit3_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit3)
        self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit3_filediff)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment2,
            diff_against_file_attachment=upstream_attachment)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment2)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1/?tip-commit-id={commit2.pk}'
                         f'#file{commit2_filediff.pk}')

    @add_fixtures(['test_scmtools'])
    def test_get_comment_link_diff_with_commits_base_and_tip_commit_id(
        self,
    ) -> None:
        """Testing ReviewUI.get_comment_link_url with a file attachment
        attached to a diff that has commit history with a specified base and
        tip commit
        """
        review_request = self.create_review_request(
            publish=True, create_repository=True)

        diffset = self.create_diffset(review_request=review_request)

        # Cumulative filediff
        self.create_filediff(
            diffset=diffset,
            binary=True)

        # Upstream attachment
        self.create_file_attachment(
            review_request=review_request,
            repository=review_request.repository,
            with_history=False,
            repo_path='/test-file',
            repo_revision='r0')

        commit1 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r1',
            parent_id='r0')
        commit1_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit1)
        attachment1 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit1_filediff)

        commit2 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r2',
            parent_id='r1')
        commit2_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit2)
        attachment2 = self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit2_filediff)

        commit3 = self.create_diffcommit(
            repository=review_request.repository,
            diffset=diffset,
            with_diff=False,
            commit_id='r3',
            parent_id='r2')
        commit3_filediff = self.create_filediff(
            diffset=diffset,
            binary=True,
            commit=commit3)
        self.create_file_attachment(
            review_request=review_request,
            with_history=False,
            added_in_filediff=commit3_filediff)

        review = self.create_review(review_request=review_request)
        comment = self.create_file_attachment_comment(
            review=review,
            file_attachment=attachment2,
            diff_against_file_attachment=attachment1)

        review_ui = MyReviewUI(
            review_request=review_request,
            obj=attachment2)

        self.assertEqual(review_ui.get_comment_link_url(comment),
                         f'/r/2/diff/1/?base-commit-id={commit1.pk}'
                         f'&tip-commit-id={commit2.pk}'
                         f'#file{commit2_filediff.pk}')
