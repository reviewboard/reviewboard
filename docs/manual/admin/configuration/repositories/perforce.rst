.. _repository-scm-perforce:

=====================
Perforce Repositories
=====================

Review Board supports posting and reviewing code on :rbintegration:`Perforce
<perforce>` repositories.

Perforce is widely used by large software and hardware companies. Unlike many
source code management products in this space, Perforce keeps track of all
changes that are in progress, including their pending change descriptions.
Review Board makes use of this information to help post changesets for review
and to indicate when a changeset has been submitted to the repository.

Review Board supports username/password authentication or ticket-based
authentication for Perforce, and also supports connecting using SSL or
Stunnel.

.. note::

   This guide assumes that you're adding a Perforce repository that's hosted
   somewhere in your network or one that's accessible by your Review Board
   server. Review Board requires local or network access to your repository.

   Follow the documentation in the links below if your Perforce repository is
   hosted on one of these services, as configuration may differ.

   * :ref:`Assembla <repository-hosting-assembla>`


.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing Perforce Support
===========================

Before you add the repository, you will need to install the following:

1. The p4_ command line tool.

   This must be placed in your web server's system path, and must be
   executable by the web server.

2. The p4python_ bindings.

   This can be installed by running:

   .. code-block:: console

        $ pip3 install -U 'ReviewBoard[p4]'

   You will then need to restart your web server for the new module to be
   noticed by Review Board.


.. _p4: https://www.perforce.com/downloads/helix-command-line-client-p4
.. _p4python: https://pypi.org/project/p4python/


Adding the Repository
=====================

To configure a Perforce repository:

1. :ref:`Add a new repository <adding-repositories>` and select
   :guilabel:`Perforce` from the :guilabel:`Repository type` field.

2. Set the :guilabel:`Path` field to the Perforce server.

   This is a standard Perforce :envvar:`P4PORT` value. It may optionally
   include a ``ssl:`` prefix (for :ref:`SSL connections
   <repository-scm-perforce-repo-path>`) or ``stunnel:`` (for
   :ref:`stunnel connections <repository-scm-perforce-repo-path>`).

   See :ref:`repository-scm-perforce-repo-path`.

3. Configure a :term:`Perforce standard user` account for repository
   configuration.

   See :ref:`repository-scm-perforce-config-user` and
   :ref:`repository-scm-perforce-ticket-based-auth`.

4. Save the repository.

   If using SSL, this may ask you to verify the certificate.

If you have any trouble configuring the repository, you can
`reach out to us for support <support_>`_.


.. _support: https://www.reviewboard.org/support/


.. _repository-scm-perforce-repo-path:

Determining your Repository Path
--------------------------------

To determine the repository path to use, run the following inside a checkout
of your repository:

.. code-block:: console

    $ p4 info

The ``Server address`` field contains the value to use for the repository
path in Review Board.


.. _repository-scm-perforce-ssl:

Using SSL
---------

Modern versions of Perforce (2012.1 or higher) natively support SSL
connections.

If your Perforce server listens over a SSL connection, you can connect by
prefixing ``ssl:`` to the path. For example::

    ssl:perforce.example.com:1668

Follow `Perforce's guide on enabling SSL support`_ to get started.


.. _Perforce's guide on enabling SSL support:
   https://portal.perforce.com/s/article/2596


.. _repository-scm-perforce-stunnel:

Using Stunnel
-------------

If you're not using a SSL-backed connection, and your Perforce server is
located in a different network, you may want to set up a Stunnel connection.
This will provide an encrypted connection between Review Board and your
Perforce server, and can be used for any version of Perforce.

To use Stunnel:

1. Follow `Perforce's guide on using Stunnel`_. This will take care of the
   configuration on the Perforce server.

2. Install Stunnel_ 3 or higher on the Review Board server.

   The :command:`stunnel` binary must be in the web server's path.

3. Configure your repository path to point to your Stunnel proxy.

   To do this, prefix your standard repository path with ``stunnel:`` and
   list the port that the Stunnel server is running on. Review Board will take
   care of the rest.

   For example, if Stunnel is listening on port 2666, you can use::

       stunnel:perforce.example.com:2666

