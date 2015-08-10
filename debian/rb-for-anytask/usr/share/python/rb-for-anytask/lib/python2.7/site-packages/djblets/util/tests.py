#
# tests.py -- Unit tests for classes in djblets.util
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import datetime
import unittest

from django.http import HttpRequest
from django.template import Token, TOKEN_TEXT, TemplateSyntaxError
from django.utils.html import strip_spaces_between_tags

from djblets.testing.testcases import TestCase, TagTest
from djblets.util.http import (get_http_accept_lists,
                               get_http_requested_mimetype,
                               is_mimetype_a)
from djblets.util.templatetags import (djblets_deco, djblets_email,
                                       djblets_utils)


def normalize_html(s):
    return strip_spaces_between_tags(s).strip()


class BoxTest(TagTest):
    def testPlain(self):
        """Testing box tag"""
        node = djblets_deco.box(self.parser, Token(TOKEN_TEXT, 'box'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testClass(self):
        """Testing box tag (with extra class)"""
        node = djblets_deco.box(self.parser, Token(TOKEN_TEXT, 'box "class"'))
        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="box-container"><div class="box class">' +
                         '<div class="box-inner">\ncontent\n  ' +
                         '</div></div></div>')

    def testError(self):
        """Testing box tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_deco.box(
                              self.parser,
                              Token(TOKEN_TEXT, 'box "class" "foo"')))


class ErrorBoxTest(TagTest):
    def testPlain(self):
        """Testing errorbox tag"""
        node = djblets_deco.errorbox(self.parser,
                                     Token(TOKEN_TEXT, 'errorbox'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox">\ncontent\n</div>')

    def testId(self):
        """Testing errorbox tag (with id)"""
        node = djblets_deco.errorbox(self.parser,
                                     Token(TOKEN_TEXT, 'errorbox "id"'))

        context = {}

        self.assertEqual(normalize_html(node.render(context)),
                         '<div class="errorbox" id="id">\ncontent\n</div>')

    def testError(self):
        """Testing errorbox tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_deco.errorbox(
                              self.parser,
                              Token(TOKEN_TEXT, 'errorbox "id" "foo"')))


class HttpTest(TestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = \
            'application/json;q=0.5,application/xml,text/plain;q=0.0,*/*;q=0.0'

    def test_http_accept_lists(self):
        """Testing djblets.http.get_http_accept_lists"""

        acceptable_mimetypes, unacceptable_mimetypes = \
            get_http_accept_lists(self.request)

        self.assertEqual(acceptable_mimetypes,
                         ['application/xml', 'application/json'])
        self.assertEqual(unacceptable_mimetypes, ['text/plain', '*/*'])

    def test_get_requested_mimetype_with_supported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with supported
        mimetype
        """
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['foo/bar',
                                                       'application/json']),
            'application/json')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/xml']),
            'application/xml')
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/xml')

    def test_get_requested_mimetype_with_no_consensus(self):
        """Testing djblets.http.get_requested_mimetype with no consensus
        between client and server
        """
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = ('text/html,application/xhtml+xml,'
                                            'application/xml;q=0.9,*/*;q=0.8')

        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/x-foo']),
            'application/json')

    def test_get_requested_mimetype_with_wildcard_supported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with supported */*
        mimetype
        """
        self.request = HttpRequest()
        self.request.META['HTTP_ACCEPT'] = '*/*'
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['application/json',
                                                       'application/xml']),
            'application/json')

    def test_get_requested_mimetype_with_unsupported_mimetype(self):
        """Testing djblets.http.get_requested_mimetype with unsupported
        mimetype
        """
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['text/plain']),
            None)
        self.assertEqual(
            get_http_requested_mimetype(self.request, ['foo/bar']),
            None)

    def test_is_mimetype_a(self):
        """Testing djblets.util.http.is_mimetype_a"""
        self.assertTrue(is_mimetype_a('application/json',
                                      'application/json'))
        self.assertTrue(is_mimetype_a('application/vnd.foo+json',
                                      'application/json'))
        self.assertFalse(is_mimetype_a('application/xml',
                                       'application/json'))
        self.assertFalse(is_mimetype_a('foo/vnd.bar+json',
                                       'application/json'))


