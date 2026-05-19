.. _ssl-certificates:

============================================
Managing SSL/TLS Certificates and CA Bundles
============================================

.. versionadded:: 8.0

Review Board connects to external services (such as source code repositories
and authentication servers) over HTTPS or other SSL/TLS-based protocols
using :term:`SSL/TLS certificates` to verify and possibly authenticate with
the service.

Certificates may be used for:

* **Verification** of a service Review Board needs to connect to. We refer
  to these certificates as :term:`Trust Certificates`.

* **Authenticating** with a service using :term:`Mutual TLS (mTLS)`. We refer
  to these as :term:`Client Certificates`.

Certificates are normally issued by a :term:`Certificate Authority (CA)`
trusted by your operating system, but if you're maintaining services in-house,
you may be using :term:`self-signed certificates` or your company's
own Certificate Authority.

This guide covers how to install and manage your own :term:`CA bundles`
(containing your CA's own root certificate to trust) and self-signed SSL/TLS
certificates for use in Review Board.


.. _ssl-certificates-storage-location:

Certificate Storage Locations
=============================

All certificates and CA bundles are stored under the Review Board
:term:`site directory`'s :file:`data/rb-certs/file/` path.

The directory layout is as follows:

.. code-block:: text

   <site_dir>/data/rb-certs/file/
       cabundles/
           <slug>.pem

       certs/
           client/
               <hostname>__<port>.crt
               <hostname>__<port>.key
               __.<hostname>__<port>.crt
               __.<hostname>__<port>.key

           trust/
               <hostname>__<port>.crt
               __.<hostname>__<port>.crt

We'll cover the naming of these files below.

If you are using :term:`Local Sites`, certificates can be added for a
specific Local Site by placing them under a :file:`sites/` subdirectory:

.. code-block:: text

   <site_dir>/data/rb-certs/file/
       sites/
           <local_site_name>/
               cabundles/
                   ...

               certs/
                   ...

Certificates under :file:`sites/<local_site_name>/` only apply to connections
made within that Local Site.

Other files or directories within :file:`rb-certs/` should not be modified.


.. _ssl-certificates-ca-bundles:

CA Bundles
==========

A :term:`CA bundle` is a :term:`PEM`-formatted file containing one or more
:term:`Certificate Authority (CA)` root certificates and any intermediary
certificates.

When Review Board connects to a server whose certificate was signed by a CA
found in a bundle, the connection can be trusted. Creating an internal CA
and using it to sign certificates for your services is recommended over
creating individual :term:`self-signed certificates`. You can upload one
bundle to verify and trust all of your certificates.

To add a CA bundle:

1. Make sure your CA's root certificate (or certificate chain) is exported
   in :term:`PEM` format.

2. Place the file at:

   .. code-block:: text

      <site_dir>/data/rb-certs/file/cabundles/<slug>.pem

   The ``<slug>`` is a short name for the bundle. This can be anything, but
   it must follow the :term:`slug` format (lowercase letters, digits,
   and hyphens only).

   For example, if naming this ``internal-ca``, place the file at
   :file:`data/rb-certs/file/cabundles/internal-ca.pem` within your
   :term:`site directory`.

3. Make sure the file's permissions allow it to be read by the web server's
   user.

No server restart is required. Review Board will automatically verify against
your CA bundle as needed.


.. _ssl-certificates-individual:

Individual SSL/TLS Certificates
===============================

Individual certificates may target a specific hostname and port, or may be
a wildcard certificate applying to multiple servers.

They may represent a :term:`Trust Certificate` or a :term:`Client
Certificate`.

We'll walk you through :ref:`installation <ssl-certificates-install-cert>`,
but you'll need to know a bit about how to name the files first.


.. _ssl-certificates-naming:

Certificate Filenames
---------------------

Certificate files *must* follow this naming convention:

.. code-block:: text

   <hostname>__<port>.crt
   <hostname>__<port>.key

Note that the hostname and port are separated by **two underscores** and
the hostname must be lowercase.

For example:

.. code-block:: text

   git.example.com__443.crt
   ldap.corp.internal__636.crt
   ldap.corp.internal__636.key

.. note::

   If your domain uses any non-ASCII characters, you will need to encode
   the domain name using IDNA UTS #46 encoding. This is complex and beyond
   the scope of this guide.


.. _ssl-certificates-wildcard:

Wildcard Certificates
~~~~~~~~~~~~~~~~~~~~~

A wildcard certificate can apply to all subdomains of a domain. Instead of
using a ``*`` wildcard, the filename must instead start with ``__.`` (two
underscores followed by a period):

.. code-block:: text

   __.<hostname>__<port>.crt
   __.<hostname>__<port>.key

For example, ``__.example.com__443.crt`` would be used when connecting to
``git.example.com``, ``ldap.example.com``, or any other subdomain of
``example.com`` on port 443.

.. note::

   Only domains starting with a wildcard are supported. For instance,
   ``*.corp.example.com``. You cannot have a wildcard anywhere else in the
   hostname (``git.*.example.com`` will not work).


.. _ssl-certificates-install-cert:

Installing the Certificate
--------------------------

To add a certificate:

1. Make sure your certificate is exported in :term:`PEM` format.

2. If you're using a :term:`client certificate`, make sure you have its
   :term:`Private Key` in :term:`PEM` format.

3. Rename the files to use the correct :ref:`file naming
   <ssl-certificates-naming>` convention.

4. Place the file within:

   .. code-block:: text

      <site_dir>/data/rb-certs/file/certs/<type>/

   Replace ``<type>`` with the type of certificate. This will be one of:

   * :file:`trust/`:

     :term:`Trust certificates` that tell Review Board to trust a particular
     server's self-signed certificate.

     Only the certificate file (:file:`.crt`) is required. No
     :term:`Private Key` is needed.

   * :file:`client/`:

     :term:`Client certificates` that can be used for :term:`Mutual TLS
     (mTLS)` authentication.

     Both the certificate (:file:`.crt`) and :term:`Private Key`
     (:file:`.key`) files are required.

5. Make sure the file permissions allow them to be read by the web server's
   user.

No server restart is required to use your new certificates. Review Board will
automatically use them as needed.
