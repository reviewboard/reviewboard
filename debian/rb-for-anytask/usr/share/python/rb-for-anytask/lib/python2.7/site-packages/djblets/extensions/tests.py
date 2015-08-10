#
# tests.py -- Unit tests for extensions.
#
# Copyright (c) 2010-2013  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
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

import logging
import os
import threading
import time

from django import forms
from django.conf import settings
from django.conf.urls import include, patterns
from django.core.exceptions import ImproperlyConfigured
from django.dispatch import Signal
from django.template import Context, Template
from django.utils import six
from kgb import SpyAgency
from mock import Mock

from djblets.datagrid.grids import Column, DataGrid
from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.forms import SettingsForm
from djblets.extensions.hooks import (DataGridColumnsHook, ExtensionHook,
                                      ExtensionHookPoint, SignalHook,
                                      TemplateHook, URLHook)
from djblets.extensions.manager import (_extension_managers, ExtensionManager,
                                        SettingListWrapper)
from djblets.extensions.settings import Settings
from djblets.extensions.signals import settings_saved
from djblets.extensions.views import configure_extension
from djblets.testing.testcases import TestCase


class SettingsTest(TestCase):
    def setUp(self):
        # Build up a mocked extension
        self.extension = Mock()
        self.extension.registration = Mock()
        self.test_dict = {
            'test_key1': 'test_value1',
            'test_key2': 'test_value2',
        }
        self.extension.registration.settings = self.test_dict
        self.settings = Settings(self.extension)

    def test_constructor(self):
        """Testing the Extension's Settings constructor"""
        # Build the Settings objects
        self.assertEqual(self.extension, self.settings.extension)

        # Ensure that the registration settings dict gets
        # added to this Settings
        self.assertEqual(self.test_dict['test_key1'],
                         self.settings['test_key1'])

    def test_load_updates_dict(self):
        """Testing that Settings.load correctly updates core dict"""
        new_dict = {
            'test_new_key': 'test_new_value',
            'test_key1': 'new_value',
        }
        self.extension.registration.settings = new_dict
        self.settings.load()

        # Should have added test_new_key, and modified test_key1
        self.assertEqual(new_dict['test_new_key'],
                         self.settings['test_new_key'])
        self.assertEqual(new_dict['test_key1'], self.settings['test_key1'])

        # Should have left test_key2 alone
        self.assertEqual(self.test_dict['test_key2'],
                         self.settings['test_key2'])

    def test_load_silently_discards(self):
        """Testing that Settings.load silently ignores invalid settings"""
        some_string = 'This is a string'
        self.extension.registration.settings = some_string

        try:
            self.settings.load()
        except Exception:
            self.fail("Shouldn't have raised an exception")

    def test_save_updates_database(self):
        """Testing that Settings.save will correctly update registration"""
        registration = self.extension.registration
        self.settings['test_new_key'] = 'Test new value'
        generated_dict = dict(self.settings)
        self.settings.save()

        self.assertTrue(registration.save.called)
        self.assertEqual(generated_dict, registration.settings)

    def test_save_emits_settings_saved_signal(self):
        """Testing that Settings.save emits the settings_saved signal"""
        saw = {}

        def on_settings_saved(*args, **kwargs):
            saw['signal'] = True

        settings_saved.connect(on_settings_saved, sender=self.extension)

        self.settings['test_new_key'] = 'Test new value'
        self.settings.save()

        self.assertIn('signal', saw)


class TestExtensionWithRegistration(Extension):
    """Dummy extension for testing."""
    id = 'TestExtensionWithRegistration'
    registration = Mock()
    registration.settings = dict()


@six.add_metaclass(ExtensionHookPoint)
class DummyHook(ExtensionHook):
    def __init__(self, extension):
        super(DummyHook, self).__init__(extension)
        self.foo = [1]

    def shutdown(self):
        super(DummyHook, self).shutdown()
        self.foo.pop()


