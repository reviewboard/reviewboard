.. _managing-default-reviewers:
.. _default-reviewers:

=================
Default Reviewers
=================

The Default Reviewers list provides a way to automatically add certain users
or groups to the reviewer lists on new review requests, depending on the paths
of the files modified in the diff.

This is most useful when particular :ref:`review groups <review-groups>` own
parts of the tree.


.. _adding-default-reviewers:

Adding Default Reviewers
========================

To add a new default reviewer, click the "Add" link next to the
"Default reviewers" entry in the
:ref:`database section <database-management>` or the
:ref:`administrator-dashboard` in the
:ref:`Administration UI <administration-ui>`.

A form will appear with the following fields:

* **Name** (required)
    A name describing this default reviewer. This won't be shown to users.

.. _`File regex`:

* **File regex** (required)
    A "regular expression" defining the file path. This is way of specifying
    patterns to match strings.

    See `Regex Pattern Matching`_ for more information.

* **Default groups** (optional)
    One or more review groups that should be automatically added to a review
    request when the `File regex`_ matches a file in the diff.

    The list contains possible review groups to match. Selected entries
    are the groups you want to add. Hold down :kbd:`Control` (on the PC) or
    :kbd:`Command` (on the Mac) to select more than one.

    At least one group or one user should be selected for this default
    reviewer entry to be useful.

* **Default people** (optional)
    One or more groups that should be automatically added to a review request
    when the `File regex`_ matches a file in the diff.

    The list contains possible users to match. Selected entries are the users
    you want to add. Hold down :kbd:`Control` (on the PC) or :kbd:`Command`
    (on the Mac) to select more than one.

    At least one group or one user should be selected for this default
    reviewer entry to be useful.

* **Repositories** (optional)
    A default reviewer can be limited to one or more repositories. This is
    particularly useful when operating a Review Board server with many
    repositories ran by separate groups.

    Hold down :kbd:`Control` (on the PC) or :kbd:`Command` (on the Mac)
    to select more than one repository.

    If no repositories are selected, then this default reviewer will apply to
    every repository.


.. _editing-default-reviewers:

Editing Default Reviewers
=========================

To edit a default reviewer, click "Default reviewers" in the
:ref:`administrator-dashboard` or
:ref:`Database section <database-management>` of the
:ref:`Administration UI <administration-ui>`.
You can then browse to the default reviewer you want to modify and click it.

See :ref:`adding-default-reviewers` for a description of each field.

When done, click :guilabel:`Save` to save your changes.


Deleting Default Reviewers
==========================

To delete a default reviewer, follow the instructions in
:ref:`editing-default-reviewers` to find the default reviewer you want to get
rid of. Then click :guilabel:`Delete` at the bottom of the page.


Regex Pattern Matching
======================

Regular expressions (or "regexes") provide a way to match potentially complex
strings of text. In this case, file paths.

A regular expression contains a mix of the text you want to match and special
characters defining the pattern. Some of the more important concepts are
described below:

* **Matching any number of characters**
    To match any number of characters, you can use ``.*`` or ``.+``.
    The period (``.``) means to match a single character. The asterisk
    (``*``) means to match zero or more characters. The plus (``+``) means
    to match one or more characters.

    This will often be used at the end of a directory hierarchy, if you
    want to match on every file or directory inside that directory.

    For example::

        /trunk/project1/src/.*

* **Matching multiple possible strings**
    To match one or more possible strings (such as two possible directory
    names in a patch), you can place parenthesis around the text and separate
    the possible matches with a ``|``.

    For example::

        /trunk/(project1|project2)/src/.*

* **Matching a period**
    Periods are special characters in regular expressions. They match
    1 single character, any character. To actually match a period, you
    can escape it with a backslash, as follows: ``\.``

    For example::

        /trunk/project1/src/*\.c

More operators can be found in the `Python Regular Expression HOWTO`_.
The above is all that's generally needed for file paths, though.


.. _`Python Regular Expression HOWTO`:
   https://docs.python.org/2/howto/regex.html