class AgeIdTest(TagTest):
    def setUp(self):
        TagTest.setUp(self)

        self.now = datetime.datetime.utcnow()

        self.context = {
            'now': self.now,
            'minus1': self.now - datetime.timedelta(1),
            'minus2': self.now - datetime.timedelta(2),
            'minus3': self.now - datetime.timedelta(3),
            'minus4': self.now - datetime.timedelta(4),
        }

    def testNow(self):
        """Testing ageid tag (now)"""
        self.assertEqual(djblets_utils.ageid(self.now), 'age1')

    def testMinus1(self):
        """Testing ageid tag (yesterday)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(1)),
                         'age2')

    def testMinus2(self):
        """Testing ageid tag (two days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(2)),
                         'age3')

    def testMinus3(self):
        """Testing ageid tag (three days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(3)),
                         'age4')

    def testMinus4(self):
        """Testing ageid tag (four days ago)"""
        self.assertEqual(djblets_utils.ageid(self.now - datetime.timedelta(4)),
                         'age5')

    def testNotDateTime(self):
        """Testing ageid tag (non-datetime object)"""
        class Foo:
            def __init__(self, now):
                self.day = now.day
                self.month = now.month
                self.year = now.year

        self.assertEqual(djblets_utils.ageid(Foo(self.now)), 'age1')


class TestEscapeSpaces(unittest.TestCase):
    def test(self):
        """Testing escapespaces filter"""
        self.assertEqual(djblets_utils.escapespaces('Hi there'),
                         'Hi there')
        self.assertEqual(djblets_utils.escapespaces('Hi  there'),
                         'Hi&nbsp; there')
        self.assertEqual(djblets_utils.escapespaces('Hi  there\n'),
                         'Hi&nbsp; there<br />')


class TestHumanizeList(unittest.TestCase):
    def test0(self):
        """Testing humanize_list filter (length 0)"""
        self.assertEqual(djblets_utils.humanize_list([]), '')

    def test1(self):
        """Testing humanize_list filter (length 1)"""
        self.assertEqual(djblets_utils.humanize_list(['a']), 'a')

    def test2(self):
        """Testing humanize_list filter (length 2)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b']), 'a and b')

    def test3(self):
        """Testing humanize_list filter (length 3)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b', 'c']),
                         'a, b and c')

    def test4(self):
        """Testing humanize_list filter (length 4)"""
        self.assertEqual(djblets_utils.humanize_list(['a', 'b', 'c', 'd']),
                         'a, b, c, and d')


class TestIndent(unittest.TestCase):
    def test(self):
        """Testing indent filter"""
        self.assertEqual(djblets_utils.indent('foo'), '    foo')
        self.assertEqual(djblets_utils.indent('foo', 3), '   foo')
        self.assertEqual(djblets_utils.indent('foo\nbar'),
                         '    foo\n    bar')


class QuotedEmailTagTest(TagTest):
    def testInvalid(self):
        """Testing quoted_email tag (invalid usage)"""
        self.assertRaises(TemplateSyntaxError,
                          lambda: djblets_email.quoted_email(
                              self.parser,
                              Token(TOKEN_TEXT, 'quoted_email')))


class CondenseTagTest(TagTest):
    def getContentText(self):
        return "foo\nbar\n\n\n\n\n\n\nfoobar!"

    def test_plain(self):
        """Testing condense tag"""
        node = djblets_email.condense(self.parser,
                                      Token(TOKEN_TEXT, 'condense'))
        self.assertEqual(node.render({}), "foo\nbar\n\n\nfoobar!")

    def test_with_max_indents(self):
        """Testing condense tag with custom max_indents"""
        node = djblets_email.condense(self.parser,
                                      Token(TOKEN_TEXT, 'condense 1'))
        self.assertEqual(node.render({}), "foo\nbar\nfoobar!")


class QuoteTextFilterTest(unittest.TestCase):
    def testPlain(self):
        """Testing quote_text filter (default level)"""
        self.assertEqual(djblets_email.quote_text('foo\nbar'),
                         "> foo\n> bar")

    def testLevel2(self):
        """Testing quote_text filter (level 2)"""
        self.assertEqual(djblets_email.quote_text('foo\nbar', 2),
                         "> > foo\n> > bar")
