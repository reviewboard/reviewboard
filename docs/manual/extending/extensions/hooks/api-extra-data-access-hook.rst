.. _api-extra-data-access-hook:

======================
APIExtraDataAccessHook
======================


.. currentmodule:: reviewboard.webapi.base

:py:class:`reviewboard.extensions.hooks.APIExtraDataAccessHook` is used
when an extension wants to give an ``extra_data`` field certain accessibility
rules by registering an access state to a given key. The access states are:

:py:data:`ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`:
    The extra data key can be retrieved and updated via the API.

:py:data:`ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY`:
    The extra data key can only be retrieved via the API. It cannot be
    updated.

:py:data:`ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`:
    The extra data key can neither be retrieved nor updated via the API.

Extensions wishing to use this functionality must provide:

1. The :py:class:`resource <WebAPIResource>` they wish to hook into
2. A mapping of each path (as a tuple of keys) to the desired access state

For example, consider the following ``extra_data`` object:

.. code-block:: python

   extra_data = {
       'pgp': {
           'public_key': 'my public key',
           'private_key': 'my private key',
       },
   }

In this case, to make the ``private_key`` field private, you could instantiate
the hook like:

.. code-block:: python

   APIExtraDataAccessHook(
       extension,
       resource,
       [
           (('pgp', 'private_key'), ExtraDataAccessLevel.ACCESS_STATE_PRIVATE),
       ])


The :py:meth:`APIExtraDataAccessHook.get_extra_data_state
<reviewboard.extensions.hooks.APIExtraDataAccessHook.get_extra_data_state>`
method can also be overridden to provide more complex behaviour in determining
the access level of an extra data key. An example follows:

Example
=======

.. code-block:: python

   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import APIExtraDataAccessHook
   from reviewboard.webapi.base import ExtraDataAccessLevel
   from reviewboard.webapi.resources import resources


   class CustomAccessHook(APIExtraDataAccessHook):
       """An extra data access hook that defaults to private.

       All extra_data keys on associated resources will be marked as private
       (and therefore not returned by the API) unless specified otherwise.
       """

       def get_extra_data_state(self, key_path):
           return (
               super(CustomAccessHook, self).get_extra_data_state(key_path) or
               None
           )


   class SampleExtension(Extension):
       def initialize(self):
           # Imagine a review request with an extra_data like this:
           #
           # review_request.extra_data = {
           #     'public': 'foo',
           #     'private': 'secret',
           #     'readonly': 'bar',
           # }

           access_hook = CustomAccessHook(
               self,
               resources.review_request,
               {
                   ('public',): ExtraDataAccessLevel.ACCESS_STATE_PUBLIC,
                   ('readonly',): ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY,
               })
