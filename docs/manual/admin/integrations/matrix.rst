.. _integrations-matrix:

==================
Matrix Integration
==================

.. versionadded:: 5.0

Matrix_ is a decentralized chat service used for workplace communication, which
is based on an open standard. It supports numerous different clients and tools.

Review Board can integrate with Matrix to post notifications whenever review
requests or reviews are published. You can have multiple different Matrix
configurations to deliver notifications to different rooms (or even different
Matrix servers).


.. _Matrix: https://matrix.org/


Integration Configuration
=========================

To configure an integration with Matrix:

1. Click :guilabel:`Add Integration`, then select :guilabel:`Matrix` on the
   :guilabel:`Integrations` page in the :ref:`Administration UI
   <administration-ui>`.

2. Give the configuration a descriptive name. This can be anything at all, and
   just helps identify this configuration.

   .. image:: images/matrix-config-general.png

3. Select the conditions under which Review Board will send notifications to
   Matrix under this configuration. If you have a small Review Board server and
   want all notifications to go to the same place, you can set this to
   :guilabel:`Always match`. However, you can also create complex rules to
   match based on repository, groups, or other criteria.

   .. image:: images/matrix-config-conditions.png

4. Connect Review Board to Matrix. This requires three pieces of information.

   The :guilabel:`Access Token` is a key which allows Review Board to connect
   to Matrix. In Element, it can be found at :guilabel:`Profile -> All settings
   -> Help & About -> Advanced`.

   The :guilabel:`Room ID` is a key which identifies which room to send
   notifications to. In Element, it can be found by clicking the three dots
   beside the room icon, and then selecting :guilabel:`Settings -> Advanced`.

   Finally, the :guilabel:`Server URL` defines the Matrix server to connect to.
   In most cases this will be ``https://matrix.org`` but this can be changed if
   you have a different Matrix server.

   .. image:: images/matrix-config-where.png
