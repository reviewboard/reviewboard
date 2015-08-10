#
# settings.py -- Settings storage operations for extensions.
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

from django.utils.translation import ugettext as _

from djblets.extensions.signals import settings_saved


class Settings(dict):
    """
    Settings data for an extension. This is a glorified dictionary that
    acts as a proxy for the extension's stored settings in the database.

    Callers must call save() when they want to make the settings persistent.

    If a key is not found in the dictionary, extension.default_settings
    will be checked as well.
    """
    def __init__(self, extension):
        dict.__init__(self)
        self.extension = extension
        self.load()

    def __getitem__(self, key):
        """Retrieve an item from the dictionary.

        This will attempt to return a default value from
        extension.default_settings if the setting has not
        been set.
        """
        if super(Settings, self).__contains__(key):
            return super(Settings, self).__getitem__(key)

        if key in self.extension.default_settings:
            return self.extension.default_settings[key]

        raise KeyError(
            _('The settings key "%(key)s" was not found in extension %(ext)s')
            % {
                'key': key,
                'ext': self.extension.id
            })

    def __contains__(self, key):
        """Indicate if the setting is present.

        If the key is not present in the settings dictionary
        check the default settings as well.
        """
        if super(Settings, self).__contains__(key):
            return True

        return key in self.extension.default_settings

    def get(self, key, default=None):
        """Returns a setting.

        This will return the setting's stored value, or its default value if
        unset.

        If the key isn't a valid setting, the provided default will be
        returned instead.
        """
        # dict.get doesn't call __getitem__ internally, and instead looks up
        # straight from the internal dictionary data. So, we need to handle it
        # ourselves in order to support defaults through __getitem__.
        try:
            return self[key]
        except KeyError:
            return default

    def set(self, key, value):
        """Sets a setting's value.

        This is equivalent to setting the value through standard dictionary
        attribute storage.
        """
        self[key] = value

    def load(self):
        """Loads the settings from the database."""
        try:
            self.update(self.extension.registration.settings)
        except ValueError:
            # The settings in the database are invalid. We'll have to discard
            # it. Note that this should never happen unless the user
            # hand-modifies the entries and breaks something.
            pass

    def save(self):
        """Saves all current settings to the database."""
        registration = self.extension.registration
        registration.settings = dict(self)
        registration.save()

        settings_saved.send(sender=self.extension)

        # Make sure others are aware that the configuration changed.
        self.extension.extension_manager._bump_sync_gen()
