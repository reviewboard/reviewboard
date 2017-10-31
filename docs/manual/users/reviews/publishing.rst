.. _publishing-reviews:

==================
Publishing Reviews
==================

You can publish your review by clicking :guilabel:`Publish Review` on the
:ref:`review draft banner <review-draft-banner>` or
:ref:`review dialog <review-dialog>`.

.. image:: review-draft-banner-publish.png

After publishing your review, it will show up in the review request page with
all the comments you've written. Anybody can reply to your comments to discuss
your feedback.

If the administrator has enabled e-mail support, the owner of the review
request and all existing reviewers will be e-mailed a copy of your new review.
Notifications may also be sent to any chat services you have configured.

Once you have published a review, you can't go back and edit it (but you can
later :ref:`revoke a Ship It! <revoking-ship-it>` if you filed one).


.. _publish-review-owner-only:

E-mailing Only the Owner On Publish
===================================

If your comments are pretty trivial, or not worth e-mailing out to everyone
who's watching, you can choose to publish reviews only to the owner of the
change. Everyone can still see them on the review request page, but they won't
receive e-mails.

You can do this by hovering over the drop-down arrow on the :guilabel:`Publish
Review` and choosing :guilabel:`and only e-mail the owner` (instead of
clicking :guilabel:`Publish Review` directly). That will immediately publish
your change and e-mail only the owner.

.. image:: review-draft-banner-publish-owner-only.png

Note that Review Board extensions and integrations may change their behavior
as well when choosing this option.
