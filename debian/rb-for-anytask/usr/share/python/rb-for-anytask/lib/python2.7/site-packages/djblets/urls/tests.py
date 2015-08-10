from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import include, patterns, url
from django.core.urlresolvers import NoReverseMatch, reverse

from djblets.testing.testcases import TestCase
from djblets.urls.resolvers import DynamicURLResolver


class URLResolverTests(TestCase):
    def setUp(self):
        self._old_root_urlconf = settings.ROOT_URLCONF

    def tearDown(self):
        settings.ROOT_URLCONF = self._old_root_urlconf

    def test_dynamic_url_resolver(self):
        """Testing DynamicURLResolver"""
        self.dynamic_urls = DynamicURLResolver()

        settings.ROOT_URLCONF = patterns(
            '',

            url(r'^root/', include(patterns('', self.dynamic_urls))),
            url(r'^foo/', self._dummy_view, name='foo'),
        )

        new_patterns = patterns(
            '',

            url(r'^bar/$', self._dummy_view, name='bar'),
            url(r'^baz/$', self._dummy_view, name='baz'),
        )

        # The new patterns shouldn't reverse, just the original "foo".
        reverse('foo')
        self.assertRaises(NoReverseMatch, reverse, 'bar')
        self.assertRaises(NoReverseMatch, reverse, 'baz')

        # Add the new patterns. Now reversing should work.
        self.dynamic_urls.add_patterns(new_patterns)

        reverse('foo')
        reverse('bar')
        reverse('baz')

        # Get rid of the patterns again. We should be back in the original
        # state.
        self.dynamic_urls.remove_patterns(new_patterns)

        reverse('foo')
        self.assertRaises(NoReverseMatch, reverse, 'bar')
        self.assertRaises(NoReverseMatch, reverse, 'baz')

    def _dummy_view(self):
        pass
