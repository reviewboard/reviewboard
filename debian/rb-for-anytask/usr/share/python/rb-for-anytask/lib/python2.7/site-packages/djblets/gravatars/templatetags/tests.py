from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Token, TOKEN_TEXT

from djblets.testing.testcases import TagTest
from djblets.gravatars.templatetags.gravatars import gravatar


class DummyRequest(object):
    def is_secure(self):
        return False


class TagTests(TagTest):
    """Unit tests for gravatars template tags."""
    def test_gravatar_xss(self):
        """Testing {% gravatar %} doesn't allow XSS injection"""
        user = User(username='test',
                    first_name='"><script>alert(1);</script><"',
                    email='test@example.com')

        node = gravatar(self.parser, Token(TOKEN_TEXT, 'gravatar user 32'))
        context = {
            'request': DummyRequest(),
            'user': user,
        }

        self.assertEqual(
            node.render(context),
            '<img src="http://www.gravatar.com/avatar/'
            '55502f40dc8b7c769880b10874abc9d0?s=32" width="32" height="32" '
            'alt="&quot;&gt;&lt;script&gt;alert(1);&lt;/script&gt;&lt;&quot;" '
            'class="gravatar"/>')
