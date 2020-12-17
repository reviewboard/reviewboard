.. _integrations-discord:

===================
Discord Integration
===================

.. versionadded:: 4.0

Discord_ is a popular chat service used by various communities, supporting
integrations with a great number of services.

Review Board can integrate with Discord to post notifications whenever review
requests or reviews are published. You can have multiple different Discord
configurations to deliver notifications to different channels (or even
different Discord servers).


.. _Discord: https://discord.com/


Integration Configuration
=========================

To configure an integration with Discord:

1. Click :guilabel:`Add a new configuration` for Discord on the
   :guilabel:`Integrations` page in the :ref:`Administration UI
   <administration-ui>`.

   .. image:: images/discord-add-integration.png

2. Give the configuration a descriptive name. This can be anything at all, and
   just helps identify this configuration.

   .. image:: images/discord-config-general.png

3. Select the conditions under which Review Board will send notifications
   to Discord under this configuration. If you have a small Review Board
   server and want all notifications to go to the same place, you can set this
   to :guilabel:`Always match`. However, you can also create complex rules to
   match based on repository, groups, or other criteria.

   .. image:: images/discord-config-conditions.png

4. Register a new Incoming WebHook on Discord by visiting the
   :guilabel:`Server Settings` in the dropdown menu beside the Discord Server
   name.

   Once there, navigate to :guilabel:`Integrations`, then click the
   :guilabel:`Create Webhook` button, which will create your Incoming WebHook.
   Choose the channel you want to post updates to using Discord's dropdown
   menu.

   Look for the button :guilabel:`Copy Webhook URL` and paste that in the
   matching field for your configuration on Review Board.

   .. image:: images/discord-config-where.png
