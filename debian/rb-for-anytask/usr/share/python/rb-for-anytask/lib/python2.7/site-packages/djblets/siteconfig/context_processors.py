#
# context_processors.py -- Context processors for the siteconfig app.
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

import logging

from django.conf import settings

from djblets.siteconfig.models import SiteConfiguration


def siteconfig(request):
    """Provides variables for accessing site configuration data.

    This will provide templates with a 'siteconfig' variable, representing
    the SiteConfiguration for the installation, and a 'siteconfig_settings',
    representing all settings on the SiteConfiguration.

    siteconfig_settings is preferred over accessing siteconfig.settings, as
    it will properly handle returning default values.
    """
    try:
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig_settings = siteconfig.settings_wrapper
    except Exception, e:
        logging.error('Unable to load SiteConfiguration: %s', e, exc_info=1)

        siteconfig = None
        siteconfig_settings = None

    return {
        'siteconfig': siteconfig,
        'siteconfig_settings': siteconfig_settings,
    }


def settings_vars(request):
    return {'settings': settings}
