:orphan:

.. _glossary:

========
Glossary
========

.. glossary::

   CI
   Continuous Integration
       A development process where commits are integrated frequently, and
       automated builds and tests are triggered for each commit.

   Context Diff
       A type of :term:`diff file` that represents changes to a file
       using before/after sections. These are not well supported by
       Review Board.

       Context diffs indicate a changed region of a file by showing
       before and after versions of a group of lines. The changed lines
       in that before and after region are indicated by beginning the
       lines with an exclamation point (``!``). Changes that only add
       lines only show one section.

   Cumulative Diff
       A diff that represents a squashed set of commits, each of which has
       their own diffs. It is equivalent to applying all of the diffs for all
       the commits in order.

   Default Reviewer
   Default Reviewers
       A feature that allows individual ussers or :term:`review groups` to be
       automatically assigned as reviewers to a review request based on the
       repository or files being modified.

   Diff File
       A file representing changes to one or more files. Common diff
       formats are :term:`unified diff`\s and :term:`context diff`\s.

   DKIM
       DomainKeys Identified Mail, a method for validating that an e-mail
       claiming to have come from a domain actually came from that domain.
       See the `Wikipedia article
       <https://en.wikipedia.org/wiki/DomainKeys_Identified_Mail>`_ for more
       information.

   DMARC
       Domain Message Authentication, Reporting & Conformance. This is an
       e-mail standard for specifying policies around e-mail sender
       validation, allowing spoofed/malicious e-mails to be rejected or
       quarantined, amongst other capabilities. See the
       `Wikipedia article <https://en.wikipedia.org/wiki/DMARC>` and the
       official `DMARC website <https://dmarc.org/>` for more information.

       Review Board checks DMARC rejection/quarantine policies before
       attempting to send e-mails on behalf of users. See :ref:`email` for
       more information.

   Draft
       A term used for a review request or review that's been created or
       modified but not yet published for others to see. We store these in a
       draft state so that the review request or review can be fully composed
       before, giving users control over when they're finished and ready for
       feedback.

   Draft Bar
       A green bar that represents an active draft for a review request or
       review, allowing the draft to be discarded or published.

   Evolution File
       A file that contains information on how to make changes to the database
       schema (in a database-agnostic way). These files are shipped with
       Review Board or extensions and are applied automatically during site
       upgrade or when enabling an extension.

   Interdiffs
       An interdiff is a diff between diffs. They show what has changed
       between two versions of a diff, which is useful when making incremental
       changes to a very large diff.

   Local Site
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
       <https://daringfireball.net/projects/markdown/>`_ for more information.

   OAuth2
       OAuth2 is a framework that allows third-party applications to gain
       limited access to user accounts, without the owner of that account
       divulging their authentication credentials.

   Post-commit Hook
       A script that is executed after a commit is made to a repository.
       See :ref:`automating-rbt-post` for ways to use post-commit hooks
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

   Python Eggs
       A type of binary package for Python applications. These are installed
       via :command:`easy_install`.

       Historically, this was the main way that Python applications, Review
       Board included, would be packaged and distributed. They have since
       been replaced by a new format, :term:`Python Wheels`.

   Python Entry Point
   Python Entry Points
       A mechanism used by Python packages to register classes so that they
       can be found by other Python applications. This is often used for
       pluggable features. Review Board uses this to register extensions,
       repository support, and more.

   Python Wheels
       The modern package format for Python applications. These are installed
       using modern versions of the :command:`pip` package installer.

   Review Group
   Review Groups
       A group of users, often a team or set of owners on a component, that
       can be assigned as a targetted reviewer for a review request.

   Review Request
   Review Requests
       A review request is a collection of assets (such as source code,
       documents, and test data) and information (such as a summary,
       description, testing, and branch information) put up for review.

   Unified Diff
       A type of :term:`diff file` designed to be easy to parse and easy
       to read by humans. This is the format supported by Review Board.

       Unified diffs indicate the changed region of a file by showing some
       unchanged lines of context, then lines beginning with a minus sign
       (``-``) to show removed lines or a plus sign (``+``) to show added
       lines. Replaced lines are shown by a remove line followed by an add
       line.
