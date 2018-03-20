.. _integrations-slack:

=================
Slack Integration
=================

.. versionadded:: 3.0

Slack_ is a popular chat service used for workplace communication, supporting
integrations with a great number of services.

Review Board can integrate with Slack to post notifications whenever review
requests or reviews are published. You can have multiple different Slack
configurations to deliver notifications to different channels (or even
different Slack instances).


.. _Slack: https://slack.com/


Integration Configuration
=========================

To configure an integration with Slack:

1. Click :guilabel:`Add a new configuration` for Slack on the
   :guilabel:`Integrations` page in the :ref:`Administration UI
   <administration-ui>`.

   .. image:: images/slack-add-integration.png

2. Give the configuration a descriptive name. This can be anything at all, and
   just helps identify this configuration.

   .. image:: images/slack-config-general.png

3. Select the conditions under which Review Board will send notifications
   to Slack under this configuration. If you have a small Review Board server
   and want all notifications to go to the same place, you can set this to
   :guilabel:`Always match`. However, you can also create complex rules to
   match based on repository, groups, or other criteria.

   .. image:: images/slack-config-conditions.png

4. Register a new Incoming WebHook on Slack by visiting the `App Directory`_.
   You can also get there by viewing a channel in Slack, clicking its name
   in the bar above the chat, then clicking :guilabel:`Add apps -> Manage
   apps...`

   Once there, navigate to :guilabel:`Custom Integrations -> Incoming WebHooks
   -> Add Configuration`. Choose the channel you want to post updates to and
   then click :guilabel:`Add Incoming WebHooks integration`.

   This will create your Incoming WebHook. Look for the :guilabel:`Webhook
   URL` and paste that in the matching field for your configuration on Review
   Board.

   .. image:: images/slack-config-where.png

5. If you want to reuse the same WebHook URL for multiple channels on the
   same Slack team, you can. Just provide the same URL you used in another
   integration and then set the :guilabel:`Send to Channel` field to your
   desired channel.


.. _App Directory: https://slack.com/apps/manage
