import datetime
import unittest

from django.template import Node, Token, TOKEN_TEXT, TemplateSyntaxError

from reviewboard.utils.templatetags import htmlutils


class StubNodeList(Node):
    def render(self, context):
        return 'content'


class StubParser:
    def parse(self, until):
        return StubNodeList()

    def delete_first_token(self):
        pass


class TagTest(unittest.TestCase):
    """Base testing setup for utils.templatetags.htmlutils"""

    def setUp(self):
        self.parser = StubParser()


class BoxTest(TagTest):
    def testPlain(self):
        """Testing box tag"""
        node = htmlutils.box(self.parser,
                             Token(TOKEN_TEXT, 'box'))
        context = {}

        self.assertEqual(node.render_title_area(context), '')
        self.assertEqual(node.render(context),
                         '<div class="box-container"><div class="box">\n' +
                         '<div class="box-inner">content</div></div></div>\n')

    def testClass(self):
        """Testing box tag (with extra class)"""
        node = htmlutils.box(self.parser,
                             Token(TOKEN_TEXT, 'box class'))
        context = {}

        self.assertEqual(node.render_title_area(context), '')
        self.assertEqual(node.render(context),
                         '<div class="box-container"><div class="box class">\n' +
                         '<div class="box-inner">content</div></div></div>\n')

    def testError(self):
        """Testing box tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.box(self.parser,
                                                Token(TOKEN_TEXT,
                                                      'box class foo')))


class ErrorBoxTest(TagTest):
    def testPlain(self):
        """Testing errorbox tag"""
        node = htmlutils.errorbox(self.parser,
                                  Token(TOKEN_TEXT, 'errorbox'))

        context = {}

        self.assertEqual(node.render(context),
                         '<div class="errorbox">\ncontent</div>')

    def testId(self):
        """Testing errorbox tag (with id)"""
        node = htmlutils.errorbox(self.parser,
                                  Token(TOKEN_TEXT, 'errorbox id'))

        context = {}

        self.assertEqual(node.render(context),
                         '<div class="errorbox" id="id">\ncontent</div>')


    def testError(self):
        """Testing errorbox tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.errorbox(self.parser,
                                                     Token(TOKEN_TEXT,
                                                           'errorbox id foo')))


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
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid now'))

        self.assertEqual(node.render(self.context), 'age1')

    def testMinus1(self):
        """Testing ageid tag (yesterday)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid minus1'))

        self.assertEqual(node.render(self.context), 'age2')

    def testMinus2(self):
        """Testing ageid tag (two days ago)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid minus2'))

        self.assertEqual(node.render(self.context), 'age3')

    def testMinus3(self):
        """Testing ageid tag (three days ago)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid minus3'))

        self.assertEqual(node.render(self.context), 'age4')

    def testMinus4(self):
        """Testing ageid tag (four days ago)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid minus4'))

        self.assertEqual(node.render(self.context), 'age5')

    def testNotDateTime(self):
        """Testing ageid tag (non-datetime object)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid foo'))
        class Foo:
            def __init__(self, now):
                self.day   = now.day
                self.month = now.month
                self.year  = now.year

        context = {'foo': Foo(self.now),}
        self.assertEqual(node.render(context), 'age1')

    def testError1(self):
        """Testing ageid tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.ageid(self.parser,
                                                  Token(TOKEN_TEXT,
                                                        'ageid')))

        self.assertRaises(TemplateSyntaxError,
                          lambda: htmlutils.ageid(self.parser,
                                                  Token(TOKEN_TEXT,
                                                        'ageid timestamp foo')))

    def testError2(self):
        """Testing ageid tag (bad variable name)"""
        node = htmlutils.ageid(self.parser,
                               Token(TOKEN_TEXT, 'ageid foo'))

        self.assertRaises(TemplateSyntaxError,
                          lambda: node.render({}))


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
        self.assertEqual(htmlutils.indent('foo'), '    foo')
        self.assertEqual(htmlutils.indent('foo', 3), '   foo')
        self.assertEqual(htmlutils.indent('foo\nbar'), '    foo\n    bar')
