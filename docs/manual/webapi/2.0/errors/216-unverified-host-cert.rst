.. webapi-error::
   :title: Unverified Host Certificate
   :instance: reviewboard.webapi.errors.UNVERIFIED_HOST_CERT
   :example-data:
       {
           "certificate": {
               "failures": ["failure 1", "failure 2", "..."],
               "fingerprint": "_https certificate fingerprint_",
               "hostname": "svn.example.com",
               "issuer": "MyIssuer",
               "valid": {
                   "from": "_date_",
                   "until": "_date_"
               }
           }
       }

   Review Board encountered an unverified HTTPS certificate another host
   (typically a repository).  The certificate needs to be verified before
   Review Board can access the host.

   The certificate information will be returned along with the error.
