.. _writing-good-change-descriptions:

================================
Writing Good Change Descriptions
================================

Whenever you're presenting code to other people, through a pushed commit or a
review request, it's important to ensure that your change's description
sufficiently communicates its purpose. Another person should, without ever
seeing the code or reading an associated bug report, have a clear
understanding of the problem you are solving and how you are solving it.

Writing good change descriptions is first and foremost a question of good
writing. Make sure that everything you write uses full sentences with proper
spelling and capitalization.

A good description of a commit or a review request starts in two parts: A
clear summary of the purpose of the change, and a detailed description
explaining the why/how of the change.

Review requests have one further requirement, which is to explain the testing
that was done for the change. This should provide a reader with enough
information to feel confident that your change has been thoroughly tested.

Let's go into each of these.


Writing Good Summaries
======================

A summary should be clear and concise, not cryptic. It should accurately sum
up the purpose of the change in under 80 characters (and should not wrap). It
should also be in sentence casing, with a trailing period.

It should *not* include details that could otherwise be found in the
description such as bug numbers or filenames, with very few exceptions.

When drafting a summary, try to figure out what you would verbally say to
someone if you had one sentence to explain your change.

Some examples of good summaries include:

* ``Fix rendering change descriptions without raw insert/delete counts.``
* ``Polish the look and feel of file attachment revisions.``
* ``Add a hook for extensions to register administration widgets.``

Some examples of bad summaries include:

* ``Fix bug #1234``
* ``Add a new function to MyClass.``
* ``Update path/to/file.py to fix a bug when doing XYZ.``
* ``My new feature``

These ones almost have it right, but aren't in a proper sentence style.

* ``fix a bug in the API``
* ``Add documentation for the UI...``
* ``Update The Database Schema For User Notes.``


Writing Good Descriptions
=========================

Your goal when writing a description is to leave the reader with a clear
understanding of the purpose and reason for your change, without assuming
they've already read the diff or any related bugs. This should typically be a
high-level description. Going into some details of your code is fine, but
leave the nitty-gritty to code comments.

When fixing bugs or improving features, a good pattern is to structure your
description into a "What was wrong/why" and "How it's been fixed/improved."
For instance::

    When rendering a change entry for a diff, the code attempts to get the
    total raw insert/delete line counts across all FileDiffs. If there are
    no FileDiffs for some reason, then this would end up crashing.

    We're now more careful to not assume these counts exist, and to use 0 as
    the value in this case.

Or::

    Fix absolute paths with prepare-dev.py

    A recent change to install sites into a default directory had the
    unintentional side effect of breaking prepare-dev.py. The issue was that
    using the Site object with a relative path now tries to use that path
    relative to the default directory rather than the current working
    directory.

    This change makes the relative 'reviewboard' path absolute before
    constructing the Site object.

When adding new features, you should explain the purpose of your feature,
and how it works, thoroughly. For instance::

    Add support for Kiln and FogBugz as hosting services.

    Kiln and FogBugz are services provided by Fog Creek for repository
    hosting and bug tracking, respectively. Kiln does not support any
    built-in endpoints for Mercurial file fetching, and the Git hosting is
    not compatible with the raw file URL support.

    This change adds support for working with repositories stored on Kiln,
    and for easily setting up bug tracking at FogBugz.

    The Kiln API has almost everything needed for fetching commits for the
    New Review Request page, but is just useless enough where we cannot
    provide that feature. The primary reason being that the API only allows
    paginating from the oldest commit to the newest, and not vice-versa. It
    also doesn't really allow us to start at any particular revision. So for
    now, we just have basic support.

    This also does not support Kiln repository aliases.


Writing Good Testing Information
================================

Particularly with review requests, but often with commits, it's important to
describe how you tested your change. Reviewers will feel better about the
quality of your work if they know it was tested thoroughly.

There are a lot of ways to write this. Some people like bullet points covering
all the tests they've ran. Some people like to show test output.

Whatever you do, make sure you've clearly and accurately detailed your
testing. Don't just say you've tested it. Say which tests you've tried and how
they responded. Go into as much detail as possible.

A good example would be::

    Added a unit test, which passes (along with all other tests).

    Tested with a diff containing a form feed character. Previously, it would
    turn into a newline, corrupting the diff and angering patch. After, the
    character was preserved and came along with the patch.

    Went through nearly all my local review requests containing diffs. None of
    them broke.


General Writing Tips
====================

If you haven't done a lot of writing, you're probably finding it hard to
figure out how to describe your work.


Talk out loud
-------------

One trick is to start off not by writing, but by explaining your change out
loud. Grab a friend, a family member, or a
`rubber duck <http://en.wikipedia.org/wiki/Rubber_duck_debugging>`_, and
explain to them what you're working on. By describing your change in a
different context, it can be easier to structure your thoughts and figure out
what you want in your commit message.

No kidding about the rubber duck. You don't need to speak to a living being.
Rubber ducks, teddy bears, or other inanimate objects have long been a useful
tool for working through your thoughts.


Use spell and grammar checks
----------------------------

Spell/grammar checking tools are very useful here. If in doubt, pull out Word
or some other word processor and write or copy/paste your description. Make
sure it's pretty happy with how you've written your text.
