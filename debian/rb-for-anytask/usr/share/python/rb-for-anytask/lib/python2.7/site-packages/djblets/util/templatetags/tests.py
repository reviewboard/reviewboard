from __future__ import unicode_literals

from djblets.testing.testcases import TestCase
from djblets.util.templatetags.djblets_js import json_dumps


class JSTagTests(TestCase):
    """Unit tests for djblets_js template tags."""
    def test_json_dumps_xss(self):
        """Testing json_dumps doesn't allow XSS injection"""
        # This is bug 3406.
        obj = {
            'xss': '</script><script>alert(1);</script>'
        }

        self.assertEqual(
            json_dumps(obj),
            '{"xss": "\\u003C/script\\u003E\\u003Cscript\\u003E'
            'alert(1);\\u003C/script\\u003E"}')
