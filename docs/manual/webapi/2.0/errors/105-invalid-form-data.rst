.. webapi-error::
   :instance: djblets.webapi.errors.INVALID_FORM_DATA
   :example-data:
      {
          "fields": {
              "myint": [
                  "`abc` is not an integer"
              ]
          }
      }

   The data sent in the request (usually when using HTTP PUT or POST) had
   errors. One or more fields failed to validate correctly.

   This comes with a ``fields`` key containing a mapping of field names to
   lists of error texts.
