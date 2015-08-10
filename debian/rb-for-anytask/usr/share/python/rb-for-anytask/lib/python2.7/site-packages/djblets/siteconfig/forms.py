#
# forms.py -- Forms for the siteconfig app.
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

from django import forms
from django.utils import six


class SiteSettingsForm(forms.Form):
    """
    A base form for loading/saving settings for a SiteConfiguration. This is
    meant to be subclassed for different settings pages. Any fields defined
    by the form will be loaded/saved automatically.
    """
    def __init__(self, siteconfig, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(SiteSettingsForm, self).__init__(*args, **kwargs)
        self.siteconfig = siteconfig
        self.disabled_fields = {}
        self.disabled_reasons = {}

        self.load()

    def load(self):
        """
        Loads settings from the ```SiteConfiguration''' into this form.
        The default values in the form will be the values in the settings.

        This also handles setting disabled fields based on the
        ```disabled_fields''' and ```disabled_reasons''' variables set on
        this form.
        """
        for field in self.fields:
            value = self.siteconfig.get(field)
            self.fields[field].initial = value

            if field in self.disabled_fields:
                self.fields[field].widget.attrs['disabled'] = 'disabled'

    def save(self):
        """
        Saves settings from the form back into the ```SiteConfiguration'''.
        """
        if not self.errors:
            if hasattr(self, "Meta"):
                save_blacklist = getattr(self.Meta, "save_blacklist", [])
            else:
                save_blacklist = []

            for key, value in six.iteritems(self.cleaned_data):
                if key not in save_blacklist:
                    self.siteconfig.set(key, value)

            self.siteconfig.save()
