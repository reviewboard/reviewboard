.. _api-extra-data-access-hook:

======================
APIExtraDataAccessHook
======================

:py:class:`reviewboard.extensions.hooks.APIExtraDataAccessHook` is used
when an extension wants to give an ``extra_data`` field certain accessibility
rules by registering an access state to a given key. The access states can be
one of:
:py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`,
:py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC_READONLY`,
or :py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`.
When the resource is accessed through the API, those fields with registered
access states would then only be viewable or modifiable from within the code.

Extensions must provide a resource subclass of
:py:class:`reviewboard.webapi.base.WebAPIResource` as well as a ``field_set``
to :py:class:`reviewboard.extensions.hooks.APIExtraDataAccessHook`. Each
element of ``field_set`` is a 2-:py:class:`tuple` where the first element of
the tuple is the field's path (as a :py:class:`tuple`) and the second is the
field's access state (as one of
:py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PUBLIC`,
:py:data:`~reviewboard.webapi.base.ExtraDataAccessLevel.ACCESS_STATE_PRIVATE`,
etc.).

:py:meth:`~reviewboard.extensions.hooks.APIExtraDataAccessHook.get_extra_data_state`
determines if an ``extra_data`` field has an access state registered for it
and returns it. It accepts an argument, ``key_path``, which it compares
against the provided paths found in ``field_set`` and returns the associated
access state if a match is found.


Example
=======

.. code-block:: python

   from reviewboard.extensions.base import Extension
   from reviewboard.extensions.hooks import APIExtraDataAccessHook
   from reviewboard.webapi.base import WebAPIResource, ExtraDataAccessLevel
   from reviewboard.webapi.resources.review_request import \\
        ReviewRequestResource


   class CustomAccessHook(APIExtraDataAccessHook):
       def get_extra_data_state(self, key_path):
           for path, access_state in self.field_set:
               if path == key_path:
                   return access_state

           return ExtraDataAccessLevel.ACCESS_STATE_PRIVATE

   class SampleExtension(Extension):
       def initialize(self):
           review_request_resource = ReviewRequestResource()

           review_request_resource.extra_data = {
               'public': 'foo',
               'private': 'secret',
               'readonly': 'bar',
           }

           access_hook = CustomAccessHook(
               self,
               review_request_resource,
               [
                   (('public_item',), ExtraDataAccessLevel.ACCESS_STATE_PUBLIC)
               ])
