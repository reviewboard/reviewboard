import datetime
import unittest

from django.template import Token, TOKEN_TEXT, TemplateSyntaxError
from django.utils.html import strip_spaces_between_tags
from djblets.util.testing import TagTest

from reviewboard.utils.templatetags import htmlutils


def normalize_html(s):
    return strip_spaces_between_tags(s).strip()


class BoxTest(TagTest):
    def testPlain(self):
        """Testing box tag"""
        node = htmlutils.box(self.parser,
                             Token(TOKEN_TEXT, 'box'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testClass(self):
        """Testing box tag (with extra class)"""
        node = htmlutils.box(self.parser,
                             Token(TOKEN_TEXT, 'box "class"'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box class">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testError(self):
        """Testing box tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.box(self.parser,
                                                Token(TOKEN_TEXT,
                                                      'box "class" "foo"')))


class ErrorBoxTest(TagTest):
    def testPlain(self):
        """Testing errorbox tag"""
        node = htmlutils.errorbox(self.parser,
                                  Token(TOKEN_TEXT, 'errorbox'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox">\ncontent\n</div>')

    def testId(self):
        """Testing errorbox tag (with id)"""
        node = htmlutils.errorbox(self.parser,
                                  Token(TOKEN_TEXT, 'errorbox "id"'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox" id="id">\ncontent\n</div>')


    def testError(self):
        """Testing errorbox tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.errorbox(self.parser,
                                                     Token(TOKEN_TEXT,
                                                           'errorbox "id" ' +
                                                           '"foo"')))


class AgeIdTest(TagTest):
    def setUp(self):
        TagTest.setUp(self)

        self.now = datetime.datetime.now()

        self.context = {
            'now':    self.now,
            'minus1': self.now - datetime.timedelta(1),
            'minus2': self.now - datetime.timedelta(2),
            'minus3': self.now - datetime.timedelta(3),
            'minus4': self.now - datetime.timedelta(4),
        }

    def testNow(self):
        """Testing ageid tag (now)"""
        self.assertEqual(htmlutils.ageid(self.now), 'age1')

    def testMinus1(self):
        """Testing ageid tag (yesterday)"""
        self.assertEqual(htmlutils.ageid(self.now - datetime.timedelta(1)),
                         'age2')

    def testMinus2(self):
        """Testing ageid tag (two days ago)"""
        self.assertEqual(htmlutils.ageid(self.now - datetime.timedelta(2)),
                         'age3')

    def testMinus3(self):
        """Testing ageid tag (three days ago)"""
        self.assertEqual(htmlutils.ageid(self.now - datetime.timedelta(3)),
                         'age4')

    def testMinus4(self):
        """Testing ageid tag (four days ago)"""
        self.assertEqual(htmlutils.ageid(self.now - datetime.timedelta(4)),
                         'age5')

    def testNotDateTime(self):
        """Testing ageid tag (non-datetime object)"""
        class Foo:
            def __init__(self, now):
                self.day   = now.day
                self.month = now.month
                self.year  = now.year

        self.assertEqual(htmlutils.ageid(Foo(self.now)), 'age1')


class TestEscapeSpaces(unittest.TestCase):
    def test(self):
        """Testing escapespaces filter"""
        self.assertEqual(htmlutils.escapespaces('Hi there'),
                         'Hi there')
        self.assertEqual(htmlutils.escapespaces('Hi  there'),
                         'Hi&nbsp; there')
        self.assertEqual(htmlutils.escapespaces('Hi  there\n'),
                         'Hi&nbsp; there<br />')


class TestHumanizeList(unittest.TestCase):
    def test0(self):
        """Testing humanize_list filter (length 0)"""
        self.assertEqual(htmlutils.humanize_list([]), '')

    def test1(self):
        """Testing humanize_list filter (length 1)"""
        self.assertEqual(htmlutils.humanize_list(['a']), 'a')

    def test2(self):
        """Testing humanize_list filter (length 2)"""
        self.assertEqual(htmlutils.humanize_list(['a', 'b']), 'a and b')

    def test3(self):
        """Testing humanize_list filter (length 3)"""
        self.assertEqual(htmlutils.humanize_list(['a', 'b', 'c']),
                         'a, b and c')

    def test4(self):
        """Testing humanize_list filter (length 4)"""
        self.assertEqual(htmlutils.humanize_list(['a', 'b', 'c', 'd']),
                         'a, b, c, and d')


class TestIndent(unittest.TestCase):
    def test(self):
        """Testing indent filter"""
        self.assertEqual(htmlutils.indent('foo'), '    foo')
        self.assertEqual(htmlutils.indent('foo', 3), '   foo')
        self.assertEqual(htmlutils.indent('foo\nbar'), '    foo\n    bar')
