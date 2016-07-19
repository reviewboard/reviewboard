from __future__ import unicode_literals

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.avatars import avatar_services


class AvatarServicesTestMixin(object):
    """A testcase mixin for resetting the state of avatar services.

    The avatar service registry class will change the state of the
    :py:attr:`SiteConfiguration.settings
    <djblets.siteconfig.models.SiteConfiguration>` object, which will not be
    automatically undone when the test-case finishes. Instead, we cache the
    site configuration settings prior to running any test cases and reset the
    site configuration settings to these cached settings after each test.

    This mixin should be used in any test case class that deals with avatar
    services.
    """

    @classmethod
    def setUpClass(cls):
        """Cache the SiteConfiguration settings object."""
        super(AvatarServicesTestMixin, cls).setUpClass()

        siteconfig = SiteConfiguration.objects.get_current()
        cls._original_settings = siteconfig.settings.copy()

    def tearDown(self):
        """Restore the SiteConfiguration settings object."""
        super(AvatarServicesTestMixin, self).tearDown()

        avatar_services.reset()
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.settings = self._original_settings.copy()
        siteconfig.save(update_fields=('settings',))
