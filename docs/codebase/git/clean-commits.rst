.. _clean-commit-histories:

==============================
Keeping Commit Histories Clean
==============================

When maintaining a branch of commits, it's always best to keep a clean commit
history where possible. Git gives you the tools you need for this, and this
guide will help you learn how to use them.


What Is A Clean History?
========================

A clean commit history is one where each commit is a solid piece of work,
representing a milestone in your feature or fix. This might be the backend
for some part of the feature, or a component of the UI. It doesn't have to be
a large amount of work, just some good chunk that, conceptually, stands alone.

An unclean commit history is often littered with commits like "Fixed a bug
in my previous commit" or "Oops, forgot this file" or "rewrite that class
again for the 3rd time."

Ideally, you should strive for a series of commits that almost reads as a
story of how your feature came together.

A good example of a clean commit history is::

   * Added the models and forms for potatoes.
   * Added the API for interacting with potatoes, along with unit tests.
   * Added the comment dialog for reviewing potatoes.

An example of an unclean commit history is::

   * Added the models and forms for potatoes.
   * Decided the is_spud field wasn't necessary and removed it.
   * Forgot forms.py.
   * Added the API for interacting with potatoes, along with unit tests.
   * One of the tests failed, fixed it.
   * Added the comment dialog for reviewing potatoes.
   * Fixed a typo.
   * Another typo.

Now, some degree of "Oops" commits tends to happen, but the goal is to
minimize this. If your commits are all local to your checkout, with nothing
pushed to any other repository, you can make this happen using the tricks
in this guide.


Tools
=====

gitk and gitx
-------------

The best way to keep tabs on your repository is to use a graphical
Git repository viewer. Git comes with :command:`gitk`, which should be
invoked from within your checkout like::

    $ gitk --all &

This will show you your current branch in bold, and the entire history
of commits. It's a bit hard to read at first, with merges happening,
but it's better than working in your tree blind.

gitx_ is another alternative, if you use MacOS X.

.. _gitx: http://gitx.frim.nl/


Branches
========

Backing Up Branches
-------------------

Some of the tricks in this guide will change your actual commit history,
which can cause you to lose commits if you're not careful. While you often
can get your commits back, it's a bit of extra work.

If you're about to try something that will change history, you can keep
a "backup" of those commits by creating a branch or tag at the HEAD of your
branch. You can then switch back to your feature branch and then perform
the operation.

This will result in two branches, one with the newly revised history,
and one with the original. When you're happy with your new history,
you can just delete the backup branch.


Know Where To Commit
--------------------

Your work should always be done on a branch of your own, and never an upstream
branch. This means you should never make a commit on ``master`` or any
other branch with the same name as an origin branch. Instead, create your
own with a specific name of your choosing.

Committing to ``master`` or another upstream branch and then pushing to your
GitHub is the easiest way to complicate things and break your checkout.


Good Branching Naming
---------------------

Part of keeping things maintainable is making sure your branches and names are
clear and organized. A branch name should clearly describe the feature or
fix you are working on.

The following are good examples of branch names:

* ``file-attachment``
* ``ui-rewrite``
* ``search-api``

And the following are bad:

* ``my-work``
* ``enhancements``
* ``bugfix``

Now, it should be clear that when we talk about good branch names, it's
primarily important if that branch is ever going to be exposed to the world,
such as on your GitHub clone. If it's a very temporary branch, by all means
call it whatever you like, but it's still best to practice good naming.

Another trick is to organize your branch names through ``/``-separated
"namespaces." This just means naming the branch in the form of
``feature/specific-task``. For example:

* ``file-attachment/webapi``
* ``file-attachment/ui-redesign``
* ``search/webapi``


One Branch Per Review Request
-----------------------------

A review request is typically tied to a branch. When running
:command:`post-review`, a review request will be generated from ``master``
to the HEAD of your branch.

If you're doing work based on code sitting in a branch that is up for
review, you should create a new branch for that block of work, rather than
reusing the existing branch.


Working with Commits
====================

Writing Clear Commit Messages
-----------------------------

Anyone looking at your commits should be able to easily determine what a
commit accomplished and why it was made. To ensure this, make sure every
commit message is clear and readable.

A good commit message is in the following form::

    Summary (less than 80 characters)

    Multi-line description

Your summary should be brief but should clearly summarize what the commit
was for. An example may be "Implemented the API for file attachments."

Your description should be detailed, describing what changes you made and
how they work. While it shouldn't be massively long, it should cover the
high points of the change, and perhaps why you did what you did (if you
think it could be confusing).

If there are any known problems you still intend to fix at the time of commit,
that would be a good place for them. It can even help you later as a To Do
when you're amending_ or `rewriting history`_.

See also :ref:`writing-good-change-descriptions` for more details, with
examples.


Committing Only Parts of Changes
--------------------------------

