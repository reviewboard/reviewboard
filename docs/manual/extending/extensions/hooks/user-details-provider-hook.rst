.. _user-details-provider-hook:

=======================
UserDetailsProviderHook
=======================

.. versionadded:: 7.1

User Detail Providers can provide information about users for specialized
purposes. As of now, these can provide:

* Badges: Groups of badged text displayed alongside users' names in parts of
  the UI (such as discussions and infoboxes).


Creating User Details Providers
===============================

To create a User Details Provider, you'll need to subclass
:py:class:`reviewboard.accounts.user_details.BaseUserDetailsProvider`. You
must set the following:

* :py:attr:`~reviewboard.accounts.user_details.BaseUserDetailsProvider.
  user_details_provider_id`:

  A unique ID of the provider. This should be prefixed with a vendor or
  extension ID to avoid collisions.

It may also define:

* :py:meth:`~reviewboard.accounts.user_details.BaseUserDetailsProvider.
  get_user_badges`:

  Calculates and returns
  :py:class:`~reviewboard.accounts.user_details.UserBadge` instances for
  any badges to display for a user.


Example
=======

.. code-block:: python

   from reviewboard.accounts.user_details import (BaseUserDetailsProvider,
                                                  UserBadge)
   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import UserDetailsProviderHook

   class MyUserDetailsProvider(BaseUserDetailsProvider):
       user_details_provider_id = 'my-user-details-provider'

       def get_user_badges(self, user, *, local_site, request, **kwargs):
           yield UserBadge(user=user,
                           label='Developer')

           if user.is_superuser:
               yield UserBadge(user=user,
                               label='Administrator')


   class SampleExtension(Extension):
       def initialize(self):
           UserDetailsProviderHook(self, MyUserDetailsProvider())
