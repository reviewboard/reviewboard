"""Unit tests for reviewboard.extensions.hooks.NavigationBarHook."""

from django.contrib.auth.models import User
from django.template import Context, Template

from reviewboard.extensions.hooks import NavigationBarHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase


class NavigationBarHookTests(BaseExtensionHookTestCase):
    """Tests the navigation bar hooks."""

    def test_get_entries(self):
        """Testing NavigationBarHook.get_entries"""
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

    def test_get_entries_with_url_name(self):
        """Testing NavigationbarHook.get_entries with URL names"""
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

    def test_is_enabled_for_true(self):
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

    def test_is_enabled_for_false(self):
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
