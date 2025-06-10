.. _integrations-microsoft-teams:

===========================
Microsoft Teams Integration
===========================

.. versionadded:: 7.0

`Microsoft Teams`_ is a team collaboration application, offering workspace
chat and supporting integrations with a great number of services.

Review Board can integrate with Microsoft Teams to post notifications whenever
review requests and reviews are published. You can have multiple different
Microsoft Teams configurations to deliver notifications to different channels
(or even different teams).


.. _Microsoft Teams: https://www.microsoft.com/en-us/microsoft-teams/


Integration Configuration
=========================

To configure an integration with Microsoft Teams:

1. Click :guilabel:`Add Integration` on the :guilabel:`Integrations` page
   in the :ref:`Administration UI <administration-ui>` and select
   :guilabel:`Microsoft Teams` from the list.

   .. image:: images/add-integration.png

2. Give the integration a name. This can be anything at all, and helps
   to identify this integration.

3. Select the conditions under which Review Board will send notifications to
   Microsoft Teams under this integration.

   If you have a small Review Board server and want all notifications to go to
   the same place, you can set this to :guilabel:`Always match`. However, you
   can also create complex rules to match based on repositories, groups, or
   other criteria.

   .. image:: images/config-conditions.png

4. Create a new Incoming WebHook on Microsoft Teams. See here_ for more
   information.

   On the WebHook creation page, you may optionally set this
   `Review Board logo`_ as the image to associate with incoming messages.

   Once it is created, copy the WebHook URL then go back to Review
   Board and paste it in the :guilabel:`WebHook URL` field for your
   integration.

.. _here: https://www.reviewboard.org/integrations/microsoft-teams/#microsoft-teams-setup
.. _Review Board logo: https://static.reviewboard.org/integration-assets/msteams/reviewboard.png?20240501-1234