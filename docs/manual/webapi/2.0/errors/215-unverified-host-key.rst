.. webapi-error::
   :instance: reviewboard.webapi.errors.UNVERIFIED_HOST_KEY
   :example-data:
       {
           "hostname": "svn.example.com",
           "key": "_key in base64_"
       }

   Review Board encountered an unverified SSH key on another host (typically a
   repository). The key needs to be verified before Review Board can access
   the host.

   The hostname and key (in base64) will be returned along with the error.
