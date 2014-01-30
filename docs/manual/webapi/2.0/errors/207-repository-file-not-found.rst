.. webapi-error::
   :title: Repository File Not Found
   :instance: reviewboard.webapi.errors.REPO_FILE_NOT_FOUND
   :example-data:
       {
           "file": "/src/foobar.c",
           "revision": 42
       }

   A file specified in a request that should have been in the repository was
   not found there. This could be a problem with the path or the revision.

   This will provide ``file`` and ``revision`` keys containing the file path
   and revision that failed.
