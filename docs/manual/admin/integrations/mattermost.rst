.. _integrations-mattermost:

======================
Mattermost Integration
======================

.. versionadded:: 3.0.4

Mattermost_ is an open source chat and collaboration service similar to and
largely compatible with Slack. It can be installed within a company's network,
and offers Enterprise capabilities.

Review Board can integrate with Mattermost to post notifications whenever
review requests or reviews are published. You can have multiple different
Mattermost configurations to deliver notifications to different channels (or
even different Mattermost instances).


.. _Mattermost: https://mattermost.com/


Integration Configuration
=========================

To configure an integration with Mattermost:

1. Click :guilabel:`Add a new configuration` for Mattermost on the
   :guilabel:`Integrations` page in the :ref:`Administration UI
   <administration-ui>`.

   .. image:: images/mattermost-add-integration.png

2. Give the configuration a descriptive name. This can be anything at all, and
   just helps identify this configuration.

   .. image:: images/mattermost-config-general.png

3. Select the conditions under which Review Board will send notifications
   to Mattermost under this configuration. If you have a small Review Board server
   and want all notifications to go to the same place, you can set this to
   :guilabel:`Always match`. However, you can also create complex rules to
   match based on repository, groups, or other criteria.

   .. image:: images/mattermost-config-conditions.png

4. Register a new Incoming WebHook on Mattermost. To do this, open the Main
   Menu in Mattermost and click :guilabel:`Integrations`. Then click
   :guilabel:`Incoming Webhook -> Add Incoming Webhook`.

   .. image:: images/mattermost-menu.png

   Provide a title and description of your choosing, and then select the
   channel you want to post updates to and click :guilabel:`Save`.

   This will create your Incoming WebHook. Copy the URL it generates and paste
   that in the matching field for your configuration on Review Board.

   .. image:: images/mattermost-config-where.png

5. If you want to reuse the same WebHook URL for multiple channels on the
   same Mattermost team, you can. Just provide the same URL you used in another
   integration and then set the :guilabel:`Send to Channel` field to your
   desired channel.
