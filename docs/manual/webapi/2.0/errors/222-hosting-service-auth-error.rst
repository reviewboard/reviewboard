.. webapi-error::
   :title: Hosting Service Authentication Error
   :instance: reviewboard.webapi.errors.HOSTINGSVC_AUTH_ERROR
   :example-data:
       {
           "reason": "The username was invalid."
       }

   There was an error authenticating with a hosting service.

   The specific reason it failed is provided in ``reason``.
