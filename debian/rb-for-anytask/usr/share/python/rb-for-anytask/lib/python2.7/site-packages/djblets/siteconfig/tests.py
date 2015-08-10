#
# tests.py -- Unit tests for classes in djblets.siteconfig
#
# Copyright (c) 2010  Christian Hammond
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

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils import six

from djblets.siteconfig.django_settings import (apply_django_settings,
                                                cache_settings_map,
                                                mail_settings_map)
from djblets.siteconfig.models import SiteConfiguration
from djblets.testing.testcases import TestCase


class SiteConfigTest(TestCase):
    def setUp(self):
        self.siteconfig = SiteConfiguration(site=Site.objects.get_current())
        self.siteconfig.save()

    def tearDown(self):
        self.siteconfig.delete()
        SiteConfiguration.objects.clear_cache()

    def testMailAuthDeserialize(self):
        """Testing mail authentication settings deserialization"""
        # This is bug 1476. We deserialized the e-mail settings to Unicode
        # strings automatically, but this broke mail sending on some setups.
        # The HMAC library is incompatible with Unicode strings in more recent
        # Python 2.6 versions. Now we deserialize as a string. This test
        # ensures that these settings never break again.

        username = 'myuser'
        password = 'mypass'

        self.assertEqual(type(username), six.text_type)
        self.assertEqual(type(password), six.text_type)

        self.siteconfig.set('mail_host_user', username)
        self.siteconfig.set('mail_host_password', password)
        apply_django_settings(self.siteconfig, mail_settings_map)

        self.assertEqual(settings.EMAIL_HOST_USER, username)
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, password)
        self.assertEqual(type(settings.EMAIL_HOST_USER), bytes)
        self.assertEqual(type(settings.EMAIL_HOST_PASSWORD), bytes)

        # Simulate the failure point in HMAC
        import hmac
        settings.EMAIL_HOST_USER.translate(hmac.trans_5C)
        settings.EMAIL_HOST_PASSWORD.translate(hmac.trans_5C)

    def testSynchronization(self):
        """Testing synchronizing SiteConfigurations through cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def testSynchronizationExpiredCache(self):
        """Testing synchronizing SiteConfigurations with an expired cache"""
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertFalse(siteconfig1.is_expired())

        siteconfig2 = SiteConfiguration.objects.get(site=self.siteconfig.site)
        siteconfig2.set('foobar', 123)

        # Save, and prevent clearing of caches to simulate still having the
        # stale cache around for another thread.
        siteconfig2.save(clear_caches=False)

        cache.delete('%s:siteconfig:%s:generation' %
                     (siteconfig2.site.domain, siteconfig2.id))

        self.assertTrue(siteconfig1.is_expired())

        SiteConfiguration.objects.check_expired()

        # See if we fetch the same one again
        siteconfig1 = SiteConfiguration.objects.get_current()
        self.assertEqual(siteconfig1.get('foobar'), 123)

    def test_cache_backend(self):
        """Testing cache backend setting with CACHES['default']"""
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'foo',
            },
            'staticfiles': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'staticfiles-cache',
            }
        }

        self.siteconfig.set('cache_backend', 'memcached://localhost:12345/')
        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')

    def test_cache_backend_with_caches(self):
        """Testing cache backend setting with siteconfig-stored CACHES"""
        settings.CACHES['staticfiles'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staticfiles-cache',
        }

        self.siteconfig.set('cache_backend', {
            'default': {
                'BACKEND':
                    'django.core.cache.backends.memcached.MemcachedCache',
                'LOCATION': 'localhost:12345',
            },
        })

        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')

    def test_cache_backend_with_caches_legacy_memcached(self):
        """Testing cache backend setting with siteconfig-stored CACHES and
        legacy memcached.CacheClass
        """
        settings.CACHES['staticfiles'] = {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'staticfiles-cache',
        }

        self.siteconfig.set('cache_backend', {
            'default': {
                'BACKEND':
                    'django.core.cache.backends.memcached.CacheClass',
                'LOCATION': 'localhost:12345',
            },
        })

        apply_django_settings(self.siteconfig, cache_settings_map)

        self.assertTrue('staticfiles' in settings.CACHES)
        self.assertTrue('default' in settings.CACHES)
        self.assertTrue('forwarded_backend' in settings.CACHES)

        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'djblets.cache.forwarding_backend.ForwardingCacheBackend')
        self.assertEqual(settings.CACHES['default']['LOCATION'],
                         'forwarded_backend')

        self.assertEqual(settings.CACHES['forwarded_backend']['BACKEND'],
                         'django.core.cache.backends.memcached.MemcachedCache')
        self.assertEqual(settings.CACHES['forwarded_backend']['LOCATION'],
                         'localhost:12345')
