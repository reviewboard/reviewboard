.. webapi-error::
   :title: Repository Authentication Error
   :instance: reviewboard.webapi.errors.REPO_AUTHENTICATION_ERROR
   :example-data:
       {
           "reason": "The username is invalid."
       }

   Review Board attempted to authenticate with a repository, but the proper
   login information wasn't specified.

   The specific reason it failed is returned in ``reason`` along with the
   error.
