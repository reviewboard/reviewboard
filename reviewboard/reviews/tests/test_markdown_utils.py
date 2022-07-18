import io

import kgb
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.utils.safestring import SafeText
from markdown import __version_info__ as markdown_version_info

from reviewboard.accounts.models import Profile
from reviewboard.reviews.markdown_utils import (clean_markdown_html,
                                                markdown_render_conditional,
                                                normalize_text_for_edit,
                                                render_markdown,
                                                render_markdown_from_file)
from reviewboard.testing import TestCase


class MarkdownUtilsTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.reviews.markdown_utils."""

    def test_render_markdown_preserves_self_closed_tags(self):
        """Testing render_markdown preserves self-closed tags"""
        self.assertEqual(render_markdown('line1\n'
                                         'line2\n'
                                         '---'),
                         '<p>line1<br />\n'
                         'line2</p>\n'
                         '<hr />')

    def test_render_markdown_sanitizes_images(self):
        """Testing render_markdown sanitizes XSS in images"""
        self._test_clean_markdown_images_xss(render_markdown)

    def test_render_markdown_sanitizes_links(self):
        """Testing render_markdown sanitizes XSS in links"""
        self._test_clean_markdown_links_xss(render_markdown)

    def test_render_markdown_from_file_sanitizes_images(self):
        """Testing render_markdown_from_file sanitizes XSS in images"""
        self._test_clean_markdown_images_xss(
            lambda content: render_markdown_from_file(
                io.BytesIO(content.encode('utf-8'))))

    def test_render_markdown_from_file_sanitizes_links(self):
        """Testing render_markdown_from_file sanitizes XSS in links"""
        self._test_clean_markdown_links_xss(
            lambda content: render_markdown_from_file(
                io.BytesIO(content.encode('utf-8'))))

    def test_render_markdown_with_bold(self):
        """Testing render_markdown with bold"""
        self.assertEqual(
            render_markdown('**bold**'),
            '<p><strong>bold</strong></p>')

        self.assertEqual(
            render_markdown('__bold__'),
            '<p><strong>bold</strong></p>')

        self.assertEqual(
            render_markdown('mid**bold**word'),
            '<p>mid<strong>bold</strong>word</p>')

        self.assertEqual(
            render_markdown('mid__notbold__word'),
            '<p>mid__notbold__word</p>')

    def test_render_markdown_with_bold_italic(self):
        """Testing render_markdown with bold and italic"""
        self.assertEqual(
            render_markdown('*this is a __test__.*'),
            '<p><em>this is a <strong>test</strong>.</em></p>')

        self.assertEqual(
            render_markdown('_**test**_'),
            '<p><em><strong>test</strong></em></p>')

    def test_render_markdown_with_blockquotes(self):
        """Testing render_markdown with blockquotes"""
        self.assertEqual(
            render_markdown(
                '> here is a line\n'
                '> and another\n'
            ),
            '<p></p>\n'
            '<p></p>\n'
            '<blockquote>\n'
            '<p>here is a line<br />\n'
            'and another</p>\n'
            '</blockquote>')

    def test_render_markdown_with_code_blocks(self):
        """Testing render_markdown with code blocks"""
        if markdown_version_info[:2] >= (3, 2):
            # Markdown 3.2 adds <code> around each line of code. See
            # https://python-markdown.github.io/change_log/release-3.2/
            expected_html1 = (
                '<p></p>\n'
                '<div class="codehilite"><pre><span></span>'
                '<code>here is a generic code block\n'
                '</code></pre></div>'
            )
            expected_html2 = (
                '<p></p>\n'
                '<div class="codehilite"><pre><span></span>'
                '<code><span class="c1"># Here is a Python code block</span>\n'
                '</code></pre></div>'
            )
        else:
            expected_html1 = (
                '<p></p>\n'
                '<div class="codehilite"><pre><span></span>'
                'here is a generic code block\n'
                '</pre></div>'
            )
            expected_html2 = (
                '<p></p>\n'
                '<div class="codehilite"><pre><span></span>'
                '<span class="c1"># Here is a Python code block</span>\n'
                '</pre></div>'
            )

        self.assertEqual(
            render_markdown(
                '```\n'
                'here is a generic code block\n'
                '```\n'
            ),
            expected_html1)

        self.assertEqual(
            render_markdown(
                '```python\n'
                '# Here is a Python code block\n'
                '```\n'
            ),
            expected_html2)

    def test_render_markdown_with_emojis(self):
        """Testing render_markdown with emojis"""
        self.assertEqual(
            render_markdown(':thumbsup:'),
            '<p><img alt="\U0001f44d" class="emoji" '
            'src="https://github.githubassets.com/images/icons/emoji/'
            'unicode/1f44d.png" title=":thumbsup:" /></p>')

    def test_render_markdown_with_headers(self):
        """Testing render_markdown with headers"""
        self.assertEqual(
            render_markdown(
                'Header\n'
                '======\n'
                '\n'
                '# Header\n'
                '\n'
                'Subheader\n'
                '---------\n'
                '\n'
                '## Subheader\n'
                '\n'
                '### Sub-subheader\n'
                '\n'
                '#### Sub-sub-subheader\n'),
            '<h1>Header</h1>\n'
            '<h1>Header</h1>\n'
            '<h2>Subheader</h2>\n'
            '<h2>Subheader</h2>\n'
            '<h3>Sub-subheader</h3>\n'
            '<h4>Sub-sub-subheader</h4>')

    def test_render_markdown_with_images(self):
        """Testing render_markdown with images"""
        self.assertEqual(
            render_markdown('![my image](https://example.com/logo.png)'),
            '<p><img alt="my image" src="https://example.com/logo.png" />'
            '</p>')

    def test_render_markdown_with_inline_code(self):
        """Testing render_markdown with inline code"""
        self.assertEqual(
            render_markdown('here is ``inline code``'),
            '<p>here is <code>inline code</code></p>')

    def test_render_markdown_with_italic(self):
        """Testing render_markdown with italic"""
        self.assertEqual(
            render_markdown('*italic*'),
            '<p><em>italic</em></p>')

        self.assertEqual(
            render_markdown('_italic_'),
            '<p><em>italic</em></p>')

        self.assertEqual(
            render_markdown('mid*italic*word'),
            '<p>mid<em>italic</em>word</p>')

        self.assertEqual(
            render_markdown('mid_notitalic_word'),
            '<p>mid_notitalic_word</p>')

    def test_render_markdown_with_links(self):
        """Testing render_markdown with links"""
        self.assertEqual(
            render_markdown('[my link](https://www.reviewboard.org/)'),
            '<p><a href="https://www.reviewboard.org/">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](http://www.reviewboard.org/)'),
            '<p><a href="http://www.reviewboard.org/">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](mailto:user@example.com)'),
            '<p><a href="mailto:user@example.com">my link</a></p>')

        # Anything else is filtered out.
        self.assertEqual(
            render_markdown('[my link](ftp://ftp.example.com)'),
            '<p><a>my link</a></p>')
        self.assertEqual(
            render_markdown('custom://example.com'),
            '<p>custom://example.com</p>')

    @override_settings(ALLOWED_MARKDOWN_URL_PROTOCOLS=['custom', 'ftp'])
    def test_render_markdown_with_links_and_setting(self):
        """Testing render_markdown with links and
        settings.ALLOWED_MARKDOWN_URL_PROTOCOLS
        """
        self.assertEqual(
            render_markdown('[my link](https://www.reviewboard.org/)'),
            '<p><a href="https://www.reviewboard.org/">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](http://www.reviewboard.org/)'),
            '<p><a href="http://www.reviewboard.org/">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](mailto:user@example.com)'),
            '<p><a href="mailto:user@example.com">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](ftp://ftp.example.com)'),
            '<p><a href="ftp://ftp.example.com">my link</a></p>')
        self.assertEqual(
            render_markdown('[my link](custom://ftp.example.com)'),
            '<p><a href="custom://ftp.example.com">my link</a></p>')

        # Anything else is filtered out.
        self.assertEqual(
            render_markdown('[my link](other://example.com/)'),
            '<p><a>my link</a></p>')
        self.assertEqual(
            render_markdown('custom2://example.com'),
            '<p>custom2://example.com</p>')

    def test_render_markdown_with_lists_ordered(self):
        """Testing render_markdown with ordered lists"""
        self.assertEqual(
            render_markdown(
                '1. Item 1\n'
                '2. Item 2\n'
                '    1. Item 2.1\n'
                '3. Item 3\n'
            ),
            '<ol>\n'
            '<li>Item 1</li>\n'
            '<li>Item 2<ol>\n'
            '<li>Item 2.1</li>\n'
            '</ol>\n'
            '</li>\n'
            '<li>Item 3</li>\n'
            '</ol>')

    def test_render_markdown_with_lists_unordered(self):
        """Testing render_markdown with unordered lists"""
        self.assertEqual(
            render_markdown(
                '* Item 1\n'
                '* Item 2\n'
                '    * Item 2.1\n'
                '* Item 3\n'
            ),
            '<ul>\n'
            '<li>Item 1</li>\n'
            '<li>Item 2<ul>\n'
            '<li>Item 2.1</li>\n'
            '</ul>\n'
            '</li>\n'
            '<li>Item 3</li>\n'
            '</ul>')

        self.assertEqual(
            render_markdown(
                '- Item 1\n'
                '- Item 2\n'
                '    - Item 2.1\n'
                '- Item 3\n'
            ),
            '<ul>\n'
            '<li>Item 1</li>\n'
            '<li>Item 2<ul>\n'
            '<li>Item 2.1</li>\n'
            '</ul>\n'
            '</li>\n'
            '<li>Item 3</li>\n'
            '</ul>')

    def test_render_markdown_with_tables(self):
        """Testing render_markdown with tables"""
        self.assertEqual(
            render_markdown(
                '| Header | Header |\n'
                '|--------|--------|\n'
                '| Cell   | Cell   |\n'
                '| Cell   | Cell   |'
            ),
            '<table>\n'
            '<thead>\n'
            '<tr>\n'
            '<th>Header</th>\n'
            '<th>Header</th>\n'
            '</tr>\n'
            '</thead>\n'
            '<tbody>\n'
            '<tr>\n'
            '<td>Cell</td>\n'
            '<td>Cell</td>\n'
            '</tr>\n'
            '<tr>\n'
            '<td>Cell</td>\n'
            '<td>Cell</td>\n'
            '</tr>\n'
            '</tbody>\n'
            '</table>'
        )

    def test_render_markdown_with_strikethrough(self):
        """Testing render_markdown with strikethrough"""
        self.assertEqual(
            render_markdown('~~strike~~'),
            '<p><del>strike</del></p>')

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

    def _test_clean_markdown_images_xss(self, render_func):
        self.spy_on(clean_markdown_html)

        # This list courtesy of the cheat sheet at
        # https://github.com/cujanovic/Markdown-XSS-Payloads/
        #
        # To ensure clarity, blank lines have been added between each XSS
        # test/result.
        html = render_func('\n\n'.join([
            r'![XSS1](javascript:prompt(document.cookie))\\',

            r'![XSS2](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L'
            r'3NjcmlwdD4K)\\',

            r'![XSS3\'"`onerror=prompt(document.cookie)](x)\\',

            r'![XSS4](https://example.com/image.png"onload="alert(1))',

            r'![XSS5]("onerror="alert(1))',
        ]))

        self.assertEqual(
            html.split('\n'),
            [
                r'<p><img alt="XSS1" />\</p>',

                r'<p><img alt="XSS2" />\</p>',

                r'<p><img alt="XSS3\'&quot;`onerror=prompt(document.cookie)" '
                r'src="x" />\</p>',

                r'<p><img alt="XSS4" src="https://example.com/image.png&quot;'
                r'onload=&quot;alert(1" />)</p>',

                r'<p><img alt="XSS5" src="&quot;onerror=&quot;alert(1" />'
                r')</p>',
            ])

        self.assertSpyCallCount(clean_markdown_html, 1)

    def _test_clean_markdown_links_xss(self, render_func):
        self.spy_on(clean_markdown_html)

        html = render_func('\n\n'.join([
            r'[XSS1](javascript:alert("oh no"))',

            r'[XSS2](j&#X41vascript:alert("oh no"))',

            r'[XSS3](j  a  v  a  s  c  r  i  p  t:alert("oh no"))',

            r'[XSS4](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8'
            r'L3NjcmlwdD4K)',

            r'[XSS5](&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70&#x74'
            r'&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53&#x53'
            r'&#x27&#x29)',

            r'[XSS6](javascript:window.onerror=alert;throw%20'
            r'document.cookie)',

            r'[XSS7](javascript://%0d%0aprompt(1))',

            r'[XSS8](javascript://%0d%0aprompt(1);com)',

            r'[XSS9](javascript:window.onerror=alert;throw%20'
            r'document.cookie)',

            r'[XSS10](javascript://%0d%0awindow.onerror=alert;'
            r'throw%20document.cookie)',

            r'[XSS11](data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8'
            r'L3NjcmlwdD4K)',

            r'[XSS12](vbscript:alert(document.domain))',

            r'[XSS13](https://example.com " [@bad](/bad) ")',

            r'[XSS14](javascript:this,alert(1))',

            r'[XSS15](javascript:this,alert(1&#41;))',

            r'[XSS16](javascript&#58this;alert(1&#41;)',

            r'[XSS17](Javas&#99;ript:alert(1&#41;)',

            r'[XSS18](Javas%26%2399;ript:alert(1&#41;)',

            r'[XSS19](javascript:alert&#65534;(1&#41;)',

            r'[XSS20](javascript:confirm(1)',

            r'[XSS21](javascript://example.com%0Aprompt(1))',

            r'[XSS22](javascript://%0d%0aconfirm(1);com)',

            r'[XSS23](javascript:window.onerror=confirm;throw%201)',

            r'[XSS24](javascript:alert(document.domain&#41;)',

            r'[XSS25](javascript://example.com%0Aalert(1))',

            r'[XSS26](\'javascript:alert("1")\')',

            r'[XSS27](JaVaScRiPt:alert(1))',

            r'[XSS28](.alert(1);)',

            r'XSS29: [ ](https://a.de?p=[[/data-x=. style='
            r'background-color:#000000;z-index:999;width:100%;'
            r'position:fixed;top:0;left:0;right:0;bottom:0; data-y=.]])',

            r'XSS30: [ ](http://a?p=[[/onclick=alert(0) .]])',

            r'[XSS31](javascript:new%20Function`al\ert\`1\``;)',

            r'[XSS32](javascript:new%20Function`al\ert\`1\``;)',

            r'XSS33: <http://\<meta\ http-equiv=\"refresh\"\ '
            r'content=\"0;\ url=http://example.com/\"\>>',

            r'XSS33: </http://<?php\><\h1\><script:script>confirm(2)',

            r'XSS34: <javascript:prompt(document.cookie)>',

            r'XSS35: <&#x6A&#x61&#x76&#x61&#x73&#x63&#x72&#x69&#x70'
            r'&#x74&#x3A&#x61&#x6C&#x65&#x72&#x74&#x28&#x27&#x58&#x53'
            r'&#x53&#x27&#x29>',

            r'XSS36: _http://example_@.1 style=background-image:url('
            r'data:image/png;base64,ABCABCABCABC==);'
            r'background-repeat:no-repeat;display:block;width:100%;'
            r'height:100px; onclick=alert(unescape(/Oh%20No!/.source));'
            r'return(false);//',

            'XSS37:\n[cite]: (javascript:prompt(document.cookie))',
        ]))

        # This list courtesy of the cheat sheet at
        # https://github.com/cujanovic/Markdown-XSS-Payloads/
        #
        # To ensure clarity, blank lines have been added between each XSS
        # test/result.
        self.assertEqual(
            html.split('\n'),
            [
                r'<p><a title="oh no">XSS1</a>)</p>',

                r'<p><a href="j&amp;#X41vascript:alert(" title="oh no">'
                r'XSS2</a>)</p>',

                r'<p><a title="oh no">XSS3</a>)</p>',

                r'<p><a>XSS4</a></p>',

                r'<p><a href="&amp;#x6A&amp;#x61&amp;#x76&amp;#x61&amp;#x73'
                r'&amp;#x63&amp;#x72&amp;#x69&amp;#x70&amp;#x74&amp;#x3A'
                r'&amp;#x61&amp;#x6C&amp;#x65&amp;#x72&amp;#x74&amp;#x28'
                r'&amp;#x27&amp;#x58&amp;#x53&amp;#x53&amp;#x27&amp;#x29">'
                r'XSS5</a></p>',

                r'<p><a>XSS6</a></p>',

                r'<p><a>XSS7</a></p>',

                r'<p><a>XSS8</a></p>',

                r'<p><a>XSS9</a></p>',

                r'<p><a>XSS10</a></p>',

                r'<p><a>XSS11</a></p>',

                r'<p><a>XSS12</a></p>',

                r'<p><a href="https://example.com"'
                r' title="[@bad](/bad)">XSS13</a></p>',

                r'<p><a>XSS14</a></p>',

                r'<p><a>XSS15</a></p>',

                r'<p>[XSS16](javascript&amp;#58this;alert(1&#41;)</p>',

                r'<p>[XSS17](Javas&#99;ript:alert(1&#41;)</p>',

                r'<p>[XSS18](Javas%26%2399;ript:alert(1&#41;)</p>',

                r'<p>[XSS19](javascript:alert&#65534;(1&#41;)</p>',

                r'<p>[XSS20](javascript:confirm(1)</p>',

                r'<p><a>XSS21</a></p>',

                r'<p><a>XSS22</a></p>',

                r'<p><a>XSS23</a></p>',

                r'<p>[XSS24](javascript:alert(document.domain&#41;)</p>',

                r'<p><a>XSS25</a></p>',

                r'<p><a href="\'javascript:alert(" title="1">XSS26</a>\')</p>',

                r'<p><a>XSS27</a></p>',

                r'<p><a href=".alert(1);">XSS28</a></p>',

                r'<p>XSS29: <a href="https://a.de?p=[[/data-x=. style='
                r'background-color:#000000;z-index:999;width:100%;'
                r'position:fixed;top:0;left:0;right:0;bottom:0; data-y=.]]"> '
                r'</a></p>',

                r'<p>XSS30: <a href="http://a?p=[[/onclick=alert(0) .]]"> '
                r'</a></p>',

                r'<p><a>XSS31</a></p>',

                r'<p><a>XSS32</a></p>',

                r'<p>XSS33: &lt;http://\&lt;meta http-equiv=\"'
                r'refresh\" content=\"0; url=http://example.com/\"&gt;&gt;'
                r'</p>',

                r'<p>XSS33: &lt;/http://&lt;?php&gt;&lt;\h1&gt;&lt;'
                r'script:script&gt;confirm(2)</p>',

                r'<p>XSS34: &lt;javascript:prompt(document.cookie)&gt;</p>',

                r'<p>XSS35: &lt;&amp;#x6A&amp;#x61&amp;#x76&amp;#x61&amp;#x73'
                r'&amp;#x63&amp;#x72&amp;#x69&amp;#x70&amp;#x74&amp;#x3A'
                r'&amp;#x61&amp;#x6C&amp;#x65&amp;#x72&amp;#x74&amp;#x28'
                r'&amp;#x27&amp;#x58&amp;#x53&amp;#x53&amp;#x27&amp;#x29&gt;'
                r'</p>',

                r'<p>XSS36: <em>http://example</em>@.1 style='
                r'background-image:url(data:image/png;base64,ABCABCABCABC==);'
                r'background-repeat:no-repeat;display:block;width:100%;'
                r'height:100px; onclick=alert(unescape(/Oh%20No!/.source));'
                r'return(false);//</p>',

                r'<p>XSS37:</p>',
            ])

        self.assertSpyCallCount(clean_markdown_html, 1)
