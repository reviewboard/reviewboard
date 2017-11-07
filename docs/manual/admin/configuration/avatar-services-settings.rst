.. _avatar-services-settings:

========================
Avatar Services Settings
========================

The Avatar Services page allows you to configure which methods users can use
for their user avatars. This page allows you to enable or disable avatars
entirely, enable one or more avatar services, and select which service will act
as the default for users that haven't explicitly configured it.

By default, Review Board is set up to prefer Gravatars_ and allow users to
upload their own image files through their account settings.

Additional avatar services can be provided by extensions, which can be a useful
mechanism if you have a corporate system for people photos that you'd like to
integrate with. See :ref:`avatar-service-hook` for more information on writing
avatar service backends.

.. _Gravatars: https://gravatar.com/
