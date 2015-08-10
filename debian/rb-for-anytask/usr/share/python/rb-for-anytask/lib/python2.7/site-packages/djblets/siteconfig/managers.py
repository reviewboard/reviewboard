#
# managers.py -- Model managers for siteconfig objects
#
# Copyright (c) 2008-2009  Christian Hammond
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
#

from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.db import models
from django.utils import six


_SITECONFIG_CACHE = {}


class SiteConfigurationManager(models.Manager):
    """
    A Manager that provides a get_current function for retrieving the
    SiteConfiguration for this particular running site.
    """
    def get_current(self):
        """
        Returns the site configuration on the active site.
        """
        from djblets.siteconfig.models import SiteConfiguration
        global _SITECONFIG_CACHE

        # This will handle raising a ImproperlyConfigured if not set up
        # properly.
        site = Site.objects.get_current()

        if site.id not in _SITECONFIG_CACHE:
            _SITECONFIG_CACHE[site.id] = \
                SiteConfiguration.objects.get(site=site)

        return _SITECONFIG_CACHE[site.id]

    def clear_cache(self):
        global _SITECONFIG_CACHE
        _SITECONFIG_CACHE = {}

    def check_expired(self):
        """
        Checks each cached SiteConfiguration to find out if its settings
        have expired. This should be called on each request to ensure that
        the copy of the settings is up-to-date in case another web server
        worker process modifies the settings in the database.
        """
        global _SITECONFIG_CACHE

        for key, siteconfig in six.iteritems(_SITECONFIG_CACHE.copy()):
            if siteconfig.is_expired():
                try:
                    # This is stale. Get rid of it so we can load it next time.
                    del _SITECONFIG_CACHE[key]
                except KeyError:
                    pass
