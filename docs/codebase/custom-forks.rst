.. _maintainingcustomforksofreviewboard:

========================================
Maintaining Custom Forks of Review Board
========================================

There are times when it's necessary to maintain a custom copy, or "fork,"
of Review Board. Contributors may have a custom fork containing development
branches that they can access from multiple locations or share with others.
Companies may need a custom version with custom functionality that ties into
their infrastructure better.

This document will serve as a guide for creating and maintaining custom
forks. It's geared toward developers and organizations that want to maintain
a fork accessible by other developers, either publicly or in the organization.
Part of the advantage of doing this is redundancy. One copy could exist on
a central server, and one would exist on the developer systems, preventing
an entire loss of the fork if one of those copies was lost.

If only one developer will ever be working with the codebase, and you have
no need for a central fork in the organization, you can just use a single
checkout as described in :ref:`getting-started`.

If you maintain a fork and have code that you think would be useful to
the project as a whole, we would appreciate that you contribute the code
back to the project.


Creating Forks
==============

Forking Review Board is just a matter of cloning the repository and putting
it somewhere. If your changes are able to be publicly accessible, then you
can use GitHub for this. Otherwise you can just store the repository on
a server in your network, accessing it over SSH or the Git protocol.


Using GitHub
------------

GitHub_ is a popular Git hosting service, and is the one the Review Board
project uses to host Review Board, Djblets, and more. GitHub_ makes it
very easy to create and maintain a fork.

First, you'll need an account on GitHub, which your fork will be
associated with.

Then go to the page for the repository you want to fork. These can be
found at https://github.com/djblets/ and https://github.com/reviewboard/.
The most common repositories are reviewboard_, rbtools_, and djblets_.

Once you are on the desired repository page, click the :guilabel:`fork`
button. This will create a copy of the repository under your name, ready
to check out and use.

You can now check out your fork. However, rather than check it out directly,
you'll want to check out the upstream repository and create a "remote" to
your fork. The reason for this is that you will, on occasion, want to pull
from the upstream repository into your fork, and for this your checkout needs
to know about both.

The following example assumes you're forking the reviewboard_ repository
and creating a remote called ``REMOTE_NAME``. You can name this whatever
you want. You may want to use your username as the remote.

You would type::

    $ git clone git://github.com/reviewboard/reviewboard.git
    $ cd reviewboard
    $ git remote add REMOTE_NAME git@github.com:YOUR_USERNAME/reviewboard.git
    $ git fetch REMOTE_NAME


.. _GitHub: https://github.com/
.. _reviewboard: https://github.com/reviewboard/reviewboard/
.. _rbtools: https://github.com/reviewboard/rbtools/
.. _djblets: https://github.com/djblets/djblets/


Using a Custom Solution
-----------------------

There are many ways to host an internal Git repository. This guide won't
go into too many details on this subject.

To prepare your fork, you will need to first know the public clone URL from
the repository you want to clone. These can be found at
https://github.com/djblets/ and https://github.com/reviewboard/.  The most
common repositories are reviewboard_, rbtools_, and djblets_.

You will then want to clone this repository and host it on Gitosis or another
internal hosting service. Once you have done that, you can set up a clone
of the upstream project and add your new fork as a remote.

The following example assumes you're forking the reviewboard_ repository
and creating a remote called ``REMOTE_NAME`` at ``REMOTE_URL``. You can name
the remote whatever you want.

You would type::

    $ git clone git://github.com/reviewboard/reviewboard.git
    $ cd reviewboard
    $ git remote add REMOTE_NAME REPOTE_URL
    $ git fetch REMOTE_NAME


Keeping the Fork Updated
========================

When maintaining a fork, it's important to keep it up-to-date with the
latest upstream changes. This is pretty easy to do. Simply type::

    $ git checkout master
    $ git pull
    $ git push REMOTE_NAME master

If you want to post changes on your branch to the fork for others to use,
type::

    $ git checkout branch-name
    $ git push REMOTE_NAME branch-name
