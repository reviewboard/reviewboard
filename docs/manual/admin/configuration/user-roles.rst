.. _user-roles:

==========
User Roles
==========

.. versionadded:: 8.0

User Roles are a flexible way to identify a user's responsibilities and
position in an organization, and help craft policy and automation rules.

Administrators can create roles and assign them to any number of licensed
users. These can be used when configuring :ref:`integrations <integrations>`
or writing :ref:`custom approval hooks <review-request-approval-hook>`.
They'll optionally appear as badges alongside the user throughout the UI.

.. admonition:: User Roles requires a Review Board subscription

   It's included in a `Review Board Plus or Enterprise
   <https://www.reviewboard.org/get/>`_ subscription, and with a legacy
   `Power Pack`_ license.


.. _Power Pack: https://www.reviewboard.org/powerpack/


Adding User Roles
=================

Roles are managed through the :ref:`Administration UI <administration-ui>`.
To manage roles, click the :guilabel:`User Roles` entry in the
:guilabel:`Manage` section of the sidebar. This is also accessible through
the :guilabel:`Database` button in the :guilabel:`Review Board Power Pack`
entry in :guilabel:`Administration UI -> Extensions`.

A role has the following fields:

* :guilabel:`Role name`

  The display name of the role as it will appear in the UI.

* :guilabel:`Slug identifier`

  A unique identifier for the role used in integrations and approval hooks.
  This must be in :term:`slug` format (lowercase letters, digits, and
  hyphens only).

* :guilabel:`Show badges`

  When enabled, a badge displaying the role will appear alongside the user
  throughout certain parts of the UI. See `Displaying Badges`_ for details.

* :guilabel:`Assigned users`

  The list of users who belong to this role. Only users assigned to your
  license may be assigned to a role. A user may have multiple roles.

Once the fields are filled in, click :guilabel:`Save` to create or update the
role.


Displaying Badges
=================

When :guilabel:`Show badges` is enabled for a role, a badge displaying the
role's name will appear next to the user in review discussions and other
places throughout the website. This makes it easy to identify the
responsibilities of participants at a glance.

If a role is only needed for policy enforcement or integration conditions and
you do not want a visible badge, uncheck :guilabel:`Show badges` when creating
or editing the role.


Using Roles in Integrations
===========================

Once roles are defined, they can be referenced as conditions when setting up
:ref:`integrations <integrations>`. The following conditions are available:

* :guilabel:`Owner's user role`

  Matches based on the role assigned to the user who posted the review
  request.

* :guilabel:`Participant's user role`

  Matches based on the role assigned to any participant in the review
  (anyone who has posted a review or is a targeted reviewer).

For example, you can trigger a Slack notification whenever a QA Tester
publishes a review.


Using Roles in Approval Hooks
=============================

Roles can be used for enforcing role-based approval policies, such as
requiring a Ship It! from a Team Lead before a change can land. See the
:ref:`approval hook documentation <review-request-approval-hook>` for
a full example.
