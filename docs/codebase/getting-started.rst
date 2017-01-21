.. _getting-started:

===============
Getting Started
===============

This guide will serve as a basic introduction to installing Review Board
for development purposes. These steps have been tested on Linux and on
MacOS X.

The methods in this guide should not be used to install Review Board for
production use or on a production server. It certainly should not be used
with a production database. We recommend installing Review Board on a
separate development system. You can still build Review Board packages from
the development version and install them on a production system, if you
feel comfortable.


Installation
============

MacOS X Requirements
--------------------

If you're on MacOS X, you'll want to make sure you have XCode installed. This
will provide some essential tools, such as Git and patch.


Virtualenv
----------

We recommend using virtualenv_ for your development. virtualenv is a tool
that sandboxes a Python project, allowing you to easily install packages
without impacting your system packages. It's especially handy when you want to
test different configurations with different versions of packages or Python.

First, install virtualenv::

    $ sudo pip install virtualenv

You can then create your first Review Board environment. Choose a spot for it.
In this guide, we'll assume this is in :file:`~/envs`. Then type::

    $ virtualenv ~/envs/reviewboard

You can name the environment anything you want. One scheme is to have a name
per-release. So, instead of ``reviewboard`` above, maybe ``rb-master`` or
``rb2.5``. This is up to you.

From then on, before doing any Review Board development, you'll want to switch
to this environment::

    $ source ~/envs/reviewboard/bin/activate

Note that once you're in your environment, you don't need to install packages
as root. So, no need for :command:`sudo`.

.. _virtualenv: https://pypi.python.org/pypi/virtualenv


Dependencies
------------

Before we begin setting up Review Board, it's best to walk through the
installation instructions in the `Administration Guide`_. The mandatory
Python modules you'll need for development will be installed automatically
later. For now, you'll need to install the following packages from your
system's package manager:

* gettext
* git
* npm
* patch
* pysvn

Also install any tools for repository types that you may want to use.

You will **not** need to install the Djblets and ReviewBoard packages, as
we'll be doing that in a moment.

Typically on development setups, SQLite is used for the database, as this
allows for quick and easy database creation, backups, multiple versions,
and deletions.

Apache and lighttpd are usually not used. Review Board contains a built-in
single-threaded web server that can be tested against. Unless you're doing
development work that requires a real web server, don't bother setting one
up for this.

memcached can be handy, so install that if you want to, but by default we're
going to use the built-in local memory cache. This is a temporary cache that
will persist only as long as the development web server is running.

gettext is needed if you're going to be building the documentation or
packages. On OS X, gettext is available through homebrew or fink.

.. _`Administration Guide`: https://www.reviewboard.org/docs/manual/latest/admin/


Djblets
-------

Review Board requires the bleeding-edge version of Djblets. This is
hosted on GitHub_, and you can `browse the Djblets repository
<https://github.com/djblets/djblets>`_ and see details there.

First, find a nice place where the :file:`djblets` source directory will live
(such as :file:`~/src/`) and type the following::

    $ git clone git://github.com/djblets/djblets.git

This will download the latest bleeding-edge build of djblets into the
:file:`djblets` directory.

Now to prepare that copy for development use, type the following::

    $ cd djblets
    $ python setup.py develop
    $ pip install -r dev-requirements.txt

This will create a special installation of Djblets that will reference
your bleeding-edge copy. Note that this version will take precedence on
the system.


.. _GitHub: https://github.com/
.. _browse-djblets: https://github.com/djblets/djblets


Review Board
------------

Review Board installation is very similar to Djblets. It too is hosted
on GitHub_, and you can `browse the Review Board repository
<https://github.com/reviewboard/reviewboard>`_.

Go back to your source directory and check out a copy of Review Board::

    $ git clone git://github.com/reviewboard/reviewboard.git

This will download the latest bleeding-edge build of Review Board into the
:file:`reviewboard` directory.

You will not need to perform a system installation of this package. Instead,
there's a Python script that will prepare your source directory for
development use. You will need to run this::

    $ cd reviewboard
    $ python setup.py develop
    $ python ./contrib/internal/prepare-dev.py

If all went well, you will see "Your Review Board tree is ready for
development." Congratulations. You are now ready to start developing
Review Board.


RBTools
-------

You will need the latest version of RBTools for development.

Like Djblets and Review Board, you can find RBTools on GitHub_, and you can
`browse the RBTools repository <https://github.com/reviewboard/rbtools>`_.

Go back to your source directory and check out a copy of RBTools::

    $ git clone git://github.com/reviewboard/rbtools.git

This will download the latest bleeding-edge build of RBTools into the
:file:`rbtools` directory.

We highly recommend installing RBTools onto your system, since you will actively
use it to post code up for review. If you just want to develop rbtools, you can
set that up using this command::

    $ python setup.py develop

If you want to install RBTools onto your system, use::

    $ python setup.py install

This should install a system package of RBTools, ready to use. If you make
any changes that you want to test later on, you will need to re-run this
command.


Keeping Things Updated
======================

Every so often, you will need to update to the latest versions of Djblets and
Review Board. This is done by going into the source tree and downloading the
latest changes into the ``master`` branch. For example, to update Djblets,
type::

    $ cd djblets
    $ git checkout master
    $ git pull

You'll do the same with Review Board.


Beginning Development
=====================

In Git, development is done in a lightweight branch. These can be easily
created, updated, and thrown away whenever needed. You can have as many of
these branches as you need. They can be merged into other custom branches,
updated with the latest Review Board changes, or even be based on experimental
upstream branches.


