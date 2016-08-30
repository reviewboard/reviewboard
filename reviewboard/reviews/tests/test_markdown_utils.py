from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils.safestring import SafeText

from reviewboard.accounts.models import Profile
from reviewboard.reviews.markdown_utils import (markdown_render_conditional,
                                                normalize_text_for_edit)
from reviewboard.testing import TestCase


class MarkdownUtilsTests(TestCase):
    """Unit tests for reviewboard.reviews.markdown_utils."""

    def test_normalize_text_for_edit_rich_text_default_rich_text(self):
        """Testing normalize_text_for_edit with rich text and
        user defaults to rich text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=True)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_default_rich_text(self):
        """Testing normalize_text_for_edit with plain text and
        user defaults to rich text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=True)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=False)
        self.assertEqual(text, r'&amp;lt; &quot;test&quot; \*\*foo\*\*')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_rich_text_default_plain_text(self):
        """Testing normalize_text_for_edit with rich text and
        user defaults to plain text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_default_plain_text(self):
        """Testing normalize_text_for_edit with plain text and
        user defaults to plain text
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True)
        self.assertEqual(text, '&amp;lt; &quot;test&quot; **foo**')
        self.assertTrue(isinstance(text, SafeText))

    def test_normalize_text_for_edit_rich_text_no_escape(self):
        """Testing normalize_text_for_edit with rich text and not
        escaping to HTML
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True, escape_html=False)
        self.assertEqual(text, '&lt; "test" **foo**')
        self.assertFalse(isinstance(text, SafeText))

    def test_normalize_text_for_edit_plain_text_no_escape(self):
        """Testing normalize_text_for_edit with plain text and not
        escaping to HTML
        """
        user = User.objects.create_user('test', 'test@example.com')
        Profile.objects.create(user=user, default_use_rich_text=False)

        text = normalize_text_for_edit(user, text='&lt; "test" **foo**',
                                       rich_text=True, escape_html=False)
        self.assertEqual(text, '&lt; "test" **foo**')
        self.assertFalse(isinstance(text, SafeText))

    def test_markdown_render_conditional_rich_text(self):
        """Testing markdown_render_conditional with rich text"""
        text = markdown_render_conditional(text='## <script>alert();</script>',
                                           rich_text=True)
        self.assertEqual(text,
                         '<h2>&lt;script&gt;alert();&lt;/script&gt;</h2>')
        self.assertFalse(isinstance(text, SafeText))

    def test_markdown_render_conditional_plain_text(self):
        """Testing markdown_render_conditional with plain text"""
        text = markdown_render_conditional(text='## <script>alert();</script>',
                                           rich_text=False)
        self.assertEqual(text, r'## &lt;script&gt;alert();&lt;/script&gt;')
        self.assertTrue(isinstance(text, SafeText))