Review Board will automatically set up a local tunnel client as necessary.
It will bind this to a port between 30000 and 60000 on localhost, and proxy
all requests through it.


.. _Perforce's guide on using Stunnel:
   https://portal.perforce.com/s/article/2431
.. _Stunnel: https://www.stunnel.org/


.. _repository-scm-perforce-config-user:

Choosing a Perforce User
------------------------

Review Board communicates with your Perforce repositories using a single
Perforce user.

This user must meet the following criteria:

1. The user must be a :term:`Perforce standard user`.

   :term:`Perforce service users` and :term:`Perforce operator users` are not
   supported. Both are restricted to a subset of Perforce commands used for
   Perforce management tasks. The commands required by Review Board to access
   the contents of files in depots are not available to these users.

   Granting a service user or operator user the "super" permission does not
   change this.

   See the `p4 user`_ documentation for the differences between types of
   users.

2. The user must have read access to all depots used on Review Board.

   This is required in order for Review Board to fetch file contents and
   generate diffs.

   If the user does not have access to a given depot, people will not be
   able to post changes on that depot for review.

3. It must be allowed to invoke the following commands:

   * ``p4 change``
   * ``p4 describe``
   * ``p4 fstat``
   * ``p4 info``
   * ``p4 login``
   * ``p4 print``

You can either create a dedicated user for Review Board, or you can use an
existing user that meets all the necessary criteria.


.. _p4 user:
   https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_user.html


.. _repository-scm-perforce-ticket-based-auth:

Using Ticket-Based Authentication
---------------------------------

Review Board supports using ticket-based authentication for Perforce. To
enable this:

1. Provide the credentials for the Perforce user, as normal.

2. Enable :guilabel:`Use ticket-based authentication` in the Review Board
   repository configuration.

Review Board will handle storing the ticket information and requesting new
tickets when necessary. You don't have to do anything else.


.. _repository-scm-perforce-trigger-script:

Installing the Trigger Script
=============================

We provide a `trigger script`_ for your Perforce server, which does the
following:

* Checks that submitted changes are put up for review and approved, blocking
  them if they fail these checks.

* Automatically closes review requests once changes are submitted.

We recommend this for all Perforce users.

To install the trigger script:

1. `Install RBTools`_ and the Perforce command line tools on the Perforce
   server.

   .. important::

      Make sure that :command:`rbt` and :command:`p4` are in the system path
      used by the Perforce server.

2. `Download the trigger script <trigger script_>`_ and place it where the
   Perforce server can run it.

3. Set the options in the downloaded trigger script to match your environment.

   There are instructions within the file for each option. These will be
   entirely dependent on your setup.

   You can also choose which checks to activate and which actions to perform.

4. Run :command:`p4 triggers` and add the trigger script:

   .. code-block:: shell

      reviewboard change-submit //depot/... "/path/to/python /path/to/p4-trigger-script %changelist%"

   Customize the Python executable path, depot path, and the path to the
   trigger script above.

   .. tip::

      Make sure your Python executable path is the same environment in which
      RBTools was installed.

      If you're installing on Windows and using the `RBTools for Windows
      installer`_, your Python path should be::

          C:\Program Files\RBTools\Python\python.exe

You should now be up and running!

If you have any trouble configuring the trigger script, you can
`reach out to us for support <support_>`_.


.. _trigger script:
   https://raw.githubusercontent.com/reviewboard/rbtools/master/contrib/tools/p4-trigger-script
.. _Install RBTools: https://www.reviewboard.org/downloads/rbtools/
.. _RBTools for Windows installer:
   https://www.reviewboard.org/downloads/rbtools/


Posting Changes for Review
==========================

To post changes for review, you will need to use RBTools_. Standard Perforce
diffs leave out a lot of important information necessary to properly identify
files, which RBTools works around.

See :ref:`Using RBTools with Perforce <rbtools-workflow-perforce>` for more
information.