class ExtensionTest(SpyAgency, TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)

        for index in range(0, 5):
            hook = DummyHook(self.extension)
            self.spy_on(hook.shutdown)
            self.extension.hooks.add(hook)

    def test_extension_constructor(self):
        """Testing Extension construction"""
        self.assertEqual(type(self.extension.settings), Settings)
        self.assertEqual(self.extension, self.extension.settings.extension)

    def test_shutdown(self):
        """Testing Extension.shutdown"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)

    def test_shutdown_twice(self):
        """Testing Extension.shutdown when called twice"""
        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertTrue(hook.shutdown.called)
            hook.shutdown.reset_calls()

        self.extension.shutdown()

        for hook in self.extension.hooks:
            self.assertFalse(hook.shutdown.called)

    def test_get_admin_urlconf(self):
        """Testing Extension with admin URLConfs"""
        did_fail = False
        old_module = self.extension.__class__.__module__
        self.extension.__class__.__module__ = 'djblets.extensions.test.test'

        try:
            self.extension._get_admin_urlconf()
        except ImproperlyConfigured:
            did_fail = True
        finally:
            self.extension.__class__.__module__ = old_module

            if did_fail:
                self.fail("Should have loaded admin_urls.py")


class ExtensionInfoTest(TestCase):
    def test_metadata_from_package(self):
        """Testing ExtensionInfo metadata from package"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_extension_id = '%s:DummyExtension' % test_module_name
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.MEDIA_ROOT, 'ext',
                                        test_project_name)
        test_static_path = os.path.join(settings.STATIC_ROOT, 'ext',
                                        test_extension_id)

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in six.iteritems(test_metadata)
            ])

        entrypoint.dist.project_name = test_project_name
        entrypoint.dist.version = test_version

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.id = test_extension_id
        ext_class.metadata = None
        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.installed_htdocs_path,
                         test_htdocs_path)
        self.assertEqual(extension_info.installed_static_path,
                         test_static_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)

    def test_custom_metadata(self):
        """Testing ExtensionInfo metadata from Extension.metadata"""
        entrypoint = Mock()
        entrypoint.dist = Mock()

        test_author = 'Test author lorem ipsum'
        test_description = 'Test description lorem ipsum'
        test_email = 'Test author@email.com'
        test_home_page = 'http://www.example.com'
        test_license = 'Test License MIT GPL Apache Drivers'
        test_module_name = 'testextension.dummy.dummy'
        test_module_to_app = 'testextension.dummy'
        test_project_name = 'TestProjectName'
        test_summary = 'Test summary lorem ipsum'
        test_version = '1.0'

        test_htdocs_path = os.path.join(settings.MEDIA_ROOT, 'ext',
                                        'Dummy')

        test_metadata = {
            'Name': test_project_name,
            'Version': test_version,
            'Summary': test_summary,
            'Description': test_description,
            'Author': test_author,
            'Author-email': test_email,
            'License': test_license,
            'Home-page': test_home_page,
        }

        entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, 'Dummy')
                for key, value in six.iteritems(test_metadata)
            ])

        entrypoint.dist.project_name = 'Dummy'
        entrypoint.dist.version = 'Dummy'

        ext_class = Mock()
        ext_class.__module__ = test_module_name
        ext_class.metadata = test_metadata

        extension_info = ExtensionInfo(entrypoint, ext_class)

        self.assertEqual(extension_info.app_name, test_module_to_app)
        self.assertEqual(extension_info.author, test_author)
        self.assertEqual(extension_info.author_email, test_email)
        self.assertEqual(extension_info.description, test_description)
        self.assertFalse(extension_info.enabled)
        self.assertEqual(extension_info.installed_htdocs_path,
                         test_htdocs_path)
        self.assertFalse(extension_info.installed)
        self.assertEqual(extension_info.license, test_license)
        self.assertEqual(extension_info.metadata, test_metadata)
        self.assertEqual(extension_info.name, test_project_name)
        self.assertEqual(extension_info.summary, test_summary)
        self.assertEqual(extension_info.url, test_home_page)
        self.assertEqual(extension_info.version, test_version)


