.. _integrations-slack:

=================
Slack Integration
=================

Slack_ is a popular chat service used for workplace communication. Review Board
can integrate with Slack to post notifications whenever review requests or
reviews are published.


Integration Configuration
=========================

To configure integration with Slack, click :guilabel:`Add a new
configuration` on the :guilabel:`Integrations` page in the :ref:`Administration
UI <administration-ui>`. You can have multiple different Slack configurations
to deliver notifications to different channels (or even different Slack
instances).

The :guilabel:`Name` field can be used to set a name for this particular
configuration. This allows you to keep track of which is which in the case
where you have multiple Slack configurations.

:guilabel:`Conditions` allows you to set conditions for when Review Board will
send notifications for this configuration. If you have a small Review Board
server and want all notifications to go to the same place, you can set this to
:guilabel:`Always match`. However, you can also create complex rules to match
based on repository, groups, or other criteria.


.. _Slack: https://slack.com/
