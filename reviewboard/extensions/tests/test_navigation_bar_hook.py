"""Unit tests for reviewboard.extensions.hooks.NavigationBarHook."""

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.template import Context, Template
from djblets.extensions.manager import ExtensionManager

from reviewboard.extensions.hooks import NavigationBarHook
from reviewboard.extensions.tests.testcases import DummyExtension
from reviewboard.testing.testcase import TestCase


class NavigationBarHookTests(TestCase):
    """Tests the navigation bar hooks."""

    def setUp(self):
        super(NavigationBarHookTests, self).setUp()

        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

    def tearDown(self):
        super(NavigationBarHookTests, self).tearDown()

        self.extension.shutdown()

    def test_navigation_bar_hooks(self):
        """Testing navigation entry extension hooks"""
        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_is_enabled_for_true(self):
        """Testing NavigationBarHook.is_enabled_for and returns true"""
        def is_enabled_for(**kwargs):
            self.assertEqual(kwargs['user'], request.user)
            self.assertEqual(kwargs['request'], request)
            self.assertEqual(kwargs['local_site_name'], 'test-site')

            return True

        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry],
                                 is_enabled_for=is_enabled_for)

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_is_enabled_for_false(self):
        """Testing NavigationBarHook.is_enabled_for and returns false"""
        def is_enabled_for(**kwargs):
            self.assertEqual(kwargs['user'], request.user)
            self.assertEqual(kwargs['request'], request)
            self.assertEqual(kwargs['local_site_name'], 'test-site')

            return False

        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry],
                                 is_enabled_for=is_enabled_for)

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 0)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(), '')

    def test_navigation_bar_hooks_with_is_enabled_for_legacy(self):
        """Testing NavigationBarHook.is_enabled_for and legacy argument
        format
        """
        def is_enabled_for(user):
            self.assertEqual(user, request.user)

            return True

        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry],
                                 is_enabled_for=is_enabled_for)

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_url_name(self):
        """Testing navigation entry extension hooks with url names"""
        entry = {
            'label': 'Test Nav Entry',
            'url_name': 'dashboard',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        request = self.client.request()
        request.user = User(username='text')

        context = Context({
            'request': request,
            'local_site_name': 'test-site',
        })
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            '{% load rb_extensions %}'
            '{% navigation_bar_hooks %}')

        self.assertEqual(
            t.render(context).strip(),
            '<li><a href="%(url)s">%(label)s</a></li>' % {
                'label': entry['label'],
                'url': '/dashboard/',
            })
