.. _avatar-service-hook:

=================
AvatarServiceHook
=================

:py:class:`reviewboard.extensions.hooks.AvatarServiceHook` allows extensions to
register new avatar services, which can be used to integrate with databases or
servers to handle the display of user avatars.

Extensions must provide a subclass of
:py:class:`djblets.avatars.services.AvatarService`, and pass it as a parameter
to :py:class:`AvatarServiceHook`. Each class must provide
:py:attr:`avatar_service_id` and :py:attr:`name` attributes, and must implement
:py:meth:`get_avatar_urls_uncached` and :py:meth:`get_etag_data` methods.


Example
=======

This example makes use of a theoretical service that can return image files for
a given user based on a hash of their e-mail address and a desired pixel size.


.. code-block:: python

    import hashlib

    from djblets.avatars.services import AvatarService
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import AvatarServiceHook


    class SampleAvatarService(AvatarService):
        avatar_service_id = 'myvendor_sample_avatar_service'
        name = 'Sample Avatar Service'

        def get_avatar_urls_uncached(self, user, size):
            url = 'https://pictures.example.com/?user=%s&size=%d'
            user_hash = hashlib.md5(user.email)

            return {
                '%dx' % resolution: url % (user_hash, size * resolution)
                for resolution in (1, 2, 3)
            }

        def get_etag_data(self, user):
            return [self.avatar_service_id, user.email]


    class SampleExtension(Extension):
        def initialize(self):
            AvatarServiceHook(self, SampleAvatarService)