@six.add_metaclass(ExtensionHookPoint)
class TestExtensionHook(ExtensionHook):
    """A dummy ExtensionHook to test with"""


class ExtensionHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook = TestExtensionHook(self.extension)

    def test_registration(self):
        """Testing ExtensionHook registration"""
        self.assertEqual(self.extension, self.extension_hook.extension)
        self.assertTrue(self.extension_hook in self.extension.hooks)
        self.assertTrue(self.extension_hook in
                        self.extension_hook.__class__.hooks)

    def test_shutdown(self):
        """Testing ExtensionHook.shutdown"""
        self.extension_hook.shutdown()
        self.assertTrue(self.extension_hook not in
                        self.extension_hook.__class__.hooks)


class ExtensionHookPointTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.extension_hook_class = TestExtensionHook
        self.dummy_hook = Mock()
        self.extension_hook_class.add_hook(self.dummy_hook)

    def test_extension_hook_class_gets_hooks(self):
        """Testing ExtensionHookPoint.hooks"""
        self.assertTrue(hasattr(self.extension_hook_class, "hooks"))

    def test_add_hook(self):
        """Testing ExtensionHookPoint.add_hook"""
        self.assertTrue(self.dummy_hook in self.extension_hook_class.hooks)

    def test_remove_hook(self):
        """Testing ExtensionHookPoint.remove_hook"""
        self.extension_hook_class.remove_hook(self.dummy_hook)
        self.assertTrue(self.dummy_hook not in self.extension_hook_class.hooks)


