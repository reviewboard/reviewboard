.. _repository-scm-git:

================
Git Repositories
================

Review Board supports posting and reviewing code on :rbintegration:`Git <git>`
repositories.

Unlike most types of source code management systems, Git has a *very* limited
remote protocol, which isn't capable of some of the requests Review Board and
other similar tools require. Because of this, if Review Board does not have
local file-based access to your main Git repository, you will need to set up a
wrapping service, such as :ref:`GitWeb <repository-scm-git-gitweb>` or
:ref:`cgit <repository-scm-git-cgit>`. This is covered in more detail later in
this guide.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` for
more information.

.. note::

   This guide assumes that you're adding a Git repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires either local access to your repository or
   network access using a wrapping service (as documented below).

   Follow the documentation in the links below if your Git repository is
   hosted on one of these services, as configuration will differ.

   * :ref:`Assembla <repository-hosting-assembla>`
   * :ref:`AWS CodeCommit <repository-hosting-aws-codecommit>`
   * :ref:`Beanstalk <repository-hosting-beanstalk>`
   * :ref:`Bitbucket <repository-hosting-bitbucket>`
   * :ref:`Bitbucket Server <repository-hosting-bitbucket-server>`
   * :ref:`Codebase <repository-hosting-codebasehq>`
   * :ref:`Fedora Hosted <repository-hosting-fedorahosted>`
   * :ref:`GitHub <repository-hosting-github>`
   * :ref:`GitHub Enterprise <repository-hosting-github-enterprise>`
   * :ref:`GitLab <repository-hosting-gitlab>`
   * :ref:`Gitorious <repository-hosting-gitorious>`
   * :ref:`Unfuddle <repository-hosting-unfuddle>`
   * :ref:`VisualStudio.com <repository-hosting-visualstudio>`

   If your Git repository is hosted on another third-party service, it
   will not work with Review Board! Please contact us to request support
   for that service.


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing Git Support
======================

Before you add the repository, you will need to install the :command:`git`
command line tool in a system path (or in a place accessible by your web
server's process). This can be installed through your system's package
manager.

See the :ref:`installation guide <installing-git>` for Git.


Adding the Repository
=====================

To configure a Git repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Git` from the
:guilabel:`Repository Type` field.

If your repository is locally accessible over the file system via the Review
Board server, you can point to file path of the repository. However, there are
caveats. See :ref:`repository-scm-git-local-clone`.

If your repository is within your network, you will need an intermediary Git
wrapping service, such as :ref:`GitWeb <repository-scm-git-gitweb>` or
:ref:`cgit <repository-scm-git-cgit>`.

If your repository is instead hosted on a compatible source code hosting
service like :rbintegration:`GitHub <github>` or :rbintegration:`Bitbucket
<bitbucket>`, you'll want to refer to the instructions on that service. See
the list above.


.. _repository-scm-git-gitweb:

Using a GitWeb-Backed Repository
--------------------------------

If you're self-hosting one or more Git repositories, you can `install GitWeb`_
and use it as a form of remote API for Review Board. This will give you basic
support for posting and reviewing changes (though some features, like browsing
for commits on the :ref:`New Review Request page <new-review-request-page>`,
will not work).

Once you have GitWeb set up, you will want to set your :guilabel:`Path` field
to the main clone path of your repository. If you use both HTTPS and SSH
access to your repository, set one in :guilabel:`Path` and the other in
:guilabel:`Mirror Path`.

If you're using an SSH-backed repository, you will need to :ref:`configure a
SSH key <ssh-settings>` in Review Board, and grant access on the repository.

You will then need to set the :guilabel:`Raw File URL Mask` field to point to
a specific URL on your GitWeb server. This field essentially specifies a
URL template that Review Board can fill in with a filename and Git blob SHA
that will return the contents of that file and blob. This should take the form
of:

:samp:`https://{servername}/?p={relative_repo_path};a=blob_plain;f=<filename>;h=<revision>`

For example, if your repository is configured in GitWeb as
``projects/myrepo.git`` and your GitWeb is at ``git.example.com``, you will
want to use:

``https://git.example.com/?p=projects/myrepo.git;a=blob_plain;f=<filename>;h=<revision>``


.. _install GitWeb: https://git-scm.com/book/en/v2/Git-on-the-Server-GitWeb


.. _repository-scm-git-cgit:

Using a cgit-Backed Repository
------------------------------

One alternative to GitWeb would be to install cgit_. This works similarly to
GitWeb, in that it will make use of the :guilabel:`Raw File URL Mask` field.

Follow the instructions in :ref:`repository-scm-git-gitweb`, but use the following
for the URL mask:

:samp:`http://{servername}/browse/{repo_name}/blob/<filename>?id=<revision>`

For example, if your repository name is ``myproject`` and your server name is
``git.example.com``, you would use:

``http://git.example.com/browse/myproject/blob/<filename>?id=<revision>``


.. seealso::

   `cgit's Installation Instructions
   <https://git.zx2c4.com/cgit/tree/README>`_

   `Installing cgit on ArchLinux
   <https://wiki.archlinux.org/index.php/Cgit>`_


.. _cgit: https://git.zx2c4.com/cgit/about/
.. _install cgit: https://wiki.gnome.org/GnomeWeb/Tutorials/LocalGit


.. _repository-scm-git-local-clone:

Using a Local Clone
-------------------

Review Board can make use of a locally-accessible Git clone, so long as that
clone contains the very latest changes for your repository. This is an easy
way to configure a Git repository accessible over the filesystem.

If the Git clone is the master repository that your developers are cloning
from, then you're in good shape. However, if it's a clone of the master
repository, you will need to ensure it's consistently up-to-date. One way to
do this would be to have a cron job pull the latest changes at least once a
minute.

When using a local clone, you'll need to point the :guilabel:`Path` field to
the :file:`.git` directory within your clone. For example:
``/var/git/projectname/.git``.

The :guilabel:`Mirror Path` field should then list the URL that developers
would normally clone from. This is usually a HTTPS or SSH-backed URL. It's
important to note that you can only list one (which should not normally be a
problem if you're using RBTools_ with name-based repository lookups, which we
recommend by default).

To get the clone URL, you can run::

    $ git remote show origin

Then use the value shown in ``URL:``.

You will leave the :guilabel:`Username` and :guilabel:`Password` fields blank.
