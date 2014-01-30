.. _ssh-settings:

============
SSH Settings
============

The SSH settings page covers the SSH key being used to talk to SSH-backed
repositories. The page's contents differ depending on whether an SSH
key is configured.


Configure an SSH Key
====================

If an SSH key is not yet provided, you will have the option of generating a
new key, or uploading an existing private key.

Click :guilabel:`Generate an SSH Key` to generate a brand new SSH key
specific to your Review Board server.

Click :guilabel:`Upload an SSH Key` to upload an existing :file:`id_dsa` or
:file:`id_rsa` file. This must be a private key, not a public key.

.. note::

   If you choose to upload an existing SSH key, be aware that it will be
   readable by the web server and potentially anything running on it.
   Only provide one you feel safe using, and only if you trust the server.


SSH Key Details
===============

If an SSH key is already configured, the SSH Settings page will show details
on that key. Those details cover:

* Key type
* Number of bits of encryption
* Public fingerprint
* Public key

The public key can be used on other repositories to grant permission to
Review Board in order to access its files.
