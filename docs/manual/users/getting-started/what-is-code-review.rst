====================
What is Code Review?
====================

Overview
========

Code review is the process of making pieces of source code available for
other developers to review, with the intention of catching bugs and design
errors before the code becomes part of the product.

Code review dramatically helps in the quality of products. By catching
mistakes early, a lot of bad problems in a product can be avoided. Not
all companies or developers take advantage of code review, but more and
more are making it a part of their development culture and requirements.


Types of Code Review
====================

There are two types of code review: pre-commit and post-commit.

**Pre-commit review** is a form of code review where code is reviewed *before*
going into the codebase. In this method, a :term:`diff file` is uploaded to
Review Board, which reviewers can comment on, and once there's approval the
code is committed to the repository.

**Post-commit review** is where the code is reviewed *after* going into the
codebase. The code is committed to the repository and, at some point later, the
code is reviewed. Any fixes that need to be made are then committed again
later.

The advantage of pre-commit review over post-commit review is that mistakes
are caught before they become part of the product. The downside is that
development may take longer.

Review Board supports both styles of code review. For pre-commit reviews, an
uncommitted change can be uploaded either through the web UI, or using the
:ref:`rbt post <rbtools:rbt-post>` tool.

For post-commit reviews, depending on the repository type, Review Board allows
you to browse the commit history and choose a change to review. All repository
types are supported for post-commit review by using the
:ref:`rbt post <rbtools:rbt-post>` tool to prepare a diff file for the change
and upload it.