Setting up Git
--------------

Before you make your first commit, you'll want to configure Git with your
name and e-mail address. These will be used in your commits.

Type the following, substituting your name and e-mail address::

    $ git config --global user.name "FULL NAME"
    $ git config --global user.email emailaddress@example.com


Creating Branches
-----------------

To create a branch based on the upstream ``master`` branch, type::

    $ git checkout -b new-branch master

This will create a branch called ``new-branch``. You can do all your
development on here.

If instead you want to base this on a different branch, put that branch's
name in place of ``master`` above. For example, to base something on
the upstream ``release-2.0.x`` branch, you might type::

    $ git checkout -b new-branch release-2.0.x


Switching Branches
------------------

Switching branches is done with the :command:`git checkout` command.
Simply type::

    $ git checkout branch-name

This will switch your existing tree to the files on ``branch-name``.


Making Changes
--------------

In Git, your local repository is yours to play with. You can commit code
to any branch without affecting upstream. Usually it's best to limit this
to branches intended for custom development, and never to the ``master``
branch.

This means you can commit as many changes as you want to a branch before
posting it up for review, which is really beneficial for large changes.

Before committing, you need to "add" the file(s) you want to commit. This
is necessary even for existing files. For example::

    $ git add views.py models.py

Once the files are added, you can commit them::

    $ git commit

This will open your editor and ask for a change description. Once you've
provided one and quit your editor, your change will be committed.

As a shortcut, if you want to commit changes to every file you've modified,
you can type::

    $ git commit -a

This has the effect of running :command:`git add` on every file you modified
that exists already in the repository (including new files you added
previously in that branch).


Updating from Upstream
----------------------

Over time, and especially before you're ready to post your change for
review, you will want to update it with the upstream changes on ``master``.
First, update ``master`` itself::

    $ git checkout master
    $ git pull

Next, rebase your branch onto master::

    $ git checkout new-branch
    $ git rebase master

This will rebase your branch to be based on the latest code in master. If you
have any conflicts to resolve, Git will list them. For each conflict, you will
need to edit the file, find the ``<<<<<``, ``=====``, ``>>>>>`` lines, and fix
fix them. Once each conflict is resolved, :command:`git add` the file. When
you're done, you can continue the rebase::

    $ git rebase --continue

You may have to resolve conflicts multiple times if you have many commits on
your branch.


Updating your Database
----------------------

From time to time, we make changes to the schema for the database. You'll
notice this if Review Board suddenly breaks, saying ``no such column`` or
``no such table``.

To update your database, run::

    $ ./reviewboard/manage.py syncdb
    $ ./reviewboard/manage.py evolve --execute

This will apply the database schema migrations to your database.

If you're writing a change that needs to modify the database, you'll want
to see :ref:`database-evolutions`.


Testing Data
------------

A newly created instance of Review Board is pretty bare. Oftentimes, it is
useful to have some review requests, reviews, and other users set up in your
local instance to test against. Thankfully, there's a handy utility available
to create those things for you.

To create a new user and insert 5 review requests for them, run::

    $ ./reviewboard/manage.py fill-database --users=1 --review-requests=5

You can also make it so that there are diffs attached to each review request::

    $ ./reviewboard/manage.py fill-database --users=1 --review-requests=5 --diffs=2

You can also have automated reviews created for those review requests::

    $ ./reviewboard/manage.py fill-database --users=1 --review-requests=5 --diffs=2 --reviews=2

To see a full list of what fill-database can generate for you, run::

    $ ./reviewboard/manage.py fill-database --help


Additional Tips
---------------

There is a *lot* that Git can do, and this guide isn't going to attempt to
cover anything but the basics. It's highly recommended that you do some
reading to get the most out of Git. A good start is the `GitHub Guides`_.

Some people find it helpful to use a graphical repository viewer. Git ships
with :command:`gitk`, which works decently (run with the ``--all`` parameter).
MacOS X uses may want to try `GitX`_.


.. _`GitHub Guides`: https://github.com/guides/home
.. _GitX: http://gitx.frim.nl/


Testing Changes
===============

.. _development-web-server:

Development Web Server
----------------------

Review Board ships with a script that launches Django's built-in
single-threaded web server. While useless in production environments, this
server is great for development and debugging. All page requests are viewed
in the console that launched the server, as well as any debug printing or
logging output.

To launch the web server, run::

    $ ./contrib/internal/devserver.py

This will start the server on port 8080. You should then be able to access
your server by visiting ``http://localhost:8080``.

If you need to use a different port, you can use the ``-p`` parameter.
For example::

    $ ./contrib/internal/devserver.py -p PORT_NUMBER

Specify the port you want to use in ``PORT_NUMBER`` above.


Running Unit Tests
------------------

.. note::

   This section has moved. See :ref:`running-unit-tests`.


Posting Changes for Review
==========================

Before you post a change for review, make sure your branch is based on
the upstream ``master`` branch.

When you're ready to post the changes on a branch for review, you can
just run :command:`rbt post`, which you should have if you installed
RBTools above::

    $ rbt post

This will use your commit message as the base for the review request's Summary
and Description fields.

If you want to update an existing review request, use the ``-u`` parameter::

    $ rbt post -u

If it can't find your review request (which would happen if you changed your
summary and description), then you will need to use ``-r <ID>`` instead::

    $ rbt post -r 42

See our guidelines on :ref:`contributing-patches` for more information.
