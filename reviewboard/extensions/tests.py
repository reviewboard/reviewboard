from django.template import Context, Template
from django.test import TestCase
from djblets.extensions.base import ExtensionManager, RegisteredExtension

from reviewboard.extensions.base import Extension
from reviewboard.extensions.hooks import DashboardHook, DiffViewerActionHook, \
                                         HeaderActionHook, \
                                         HeaderDropdownActionHook, \
                                         NavigationBarHook, \
                                         ReviewRequestActionHook, \
                                         ReviewRequestDropdownActionHook


class DummyExtension(Extension):
    registration = RegisteredExtension()


class HookTests(TestCase):
    """Tests the extension hooks."""
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = DummyExtension(extension_manager=manager)

    def tearDown(self):
        self.extension.shutdown()

    def test_dashboard_hook(self):
        """Testing dashboard sidebar extension hooks"""
        entry = {
            'label': 'My Hook',
            'url': 'foo-url',
        }

        hook = DashboardHook(extension=self.extension, entries=[entry])
        context = Context({
            'dashboard_hook': hook,
        })

        entries = hook.entries
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            "{% load rb_extensions %}"
            "{% for hook in dashboard_hook.entries %}"
            "{{hook.label}} - {{hook.url}}"
            "{% endfor %}")

        self.assertEqual(t.render(context).strip(),
                         '%(label)s - %(url)s' % entry)

    def test_diffviewer_action_hook(self):
        """Testing diff viewer action extension hooks"""
        self._test_action_hook('diffviewer_action_hooks', DiffViewerActionHook)

    def test_review_request_action_hook(self):
        """Testing review request action extension hooks"""
        self._test_action_hook('review_request_action_hooks',
                               ReviewRequestActionHook)

    def test_review_request_dropdown_action_hook(self):
        """Testing review request drop-down action extension hooks"""
        self._test_dropdown_action_hook('review_request_dropdown_action_hooks',
                                        ReviewRequestDropdownActionHook)

    def _test_action_hook(self, template_tag_name, hook_cls):
        action = {
            'label': 'Test Action',
            'id': 'test-action',
            'image': 'test-image',
            'image_width': 42,
            'image_height': 42,
            'url': 'foo-url',
        }

        hook = hook_cls(extension=self.extension, actions=[action])

        context = Context({})
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], action)

        t = Template(
            "{% load rb_extensions %}"
            "{% " + template_tag_name + " %}")

        self.assertEqual(t.render(context).strip(),
                         self._build_action_template(action))

    def _test_dropdown_action_hook(self, template_tag_name, hook_cls):
        action = {
            'id': 'test-menu',
            'label': 'Test Menu',
            'items': [
                {
                    'id': 'test-action',
                    'label': 'Test Action',
                    'url': 'foo-url',
                    'image': 'test-image',
                    'image_width': 42,
                    'image_height': 42
                }
            ]
        }

        hook = hook_cls(extension=self.extension,
                        actions=[action])

        context = Context({})
        entries = hook.get_actions(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], action)

        t = Template(
            "{% load rb_extensions %}"
            "{% " + template_tag_name + " %}")

        content = t.render(context).strip()

        self.assertTrue(('id="%s"' % action['id']) in content)
        self.assertTrue((">%s<img" % action['label']) in content)
        self.assertTrue(self._build_action_template(action['items'][0]) in
                        content)

    def _build_action_template(self, action):
        return '<li><a id="%(id)s" href="%(url)s">' \
              '<img src="%(image)s" width="%(image_width)s" ' \
              'height="%(image_height)s" border="0" alt="" />' \
              '%(label)s</a></li>' % action

    def test_navigation_bar_hooks(self):
        """Testing navigation entry extension hooks"""
        entry = {
            'label': 'Test Nav Entry',
            'url': 'foo-url',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        context = Context({})
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            "{% load rb_extensions %}"
            "{% navigation_bar_hooks %}")

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % entry)

    def test_navigation_bar_hooks_with_url_name(self):
        "Testing navigation entry extension hooks with url names"""
        entry = {
            'label': 'Test Nav Entry',
            'url_name': 'dashboard',
        }

        hook = NavigationBarHook(extension=self.extension, entries=[entry])

        context = Context({})
        entries = hook.get_entries(context)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], entry)

        t = Template(
            "{% load rb_extensions %}"
            "{% navigation_bar_hooks %}")

        self.assertEqual(t.render(context).strip(),
                         '<li><a href="%(url)s">%(label)s</a></li>' % {
                             'label': entry['label'],
                             'url': '/dashboard/',
                         })

    def test_header_hooks(self):
        """Testing header action extension hooks"""
        self._test_action_hook('header_action_hooks', HeaderActionHook)

    def test_header_dropdown_action_hook(self):
        """Testing header drop-down action extension hooks"""
        self._test_dropdown_action_hook('header_dropdown_action_hooks',
                                        HeaderDropdownActionHook)
