.. _repository-scm-subversion:

=======================
Subversion Repositories
=======================

Review Board supports posting and reviewing code on :rbintegration:`Subversion
<subversion>` repositories. It also supports browsing for commits in the
:ref:`New Review Request page <new-review-request-page>`. All standard
Subversion repository configurations and access methods can be used.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, working around many
Subversion diff generation issues, and makes managing review requests much
easier. See :ref:`Using RBTools with Subversion <rbt-post-subversion>` for
more information.

.. note::

   This guide assumes that you're adding a Subversion repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires local or network access to your repository.

   Follow the documentation in the links below if your Subversion repository is
   hosted on one of these services, as configuration may differ.

   * :ref:`Assembla <repository-hosting-assembla>`
   * :ref:`Beanstalk <repository-hosting-beanstalk>`
   * :ref:`Codebase <repository-hosting-codebasehq>`
   * :ref:`Fedora Hosted <repository-hosting-fedorahosted>`
   * :ref:`SourceForge <repository-hosting-sourceforge>`
   * :ref:`Unfuddle <repository-hosting-unfuddle>`


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing Subversion Support
=============================

Before you add the repository, you will need to install either PySVN_ or
Subvertpy_. These are Python modules that support communicating with
Subversion repositories. If both are installed, PySVN will take precedence.

PySVN may be harder to install on some systems, but provides better
compatibility than Subvertpy. We recommend using PySVN if possible.

See the :ref:`installation guide <installing-svn>` for PySVN and Subvertpy.


.. _PySVN: http://pysvn.tigris.org/
.. _Subvertpy: https://pypi.python.org/pypi/subvertpy


Adding the Repository
=====================

To configure a Subversion repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Subversion` from the
:guilabel:`Repository type` field.

You will see a :guilabel:`Path` field, which should contain the URL for the
Subversion repository. This can make use of ``https://``, ``svn://``, or
``svn+ssh://`` repository paths.

Once added, the repository will be checked to make sure your path and
credentials are correct. If using an HTTPS-backed repository, the SSL
certificate will also be checked for validity, and you may be prompted to
confirm the certificate details.


.. warning::

   Make sure to use the **root** of your Subversion repository. This is
   important. While you can technically add a Subversion repository path that
   points to a subdirectory of the repository, you will most likely encounter
   complications when posting diffs.

.. tip::

   If some users are accessing your repository using one protocol (such as
   ``https://``) and others are accessing with another (such as
   ``svn+ssh://``), you'll want to specify the primary one Review Board should
   use to connect in the :guilabel:`Path` field and the other (which will just
   be used for repository matching purposes) in :guilabel:`Mirror path`.


Determining your Repository Path
--------------------------------

To determine the repository path to use, run the following inside a checkout
of your repository::

    $ svn info

Look for the ``Repository Root`` field. The value listed is the path you
should use for Review Board.


Using ``https://`` or ``svn://`` Repositories
---------------------------------------------

If you're using a Subversion repository with ``https://`` or ``svn://``,
you'll need to supply a username and password, either in the URL or in the
:guilabel:`Username` and :guilabel:`Password` fields.


Examples
~~~~~~~~

* ``https://svn.example.com/myrepo/``
* ``https://username@svn.example.com/myrepo/``
* ``svn://svn.example.com/myrepo/``
* ``svn://username@svn.example.com/myrepo/``


Using ``svn+ssh://`` Reposoitories
----------------------------------

If you're using a Subversion repository with ``svn+ssh://`` you will need to
:ref:`configure a SSH key <ssh-settings>` in Review Board, and grant access on
the repository. You will also need to specify a username, either in the
repository path or in the :guilabel:`Username` field. The password field can
usually be left blank.


Examples
~~~~~~~~

* ``svn+ssh://svn.example.com/myrepo/``
* ``svn+ssh://username@svn.example.com/myrepo/``
