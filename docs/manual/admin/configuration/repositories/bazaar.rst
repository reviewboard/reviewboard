.. _repository-scm-bazaar:

===================
Bazaar Repositories
===================

Review Board supports posting and reviewing code on :rbintegration:`Bazaar
<bazaar>` repositories.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier.

.. todo: Add a link to RBTools docs for Bazaar, once written.

.. note::

   This guide assumes that you're adding a Bazaar repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires local or network access to your repository.

   Follow the documentation in the links below if your Bazaar repository is
   hosted on one of these services, as configuration may differ.

   * :ref:`SourceForge <repository-hosting-sourceforge>`


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing Bazaar Support
=========================

Before you add the repository, you will need to install Bazaar on the server.
We recommend installing this using the Python packages instead of your
distribution packages.

To install Bazaar, run::

    $ pip install bzr


Adding the Repository
=====================

To configure a Bazaar repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Bazaar` from the
:guilabel:`Repository type` field.

You can then enter any valid Bazaar repository path into the :guilabel:`Path`
field. If your repository may be used at an additional path, you can also
provide an additional path for lookup matching purposes in a :guilabel:`Mirror
path`.


Using SSH-Backed Reposoitories
------------------------------

If you're using a Bazaar repository over a SSH connection, you will need to
:ref:`configure a SSH key <ssh-settings>` in Review Board, and grant access on
the repository. You will also need to specify a username, either in the
repository path or in the :guilabel:`Username` field. The password field can
usually be left blank.
