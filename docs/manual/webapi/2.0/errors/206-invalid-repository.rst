.. webapi-error::
   :instance: reviewboard.webapi.errors.INVALID_REPOSITORY
   :example-data:
      {"repository": "http://svn.example.com/ducks"}

   The repository path or ID specified in the request isn't known by Review
   Board.

   This will provide a ``repository`` key containing the path or ID that
   failed.