class ExtensionManagerTest(SpyAgency, TestCase):
    def setUp(self):
        class TestExtension(Extension):
            """An empty, dummy extension for testing"""
            css_bundles = {
                'default': {
                    'source_filenames': ['test.css'],
                }
            }

            js_bundles = {
                'default': {
                    'source_filenames': ['test.js'],
                }
            }

        self.key = 'test_key'
        self.extension_class = TestExtension
        self.manager = ExtensionManager(self.key)
        self.fake_entrypoint = Mock()
        self.fake_entrypoint.load = Mock(return_value=self.extension_class)
        self.fake_entrypoint.dist = Mock()

        self.test_author = 'Test author lorem ipsum'
        self.test_description = 'Test description lorem ipsum'
        self.test_email = 'Test author@email.com'
        self.test_home_page = 'http://www.example.com'
        self.test_license = 'Test License MIT GPL Apache Drivers'
        self.test_module_name = 'testextension.dummy.dummy'
        self.test_module_to_app = 'testextension.dummy'
        self.test_project_name = 'TestProjectName'
        self.test_summary = 'Test summary lorem ipsum'
        self.test_version = '1.0'

        self.test_metadata = {
            'Name': self.test_project_name,
            'Version': self.test_version,
            'Summary': self.test_summary,
            'Description': self.test_description,
            'Author': self.test_author,
            'Author-email': self.test_email,
            'License': self.test_license,
            'Home-page': self.test_home_page,
        }

        self.fake_entrypoint.dist.get_metadata_lines = Mock(
            return_value=[
                "%s: %s" % (key, value)
                for key, value in six.iteritems(self.test_metadata)
            ])

        self.fake_entrypoint.dist.project_name = self.test_project_name
        self.fake_entrypoint.dist.version = self.test_version

        self.manager._entrypoint_iterator = Mock(
            return_value=[self.fake_entrypoint]
        )
        self.manager.load()

    def tearDown(self):
        self.manager.clear_sync_cache()

    def test_added_to_extension_managers(self):
        """Testing ExtensionManager registration"""
        self.assertTrue(self.manager in _extension_managers)

    def test_get_enabled_extensions_returns_empty(self):
        """Testing ExtensionManager.get_enabled_extensions with no
        extensions
        """
        self.assertEqual(len(self.manager.get_enabled_extensions()), 0)

    def test_load(self):
        """Testing ExtensionManager.get_installed_extensions with loaded
        extensions
        """
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.assertTrue(self.extension_class in
                        self.manager.get_installed_extensions())
        self.assertTrue(hasattr(self.extension_class, 'info'))
        self.assertEqual(self.extension_class.info.name,
                         self.test_project_name)
        self.assertTrue(hasattr(self.extension_class, 'registration'))
        self.assertEqual(self.extension_class.registration.name,
                         self.test_project_name)

    def test_load_full_reload_hooks(self):
        """Testing ExtensionManager.load with full_reload=True"""
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        URLHook(extension, ())
        self.assertEqual(len(URLHook.hooks), 1)
        self.assertEqual(URLHook.hooks[0].extension, extension)

        self.manager.load(full_reload=True)

        self.assertEqual(len(URLHook.hooks), 0)

    def test_load_concurrent_threads(self):
        """Testing ExtensionManager.load with concurrent threads"""
        # There are a number of things that could go wrong both during
        # uninitialization and during initialization of extensions, if
        # two threads attempt to reload at the same time and locking isn't
        # properly implemented.
        #
        # Extension uninit could be called twice, resulting in one thread
        # attempting to access state that's already been destroyed. We
        # could end up hitting:
        #
        #     "Extension's installed app <app> is missing a ref count."
        #     "'<Extension>' object has no attribute 'info'."
        #
        # (Without locking, we end up hitting the latter in this test.)
        #
        # If an extension is being initialized twice simultaneously, then
        # it can hit other errors. An easy one to hit is this assertion:
        #
        #     assert extension_id not in self._extension_instances
        #
        # With proper locking, these issues don't come up. That's what
        # this test case is attempting to check for.

        # Enable one extension. This extension's state will get a bit messed
        # up if the thread locking fails. We only need one to trigger this.
        self.assertEqual(len(self.manager.get_installed_extensions()), 1)
        self.manager.enable_extension(self.extension_class.id)

        self.spy_on(self.manager._load_extensions)
        self._spy_sleep_and_call(self.manager._init_extension)
        self._spy_sleep_and_call(self.manager._uninit_extension)

        self._run_thread_test(lambda: self.manager.load(full_reload=True))

        self.assertEqual(len(self.manager._load_extensions.calls), 2)
        self.assertEqual(len(self.manager._uninit_extension.calls), 2)
        self.assertEqual(len(self.manager._init_extension.calls), 2)
        self.assertEqual(self.exceptions, [])

    def test_enable_registers_static_bundles(self):
        """Testing ExtensionManager registers static bundles when enabling
        extension
        """
        settings.PIPELINE_CSS = {}
        settings.PIPELINE_JS = {}

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 1)
        self.assertEqual(len(settings.PIPELINE_JS), 1)

        key = '%s-default' % extension.id
        self.assertIn(key, settings.PIPELINE_CSS)
        self.assertIn(key, settings.PIPELINE_JS)

        css_bundle = settings.PIPELINE_CSS[key]
        js_bundle = settings.PIPELINE_JS[key]

        self.assertIn('source_filenames', css_bundle)
        self.assertEqual(css_bundle['source_filenames'],
                         ['ext/%s/test.css' % extension.id])

        self.assertIn('output_filename', css_bundle)
        self.assertEqual(css_bundle['output_filename'],
                         'ext/%s/css/default.min.css' % extension.id)

        self.assertIn('source_filenames', js_bundle)
        self.assertEqual(js_bundle['source_filenames'],
                         ['ext/%s/test.js' % extension.id])

        self.assertIn('output_filename', js_bundle)
        self.assertEqual(js_bundle['output_filename'],
                         'ext/%s/js/default.min.js' % extension.id)

    def test_install_extension_media_with_stale_version_key(self):
        """Testing ExtensionManager installing media for newly installed
        extension with existing stale version key
        """
        extension = self.extension_class(extension_manager=self.manager)
        version_key = ExtensionManager.VERSION_SETTINGS_KEY

        self.assertFalse(extension.registration.installed)

        # Add a bad version key, perhaps copy/pasted by hand from an admin.
        # We'll set it to the current version.
        extension.settings.set(version_key, extension.info.version)
        extension.settings.save()

        # Enable the extension. It shouldn't blow up.
        extension = self.manager.enable_extension(self.extension_class.id)
        self.assertTrue(extension.registration.installed)
        self.assertIsNotNone(extension.settings.get(version_key))

    def test_install_media_concurrent_threads(self):
        """Testing ExtensionManager updating media for existing
        extension with concurrent threads
        """
        version_key = ExtensionManager.VERSION_SETTINGS_KEY

        extension = self.extension_class(extension_manager=self.manager)
        extension.registration.installed = True
        extension.registration.enabled = True
        extension.registration.save()
        extension.__class__.instance = extension

        extension.settings.set(version_key, '0.5')
        extension.settings.save()

        self.assertEqual(len(self.manager.get_installed_extensions()), 1)

        self.spy_on(self.manager._install_extension_media)
        self.spy_on(self.manager._install_extension_media_internal,
                    call_original=False)

        self._run_thread_test(
            lambda: self.manager._install_extension_media(extension.__class__))

        self.assertEqual(
            len(self.manager._install_extension_media.calls), 2)
        self.assertEqual(
            len(self.manager._install_extension_media_internal.calls), 1)
        self.assertEqual(self.exceptions, [])

    def test_disable_unregisters_static_bundles(self):
        """Testing ExtensionManager unregisters static bundles when disabling
        extension
        """
        settings.PIPELINE_CSS = {}
        settings.PIPELINE_JS = {}

        extension = self.extension_class(extension_manager=self.manager)
        extension = self.manager.enable_extension(self.extension_class.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 1)
        self.assertEqual(len(settings.PIPELINE_JS), 1)

        self.manager.disable_extension(extension.id)

        self.assertEqual(len(settings.PIPELINE_CSS), 0)
        self.assertEqual(len(settings.PIPELINE_JS), 0)

    def test_extension_list_sync(self):
        """Testing ExtensionManager extension list synchronization
        cross-process
        """
        key = 'extension-list-sync'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()
        manager2.load()

        self.assertEqual(len(manager1.get_installed_extensions()), 1)
        self.assertEqual(len(manager2.get_installed_extensions()), 1)
        self.assertEqual(len(manager1.get_enabled_extensions()), 0)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        manager1.enable_extension(self.extension_class.id)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 0)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        self.assertEqual(len(manager1.get_enabled_extensions()), 1)
        self.assertEqual(len(manager2.get_enabled_extensions()), 1)
        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

    def test_extension_settings_sync(self):
        """Testing ExtensionManager extension settings synchronization
        cross-process
        """
        key = 'extension-settings-sync'
        setting_key = 'foo'
        setting_val = 'abc123'

        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()

        extension1 = manager1.enable_extension(self.extension_class.id)

        manager2.load()

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())

        extension2 = manager2.get_enabled_extension(self.extension_class.id)
        self.assertNotEqual(extension2, None)

        self.assertFalse(setting_key in extension1.settings)
        self.assertFalse(setting_key in extension2.settings)
        extension1.settings[setting_key] = setting_val
        extension1.settings.save()

        self.assertFalse(setting_key in extension2.settings)

        self.assertFalse(manager1.is_expired())
        self.assertTrue(manager2.is_expired())

        manager2.load(full_reload=True)
        extension2 = manager2.get_enabled_extension(self.extension_class.id)

        self.assertFalse(manager1.is_expired())
        self.assertFalse(manager2.is_expired())
        self.assertTrue(setting_key in extension1.settings)
        self.assertTrue(setting_key in extension2.settings)
        self.assertEqual(extension1.settings[setting_key], setting_val)
        self.assertEqual(extension2.settings[setting_key], setting_val)

    def test_load_blocks_sync_gen(self):
        """Testing ExtensionManager.load blocks bumping sync generation
        number
        """
        key = 'check-expired-test'
        manager1 = ExtensionManager(key)
        manager2 = ExtensionManager(key)

        for manager in (manager1, manager2):
            manager._entrypoint_iterator = Mock(
                return_value=[self.fake_entrypoint]
            )

        manager1.load()
        manager1.enable_extension(self.extension_class.id)
        manager2.load()

        self.assertEqual(manager1._last_sync_gen, manager2._last_sync_gen)

        # Trigger a save whenever the extension initializes.
        self.extension_class.initialize = lambda ext: ext.settings.save()

        # Bump the generation number.
        extension = manager2.get_enabled_extension(self.extension_class.id)
        extension.settings.save()
        self.assertNotEqual(manager1._last_sync_gen, manager2._last_sync_gen)

        # Loading now should retain the new sync generation number, instead
        # of bumping it.
        manager1.load(full_reload=True)
        self.assertEqual(manager1._last_sync_gen, manager2._last_sync_gen)

    def _run_thread_test(self, main_func):
        def _thread_main(main_connection, main_func, sleep_time):
            # Insert the connection from the main thread, so that we can
            # perform lookups. We never write.
            from django.db import connections

            connections['default'] = main_connection

            time.sleep(sleep_time)
            main_func()

        # Store the main connection. We're going to let the threads share it.
        # This trick courtesy of the Django unit tests
        # (django/tests/backends/tests.py).
        from django.db import connections

        main_connection = connections['default']
        main_connection.allow_thread_sharing = True

        self.exceptions = []

        t1 = threading.Thread(target=_thread_main,
                              args=[main_connection, main_func, 0.2])
        t2 = threading.Thread(target=_thread_main,
                              args=[main_connection, main_func, 0.1])
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def _sleep_and_call(self, manager, orig_func, *args, **kwargs):
        # This works well enough to throw a monkey wrench into things.
        # One thread will be slightly ahead of the other.
        time.sleep(0.2)

        try:
            orig_func(*args, **kwargs)
        except Exception as e:
            logging.error('%s\n', e, exc_info=1)
            self.exceptions.append(e)

    def _spy_sleep_and_call(self, func):
        def _call(manager, *args, **kwargs):
            self._sleep_and_call(manager, orig_func, *args, **kwargs)

        orig_func = func

        self.spy_on(func, call_fake=_call)


