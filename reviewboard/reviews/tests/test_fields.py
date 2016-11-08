from __future__ import unicode_literals

from django.utils import six
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.fields import BaseTextAreaField
from reviewboard.reviews.models import ReviewRequest
from reviewboard.testing import TestCase


class BaseTextAreaFieldTests(TestCase):
    """Unit tests for reviewboard.reviews.fields.BaseTextAreaField."""

    def test_render_change_entry_html(self):
        """Testing BaseTextAreaField.render_change_entry_html"""
        field = BaseTextAreaField(ReviewRequest())
        html = field.render_change_entry_html({
            'old': ['This is a test\n\nWith two lines'],
            'new': ['This is a test with one line'],
        })

        self.assertHTMLEqual(
            html,
            '<table class="diffed-text-area">'
            ' <tr class="replace-old">'
            '  <td class="marker">~</td>'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="line rich-text"><p>This is a test</p></td>'
            ' </tr>'
            ' <tr class="replace-new">'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="marker">~</td>'
            '  <td class="line rich-text">'
            '   <p>This is a test<span class="hl"> with one line</span></p>'
            '  </td>'
            ' </tr>'
            ' <tr class="delete">'
            '  <td class="marker">-</td>'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="line rich-text">\n</td>'
            ' </tr>'
            ' <tr class="delete">'
            '  <td class="marker">-</td>'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="line rich-text"><p>With two lines</p></td>'
            ' </tr>'
            '</table>')

    def test_render_change_entry_html_with_entities(self):
        """Testing BaseTextAreaField.render_change_entry_html with string
        containing entities
        """
        field = BaseTextAreaField(ReviewRequest())
        html = field.render_change_entry_html({
            'old': ['This "is" a <test>'],
            'new': ['This "is" a <test> with more stuff here'],
        })

        self.assertHTMLEqual(
            html,
            '<table class="diffed-text-area">'
            ' <tr class="replace-old">'
            '  <td class="marker">~</td>'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="line rich-text">'
            '   <p>This &quot;is&quot; a &lt;test&gt;</p>'
            '  </td>'
            ' </tr>'
            ' <tr class="replace-new">'
            '  <td class="marker">&nbsp;</td>'
            '  <td class="marker">~</td>'
            '  <td class="line rich-text">'
            '   <p>This &quot;is&quot; a &lt;test&gt;<span class="hl"> with '
            '      more stuff here</span></p>'
            '  </td>'
            ' </tr>'
            '</table>')


class FieldTests(TestCase):
    """Unit tests for review request fields."""

    # Bug #1352
    def test_long_bug_numbers(self):
        """Testing review requests with very long bug numbers"""
        review_request = ReviewRequest()
        review_request.bugs_closed = '12006153200030304432010,4432009'
        self.assertEqual(review_request.get_bug_list(),
                         ['4432009', '12006153200030304432010'])

    # Our _("(no summary)") string was failing in the admin UI, as
    # django.template.defaultfilters.stringfilter would fail on a
    # ugettext_lazy proxy object. We can use any stringfilter for this.
    #
    # Bug #1346
    def test_no_summary(self):
        """Testing review requests with no summary"""
        from django.template.defaultfilters import lower
        review_request = ReviewRequest()
        lower(review_request)

    @add_fixtures(['test_users'])
    def test_commit_id(self):
        """Testing commit_id migration"""
        review_request = self.create_review_request()
        review_request.changenum = '123'

        self.assertEqual(review_request.commit_id, None)
        self.assertEqual(review_request.commit,
                         six.text_type(review_request.changenum))
        self.assertNotEqual(review_request.commit_id, None)
