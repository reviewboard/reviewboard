.. webapi-error::
   :instance: reviewboard.webapi.errors.BAD_HOST_KEY
   :example-data:
       {
           "hostname": "svn.example.com",
           "key": "_key in base64_",
           "expected_key": "_key in base64_"
       }

   Review Board encountered an unexpected SSH key on host (typically a
   repository). The key found didn't match what Review Board had previously
   recorded.

   The hostname, key (in base64) and the key we expected to find (also in
   base64) will be returned along with the error.