class SettingListWrapperTests(TestCase):
    """Unit tests for djblets.extensions.manager.SettingListWrapper."""
    def test_loading_from_setting(self):
        """Testing SettingListWrapper constructor loading from settings"""
        settings.TEST_SETTING_LIST = ['item1', 'item2']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        self.assertEqual(wrapper.ref_counts.get('item2'), 1)

    def test_add_with_new_item(self):
        """Testing SettingListWrapper.add with new item"""
        settings.TEST_SETTING_LIST = []
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)

    def test_add_with_existing_item(self):
        """Testing SettingListWrapper.add with existing item"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 2)

    def test_remove_with_ref_count_1(self):
        """Testing SettingListWrapper.remove with ref_count == 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')

        self.assertEqual(wrapper.ref_counts.get('item1'), 1)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, [])
        self.assertFalse('item1' in wrapper.ref_counts)

    def test_remove_with_ref_count_gt_1(self):
        """Testing SettingListWrapper.remove with ref_count > 1"""
        settings.TEST_SETTING_LIST = ['item1']
        wrapper = SettingListWrapper('TEST_SETTING_LIST', 'test setting list')
        wrapper.add('item1')

        self.assertEqual(wrapper.ref_counts.get('item1'), 2)
        wrapper.remove('item1')

        self.assertEqual(settings.TEST_SETTING_LIST, ['item1'])
        self.assertEqual(wrapper.ref_counts.get('item1'), 1)


