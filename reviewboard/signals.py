"""Top-level signals for initialization and settings changes."""

from __future__ import unicode_literals

from django.dispatch import Signal


#: Emitted when the initialization of Review Board is complete.
#:
#: This will emit any time a process or thread has finished initializing,
#: and is ready to serve requests.
initializing = Signal()

#: Emitted when site settings have been loaded.
#:
#: Any time there are new settings saved or loaded, this will emit. Consumers
#: can listen and update their own state based on the new settings.
site_settings_loaded = Signal()
