.. _repository-scm-perforce:

=====================
Perforce Repositories
=====================

Review Board supports posting and reviewing code on :rbintegration:`Perforce
<perforce>` repositories. Unlike with most types of source code management
systems, Perforce tracks information around in-development changes on the
Perforce server. Review Board makes use of this information to help post
changesets for review and to indicate when a changeset has been submitted to
the repository.

Review Board supports username/password authentication or ticket-based
authentication for Perforce, and also supports connecting using SSL or
Stunnel.

To post changes for review, you will need to use RBTools_. Standard Perforce
diffs leave out a lot of important information necessary to properly identify
files, which RBTools works around. See :ref:`Using RBTools with Perforce
<rbt-post-perforce>` for more information.

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

Before you add the repository, you will need to install the p4_ command line
tool in a system path (or in a place accessible by your web server's process),
and the p4python_ package.

Installing p4_ will require registering your information on Perforce's
website. If you want to download without registering, or need a specific
version, you can use their `downloads archive`_.

To install p4python, run::

    $ pip install -U 'ReviewBoard[p4]'

You will then need to restart your web server for the new module to be
noticed by Review Board.


.. _downloads archive: https://cdist2.perforce.com/perforce/
.. _p4:
   https://www.perforce.com/products/helix-core-apps/command-line-client
.. _p4python: https://pypi.python.org/pypi/P4Python


Adding the Repository
=====================

To configure a Perforce repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Perforce` from the
:guilabel:`Repository type` field.

You will see a :guilabel:`Path` field, which should contain the value normally
used in :envvar:`P4PORT`. This can be a standard Perforce server path, or it
can be prefixed with ``ssl:`` (to use SSL encryption, if enabled by the server
and p4python), or ``stunnel:`` (to tunnel encryption to a standard Perforce
server, if :command:`stunnel` is installed).


Determining your Repository Path
--------------------------------

To determine the repository path to use, run the following inside a checkout
of your repository::

    $ p4 info

Look for the ``Server address`` field. The value listed is the path you should
use for Review Board.


Using SSL
---------

If your Perforce server listens over a SSL connection (and you're using
version 2012.1 or higher for the Perforce server), you can connect over SSL by
prefixing ``ssl:`` to the path. For example::

    ssl:perforce.example.com:1668

You can follow `Perforce's guide on enabling SSL support`_ to get started.

Note that your p4python_ module must be compiled with SSL support. This should
be the case for standard builds, but if not, you will see an error explaining
the situation. Please note that p4python is provided by Perforce, and is not
maintained by the Review Board developers.

.. _Perforce's guide on enabling SSL support:
   http://answers.perforce.com/articles/KB/2596


Using Stunnel
-------------

If you're not using a SSL-backed connection, and your Perforce server is
located in a different network, you may want to set up a Stunnel connection.
This will provide an encrypted connection between Review Board and your
Perforce server, and can be used for any version of Perforce.

To start, please follow `Perforce's guide on using Stunnel`_. This will take
care of the configuration on the Perforce server.

You will then need to install Stunnel_ on the Review Board server. Review
Board 2.0.23+/2.5.4+ support Stunnel version 3 and 4, while earlier versions
of Review Board require Stunnel version 3. The :command:`stunnel` binary must
be in the web server's path.

You can then configure your repository path to point to your Stunnel proxy. To
do this, just prefix your standard repository path with ``stunnel:`` and list
the port that the Stunnel server is running on. Review Board will take care of
the rest.

For example, if Stunnel is listening on port 2666, you can use::

    stunnel:perforce.example.com:2666

Review Board will automatically set up a local tunnel client as necessary.
It will bind this to a port between 30000 and 60000 on localhost, and proxy
all requests through it.


.. _Perforce's guide on using Stunnel:
   http://kb.perforce.com/article/1018/using-stunnel-with-perforce
.. _Stunnel: https://www.stunnel.org/index.html


Using Ticket-Based Authentication
=================================

Review Board supports using ticket-based authentication for Perforce. To
enable this, simply provide the credentials for the Perforce user you want
Review Board to use and then check :guilabel:`Use ticket-based
authentication`.

Review Board will handle storing the ticket information and requesting new
tickets when necessary. You don't have to do anything else.
