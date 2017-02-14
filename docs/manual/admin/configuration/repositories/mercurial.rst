.. _repository-scm-mercurial:

======================
Mercurial Repositories
======================

Review Board supports posting and reviewing code on :rbintegration:`Mercurial
<mercurial>` repositories.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Mercurial
<rbt-post-mercurial>` for more information.

.. note::

   This guide assumes that you're adding a Mercurial repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires either local access to your repository or
   network access using hgweb (as documented below) or another hosting
   service.

   Follow the documentation in the links below if your Mercurial repository is
   hosted on one of these services, as configuration will differ.

   * :ref:`Bitbucket <repository-hosting-bitbucket>`
   * :ref:`Codebase <repository-hosting-codebasehq>`
   * :ref:`Fedora Hosted <repository-hosting-fedorahosted>`
   * :ref:`SourceForge <repository-hosting-sourceforge>`

   If your Mercurial repository is hosted on another third-party service, it
   may not work with Review Board! Please contact us to request support
   for that service.


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing Mercurial Support
============================

Before you add the repository, you will need to install Mercurial on the
server. We recommend installing this using the Python packages instead of your
distribution packages.

To install Mercurial, run::

    $ pip install mercurial


Adding the Repository
=====================

To configure a Mercurial repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Mercurial` from the
:guilabel:`Repository type` field.

If your repository is within your network and accessed remotely, you will need
to enable hgweb_. You can then point to the ``http://`` or ``https://`` URL.
See :ref:`repository-scm-mercurial-hgweb`.

If your repository is locally accessible over the file system via the Review
Board server, you can point to file path of the repository. However, there are
caveats. See :ref:`repository-scm-mercurial-local-clone`.

If your repository is instead hosted on a compatible source code hosting
service like :rbintegration:`Bitbucket <bitbucket>`, you'll want to refer to
the instructions on that service. See the list above.


.. _hgweb: https://www.mercurial-scm.org/repo/hg/help/hgweb


.. _repository-scm-mercurial-hgweb:

Using a hgweb-Backed Repository
-------------------------------

If you have hgweb installed for your repository, you can point to the
``http://`` or ``https://`` URL for your repository. Review Board can use this
to fetch the files from the repository for review.

To start, you'll need to install hgweb. You can follow `Mercurial's
documentation on hgweb`_.

Once that's set up, you will want to set your :guilabel:`Path` field to the
hgweb path for the repository. This is the same as your clone path. For
example:

``https://hg.example.com/repo/myrepo``

Or for a real-world example: https://www.mercurial-scm.org/repo/evolve

If your repository is protected by Basic HTTP Auth, you can supply credentials
in the :guilabel:`Username` and :guilabel:`Password` fields. They will be used
any time Review Board accesses your hgweb instance.

If you use the post-commit review request feature with hgweb, you need to use
at least Mercurial 3.9.


.. _Mercurial's documentation on hgweb:
   https://www.mercurial-scm.org/wiki/PublishingRepositories#hgweb


.. _repository-scm-mercurial-local-clone:

Using a Local Clone
-------------------

Review Board can make use of a locally-accessible Mercurial clone, so long as
that clone contains the very latest changes for your repository.

If the Mercurial clone is the master repository that your developers are
cloning from, then you're in good shape. However, if it's a clone of the
master repository, you will need to ensure it's consistently up-to-date. One
way to do this would be to have a cron job pull the latest changes at least
once a minute.

When using a local clone, you'll need to point the :guilabel:`Path` field to
the clone directory. For example: ``/var/hg/projectname/``.

You will leave the :guilabel:`Username` and :guilabel:`Password` fields blank.