class SignalHookTests(SpyAgency, TestCase):
    """Unit tests for djblets.extensions.hooks.SignalHook."""
    def setUp(self):
        manager = ExtensionManager('')
        self.test_extension = \
            TestExtensionWithRegistration(extension_manager=manager)

        self.signal = Signal()
        self.spy_on(self._on_signal_fired)
        self.spy_on(self._on_signal_exception)

    def test_initialize(self):
        """Testing SignalHook initialization connects to signal"""
        SignalHook(self.test_extension, self.signal, self._on_signal_fired)

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 1)

    def test_shutdown(self):
        """Testing SignalHook.shutdown disconnects from signal"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired)
        hook.shutdown()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_shutdown_with_sender(self):
        """Testing SignalHook.shutdown disconnects when a sender was set"""
        hook = SignalHook(self.test_extension, self.signal,
                          self._on_signal_fired, sender=self)
        hook.shutdown()

        self.assertEqual(len(self._on_signal_fired.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_fired.calls), 0)

    def test_forwards_args(self):
        """Testing SignalHook forwards arguments to callback"""
        seen_kwargs = {}

        def callback(**kwargs):
            seen_kwargs.update(kwargs)

        SignalHook(self.test_extension, self.signal, callback)
        self.signal.send(sender=self, foo=1, bar=2)

        self.assertTrue('foo', seen_kwargs)
        self.assertEqual(seen_kwargs['foo'], 1)
        self.assertTrue('bar', seen_kwargs)
        self.assertEqual(seen_kwargs['bar'], 2)

    def test_sandbox_errors_true(self):
        """Testing SignalHook with sandbox_errors set to True logs errors"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=True)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.signal.send(self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def test_sandbox_errors_false(self):
        """Testing SignalHook with sandbox_errors set to False"""
        SignalHook(self.test_extension, self.signal, self._on_signal_exception,
                   sandbox_errors=False)

        self.assertEqual(len(self._on_signal_exception.calls), 0)
        self.assertRaises(Exception, self.signal.send, self)
        self.assertEqual(len(self._on_signal_exception.calls), 1)

    def _on_signal_fired(self, *args, **kwargs):
        pass

    def _on_signal_exception(self, *args, **kwargs):
        raise Exception