It's common to make more than one set of changes to a file before you commit,
possibly as you're testing code or as you hit other regressions. These
changes may all be mixed in the same set of files, but that doesn't mean
you have to commit them all at once.

Git makes it easy to commit only parts of your changes. This is "Patch
Adding." Simply type::

    $ git add -p <filename>

This will start going through all the individual changes made to the file,
asking if you want to stage each for commit.

There are a few handy keys you'll want to learn.

* :kbd:`y` -- Stage the change for commit
* :kbd:`n` -- Skip it and leave it out of the commit
* :kbd:`s` -- Split the chunk you're looking at into smaller chunks,
  if possible.
* :kbd:`e` -- Edit the actual diff. Useful for getting rid of debug output.
* :kbd:`q` -- Quit processing the rest of the changes. This is equivalent to
  saying :kbd:`n` to everything remaining.

There are other keys as well. You can check ``git help add`` for more.

If you're going to be patch adding a bunch of files for one commit, you can
leave off the filename above::

    $ git add -p

Git will loop through each modified file and begin the process for each.


.. _amending:

Amending the Previous Commit
----------------------------

If you have just made a commit, and then realized you needed to fix something
in it, you can stage your files and amend it to your previous commit.

To do this::

    $ git commit --amend

It will bring up your previous commit message in an editor and then update
that commit with the staged changes.

.. note::

   You can only amend if the commit you're amending into has not been
   pushed to another repository. It must be local only to your checkout,
   or you will end up breaking your history.

   If you have already pushed the previous change, you will have to
   create a new commit for this fix.


.. _`rewriting history`:

Rewriting History
-----------------

One of the most powerful ways to clean up your history is to use
interactive rebasing. This is a way to take a history of commits and
quickly dispose of some, or merge them together, or reorder them. It's
a powerful tool, and one that can bite you if you're not careful, but
is well worth knowing.

To start this out, you want to run::

    $ git rebase -i <parent>

Where ``<parent>`` is some parent branch or commit. Everything between
that branch/commit and HEAD will be included in the rebase list. (It's
important to note that that parent itself won't be included.) Often,
the parent will be ``master``.

After typing this, your editor will come up with a list of the commits
in order. There will be some helpful instructions in there, but basically,
each line will have an operation and a commit summary. By changing the
operations or reordering/deleting lines in the editor, you'll be changing
the commit history.

A good way to clean up history is to keep your "fixed blah blah" commits
simple, run ``git rebase -i <parent>``, and then move your fix commit
below the commit it'll be fixing, and change the operation to ``squash``
or ``fixup``.

``squash`` will merge the commit with the one above it and allow you to
change the commit message (by default, both of the commits will have their
messages combined).

``fixup`` will merge the commit with the one above it, but use the above
commit's message. This is a bit faster to work with. Note that ``fixup``
is a more recent addition and you may need a newer version of Git,
depending on what your repository ships.

.. note::

   Like with amending commits, you can only change commits that have not
   been pushed. Otherwise, you will complicate things for you and anyone
   following your pushed branch.

   It's best to look at your branch in :command:`gitk` before deciding whether
   it's safe to do an interactive rebase.


Merging and Rebasing
--------------------

Git has two ways of staying up-to-date with other branches: merging, and
rebasing.

A merge takes a set of changes from the source branch and moves them into
your current branch, as a special commit. This commit generally includes
a commit message such as "Merge branch 'master' into foo". It works like::

    $ git checkout my-branch
    $ git merge master

A rebase takes your current branch and rebuilds it on top of the source
branch, effectively rewriting history (like the interactive rebase above).
It works like::

    $ git checkout my-branch
    $ git rebase master

The advantage of a rebase over a merge is that you won't get those extra
merge commits in your branch, cluttering things up. In general, if you have
a new branch with a few commits, you may want to do a rebase.

However, there are a couple reasons you would want a merge over a rebase.
A rebase will break things if the commits were already pushed, so you can
only rebase unpushed commits. Also, it can be harder to resolve conflicts if
your branch is old and a lot has changed in the branch you're rebasing onto.

One strategy is to use rebasing until you do your initial push. After that,
you will want to always merge.

Don't merge too often though. If you merge frequently, you'll just clutter
your branch with merge lines. It's best to merge either when you're dependent
on a change that just went in, or you're about to post your branch for
review.


Remote Repositories
===================

When To Push
------------

When dealing with a remote repository, such as a GitHub fork, you should
be careful when you decide to push. Once you push a commit, there's no
going back. You can't amend it, or rewrite it, or delete it. Therefore,
you should always push only when you're satisfied with the history of the
commits you're pushing.

That isn't to say that you won't find flaws in your commits that you wish
you could fix. That is bound to happen. However, by ensuring the history
is clean before you push, you will find it easier to reduce the number
of spurious commits in your branch.
