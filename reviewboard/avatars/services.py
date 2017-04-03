"""Review Board-specific specializations of avatar services."""

from __future__ import unicode_literals

from django.utils import six
from django.utils.six.moves.urllib.parse import urlparse
from djblets.avatars.services import \
    FileUploadService as DjbletsFileUploadService

from reviewboard.admin.server import build_server_url


class FileUploadService(DjbletsFileUploadService):
    """A Review Board-specialized file upload avatar services.

    This service is almost identical to the :py:class:`one in Djblets
    <djblets.avatars.services.file_upload.FileUploadService>`, except we ensure
    that all URLs returned are absolute URLs.
    """

    def get_avatar_urls_uncached(self, user, size):
        """Return the avatar URLs for the requested user.

        Args:
            user (django.contrib.auth.models.User):
                The user whose avatar URLs are to be fetched.

            size (int):
                The size (in pixels) the avatar is to be rendered at.

        Returns
            dict:
            A dictionary containing the URLs of the user's avatars at normal-
            and high-DPI.
        """
        urls = super(FileUploadService, self).get_avatar_urls_uncached(user,
                                                                       size)

        return {
            resolution: self._ensure_absolute(url)
            for resolution, url in six.iteritems(urls)
        }

    def _ensure_absolute(self, url):
        """Return the provided URL as an absolute URL.

        Relative URLs will be prefixed with the site's domain method and domain.

        Returns:
            unicode:
            An absolute URL.
        """
        result = urlparse(url)

        if result.scheme and result.netloc:
            return url

        return build_server_url(url)
