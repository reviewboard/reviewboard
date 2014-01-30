.. _glossary:

========
Glossary
========

.. glossary::

   Context Diff
       A type of :term:`diff file` that represents changes to a file
       using before/after sections. These are not well supported by
       Review Board.

       Context diffs indicate a changed region of a file by showing
       before and after versions of a group of lines. The changed lines
       in that before and after region are indicated by beginning the
       lines with an exclamation point (``!``). Changes that only add
       lines only show one section.

   Diff File
       A file representing changes to one or more files. Common diff
       formats are :term:`unified diff`\s and :term:`context diff`\s.

   DKIM
       DomainKeys Identified Mail, a method for validating that an e-mail
       claiming to have come from a domain actually came from that domain.
       See the `Wikipedia article
       <http://en.wikipedia.org/wiki/DomainKeys_Identified_Mail>`_ for more
       information.

   Interdiffs
       An interdiff is a diff between diffs. They show what has changed
       between two versions of a diff, which is useful when making incremental
       changes to a very large diff.

   Local Sites
       One or more divisions of a Review Board site. Local sites act as
       individual Review Board sites with their own set of repositories,
       user lists, and other data, but share the same database and site
       install. This is an advanced feature.

   Markdown
       A simple markup language which allows basic formatting such as headings,
       lists, links, code blocks, and images. Many of the multi-line fields in
       Review Board use Markdown to format their contents. See `John Gruber's
       Markdown Syntax Overview
       <http://daringfireball.net/projects/markdown/>`_ for more information.

   Post-commit Hook
       A script that is executed after a commit is made to a repository.
       See :ref:`automating-post-review` for ways to use post-commit hooks
       to automate submitting review requests to Review Board.

   Post-commit Review
       A form of code review where code is reviewed after it is submitted
       to a repository, usually in a development branch.

   Pre-commit Review
       A form of code review where code is reviewed before it even goes
       into a repository. This is generally a more strict way to handle
       code review, which can lead to fewer problems in the codebase.

   Private Review Requests
       A review request that can only be accessed by users meeting certain
       criteria, such as being on an access list for a group or repository.
       See :ref:`access-control` for more information.

   Unified Diff
       A type of :term:`diff file` designed to be easy to parse and easy
       to read by humans. This is the format supported by Review Board.

       Unified diffs indicate the changed region of a file by showing some
       unchanged lines of context, then lines beginning with a minus sign
       (``-``) to show removed lines or a plus sign (``+``) to show added
       lines. Replaced lines are shown by a remove line followed by an add
       line.


.. comment: vim: ft=rst et
