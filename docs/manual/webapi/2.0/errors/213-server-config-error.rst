.. webapi-error::
   :title: Server Configuration Error
   :instance: reviewboard.webapi.errors.SERVER_CONFIG_ERROR
   :example-data:
       {
           "reason": "Unable to write to /path/to/file."
       }

   Review Board attempted to store data in the database or a configuration
   file as needed to fulfill this request, but wasn't able to. The reason for
   this will be stored in ``reason``.
