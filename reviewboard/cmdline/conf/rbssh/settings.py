# A light-weight settings file tailored for rbssh.
#
# This is based off the user's primary Review Board settings, but overrides
# the list of installed apps in order to load in the bare minimum settings
# needed for rbssh.

from reviewboard.settings import *


# Load only enough to load a SiteConfiguration, needed by rbssh.
#
# NOTE: This is not enough for a full Review Board environment. It's important
#       that SSH backends stay minimal enough to operate within this
#       environment.
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'djblets.siteconfig',
]
