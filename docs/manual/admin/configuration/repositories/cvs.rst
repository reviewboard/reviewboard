.. _repository-scm-cvs:

================
CVS Repositories
================

Review Board supports posting and reviewing code on :rbintegration:`CVS <cvs>`
repositories. All standard CVS repository configurations can be used.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format and makes managing review
requests much easier. See :ref:`Using RBTools with CVS <rbt-post-cvs>` for more
information.

.. note::

   This guide assumes that you're adding a CVS repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires local or network access to your repository.

   Follow the documentation in the links below if your CVS repository is
   hosted on one of these services, as configuration may differ.

   * :ref:`SourceForge <repository-hosting-sourceforge>`


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing CVS Support
======================

Before you add the repository, you will need to install the :command:`cvs`
command line tool in a system path (or in a place accessible by your web
server's process). This can be installed through your system's package
manager.

See the :ref:`installation guide <installing-cvs>` for CVS.


Adding the Repository
=====================

To configure a CVS repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`CVS` from the
:guilabel:`Repository type` field.

You will see a :guilabel:`Path` field, which should contain the CVSROOT
for your repository. This can use any of the following CVS connection methods:

* :ref:`repository-scm-cvs-credential-cvsroots`:

  * ``:gserver:``
  * ``:kserver:``
  * ``:pserver:``

* :ref:`repository-scm-cvs-ssh-cvsroots`:

  * ``:ext:``
  * ``:extssh:``
  * ``:ssh:``

* :ref:`repository-scm-cvs-local-cvsroots`:

  * ``:fork:``
  * ``:local:``


Determining Your CVSROOT
------------------------

To determine the CVSROOT of an existing checkout, you can go to the top-most
directory of the checkout and type::

    $ cat CVS/Root

This will show the CVSROOT used for your repository. You can use the value
as-is, or modify it to suit your needs. See below for more details.


.. _repository-scm-cvs-credential-cvsroots:

Credential-Based CVSROOTs
-------------------------

If you're using ``:pserver:``, ``:gserver:``, or ``:kserver:``, you're going
to need to specify credentials (a username and password) for your repository.
You can specify these credentials either in the :guilabel:`Path` field or in
the :guilabel:`Username` and :guilabel:`Password` fields.

Credentials specified in :guilabel:`Username` and :guilabel:`Password` will
only be used if using ``:pserver:``, ``:gserver:``, or ``:kserver``
connection methods, and if the credentials aren't already provided in
:guilabel:`Path`.

.. tip::

   Specify the credentials outside of the CVSROOT, if possible. This will
   allow RBTools_ or other clients to locate your repository by CVSROOT,
   which may not be possible if it contains a username or password.


Examples
~~~~~~~~

* ``:pserver:cvs.example.com/cvsroot``
* ``:pserver:anonymous@cvs.example.com/cvsroot``
* ``:pserver:myuser:mypass@cvs.example.com:1234/cvsroot``


.. _repository-scm-cvs-ssh-cvsroots:

SSH-Based CVSROOTs
------------------

If you're using ``:ext:``, ``:extssh:``, or ``:ssh:``, you will need to
:ref:`configure a SSH key <ssh-settings>` in Review Board, and grant access on
the repository. You will also need the specify the username, either in the
CVSROOT or in the :guilabel:`Username` field. The :guilabel:`Password` field
must be blank.

.. note::

   The ``:server:`` connection method should not be used, as it makes use of
   an internal SSH client that will not see your configured Review Board SSH
   key. It's also not supported by all CVS implementations.

.. tip::

   If your repository has an alternative ``:pserver:`` (or other) CVSROOT that
   people can use, you may want to specify it in the :guilabel:`Mirror path`
   field. This is used only for path matching when looking up repositories.


Examples
~~~~~~~~

* ``:extssh:cvs.example.com:/cvsroot``
* ``:ssh:localhost:22/cvsroot``
* ``:ssh:username@cvs.example.com:/cvsroot``
* ``:ext:username@cvs.example.com:/cvsroot``
* ``:ext:username@cvs.example.com:/cvsroot``
* ``:ext:cvs.example.com:/cvsroot``


.. _repository-scm-cvs-local-cvsroots:

Local CVSROOTs
--------------

If your repository lives on the same machine as Review Board, you can refer to
it by local path using ``:local:`` or ``:fork:``.

.. tip::

   You should specify the CVSROOT that users connecting to your server would
   use in the :guilabel:`Mirror path` field. This is used only for path
   matching when looking up repositories.


Examples
~~~~~~~~

* ``:local:C:\CVSROOTS\myproject``
* ``:local:/home/myuser/cvsroot``
* ``:fork:/home/myuser/cvsroot``