class URLHookTest(TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.test_extension = \
            TestExtensionWithRegistration(extension_manager=manager)
        self.patterns = patterns(
            '',
            (r'^url_hook_test/', include('djblets.extensions.test.urls')))
        self.url_hook = URLHook(self.test_extension, self.patterns)

    def test_url_registration(self):
        """Testing URLHook URL registration"""
        self.assertTrue(
            set(self.patterns)
            .issubset(set(self.url_hook.dynamic_urls.url_patterns)))
        # And the URLHook should be added to the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)

    def test_shutdown_removes_urls(self):
        """Testing URLHook.shutdown"""
        # On shutdown, a URLHook's patterns should no longer be in its
        # parent URL resolver's pattern collection.
        self.url_hook.shutdown()
        self.assertFalse(
            set(self.patterns).issubset(
                set(self.url_hook.dynamic_urls.url_patterns)))

        # But the URLHook should still be in the extension's list of hooks
        self.assertTrue(self.url_hook in self.test_extension.hooks)


class TemplateHookTest(SpyAgency, TestCase):
    def setUp(self):
        manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=manager)

        self.hook_no_applies_name = "template-hook-no-applies-name"
        self.template_hook_no_applies = TemplateHook(
            self.extension,
            self.hook_no_applies_name,
            "test_module/some_template.html",
            [])

        self.hook_with_applies_name = "template-hook-with-applies-name"
        self.template_hook_with_applies = TemplateHook(
            self.extension,
            self.hook_with_applies_name,
            "test_module/some_template.html",
            [
                'test-url-name',
                'url_2',
                'url_3',
            ]
        )

        self.request = Mock()
        self.request._djblets_extensions_kwargs = {}
        self.request.path_info = '/'
        self.request.resolver_match = Mock()
        self.request.resolver_match.url_name = 'root'

    def test_hook_added_to_class_by_name(self):
        """Testing TemplateHook registration"""
        self.assertTrue(self.template_hook_with_applies in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should also be added to the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_hook_shutdown(self):
        """Testing TemplateHook shutdown"""
        self.template_hook_with_applies.shutdown()
        self.assertTrue(self.template_hook_with_applies not in
                        self.template_hook_with_applies.__class__
                            ._by_name[self.hook_with_applies_name])

        # The TemplateHook should still be in the Extension's collection
        # of hooks.
        self.assertTrue(self.template_hook_with_applies in
                        self.extension.hooks)

    def test_applies_to_default(self):
        """Testing TemplateHook.applies_to defaults to everything"""
        self.assertTrue(self.template_hook_no_applies.applies_to(self.request))
        self.assertTrue(self.template_hook_no_applies.applies_to(None))

    def test_applies_to(self):
        """Testing TemplateHook.applies_to customization"""
        self.assertFalse(
            self.template_hook_with_applies.applies_to(self.request))

        self.request.resolver_match.url_name = 'test-url-name'
        self.assertTrue(
            self.template_hook_with_applies.applies_to(self.request))

    def test_context_doesnt_leak(self):
        """Testing TemplateHook's context won't leak state"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                context['leaky'] = True

                return ''

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        self.assertNotIn('leaky', context)

    def test_render_to_string_sandbox(self):
        """Testing TemplateHook sandboxing"""
        class MyTemplateHook(TemplateHook):
            def render_to_string(self, request, context):
                raise Exception('Oh noes')

        MyTemplateHook(self.extension, 'test')
        context = Context({})
        context['request'] = None

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        t.render(context).strip()

        # Didn't crash. We're good.

    def test_applies_to_sandbox(self):
        """Testing TemplateHook for applies_to"""
        class MyTemplateHook(TemplateHook):
            def applies_to(self, request):
                raise Exception

        hook = MyTemplateHook(extension=self.extension, name='test')
        context = Context({})
        context['request'] = self.request

        self.spy_on(hook.applies_to)

        t = Template(
            '{% load djblets_extensions %}'
            '{% template_hook_point "test" %}')
        string = t.render(context).strip()

        self.assertEqual(string, '')

        self.assertTrue(hook.applies_to.called)


class DataGridColumnsHookTest(SpyAgency, TestCase):
    def setUp(self):
        self.manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=self.manager)

    def test_add_column(self):
        """Testing DataGridColumnsHook registers column"""
        self.spy_on(DataGrid.add_column)

        DataGridColumnsHook(extension=self.extension,
                            datagrid_cls=DataGrid,
                            columns=[Column(id='sandbox')])

        self.assertTrue(DataGrid.add_column.called)

    def test_remove_column(self):
        """Testing DataGridColumnsHook unregisters column"""
        self.spy_on(DataGrid.remove_column)

        hook = DataGridColumnsHook(extension=self.extension,
                                   datagrid_cls=DataGrid,
                                   columns=[Column(id='sandbox2')])

        hook.shutdown()

        self.assertTrue(DataGrid.remove_column.called)


class ViewTests(SpyAgency, TestCase):
    """Unit tests for djblets.extensions.views."""
    def setUp(self):
        self.manager = ExtensionManager('')
        self.extension = \
            TestExtensionWithRegistration(extension_manager=self.manager)

    def test_configure_extension_saving(self):
        """Testing configure_extension with saving settings"""
        class TestSettingsForm(SettingsForm):
            mykey = forms.CharField(max_length=100)

        self.extension.is_configurable = True
        self.spy_on(self.manager.get_enabled_extension,
                    call_fake=lambda *args: self.extension)

        request = Mock()
        request.path = '/config'
        request.method = 'POST'
        request.META = {
            'CSRF_COOKIE': 'abc123',
        }
        request.POST = {
            'mykey': 'myvalue',
        }
        request.FILES = {}

        configure_extension(request, TestExtensionWithRegistration,
                            TestSettingsForm, self.manager)

        self.assertEqual(self.extension.settings.get('mykey'), 'myvalue')


# A dummy function that acts as a View method
test_view_method = Mock()
