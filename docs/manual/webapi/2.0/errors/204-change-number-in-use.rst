.. webapi-error::
   :instance: reviewboard.webapi.errors.CHANGE_NUMBER_IN_USE
   :example-data:
       {"review_request": {}}

   The change number used to create a new review request wasn't valid, because
   another review request already exists with that change number. You will
   only see this with repositories that support server-side changesets, such
   as Perforce.

   Usually, the correct thing to do is to instead modify the other review
   request.

   The resource information for the review request that's associated with the
   change number will be returned in the ``review_request`` key.
