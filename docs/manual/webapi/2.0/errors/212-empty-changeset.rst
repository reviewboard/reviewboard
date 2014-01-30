.. webapi-error::
   :instance: reviewboard.webapi.errors.EMPTY_CHANGESET

   The change number provided for the request represents a server-side
   changeset that doesn't contain any files. You will only ever see this for
   repositories that implement server-side changesets, such as Perforce. Add
   some files to the changeset and try again.
