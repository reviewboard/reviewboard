.. _review-workflow-settings:

========================
Review Workflow Settings
========================

.. versionadded:: 8.0

This page (:guilabel:`Admin UI -> Settings -> Review Workflow`) allows you
to configure the review process at your organization.

The following settings are available:

* :guilabel:`Allow users to mark "Ship It!" on their own review requests`

  If selected (the default), users can file a :ref:`Ship It! <ship-it>` on
  their own review requests.

  Administrators may want to disable this if they're using a
  :ref:`custom approval hook <review-request-approval-hook>` or other
  integration that does not consider "Ship It!" reviews from the owner of
  the change as valid.
