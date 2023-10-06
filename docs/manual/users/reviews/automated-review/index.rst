.. _using-automated-code-review:

======================
Automated Code Reviews
======================

.. versionadded:: 3.0

Review Board provides some tools for doing automated review when code changes
are published.

By integrating static analysis tools, style checkers, and :term:`CI` (or
:term:`Continuous Integration`) builds into your review process, you can free
up your developers to concentrate on the larger, more important issues.


Choosing Your Tools
===================

There are several tools which can help with automated code review. Some of
these are bundled with Review Board, and some are available through external or
third-party tools.

* `Review Bot`_

  Our free Review Bot microservice connects your Review Board server to a
  wide ecosystem of code analysis tools, including:

  * `Cargo Tool`_
  * Checkstyle_ for Java
  * `Clang Static Analyzer`_
  * FBInfer_
  * Flake8_
  * `Go Tool`_
  * RuboCop_
  * ShellCheck_

  This can be :ref:`installed in your network
  <reviewbot:installation-manual>` on Linux or by using our :ref:`Review Bot
  Docker images <reviewbot:installation-docker>`.

  `Learn more about Review Bot <reviewbot-docs_>`_.

* **Jenkins**

  Jenkins is a full-featured :term:`CI` service that works in-house, allowing
  you to build and test your code automatically, posting results back to
  Review Board.

  Jenkins can work with any type of source code repository, and is a good
  choice for Review Board.

  Support for Jenkins is included with Review Board, and requires a
  `Jenkins plugin`_ to activate.

  :ref:`Learn more about using Jenkins with Review Board
  <integrations-jenkins-ci>`.

* **CircleCI**

  CircleCI is a :term:`CI` service that supports code hosted on GitHub and
  Bitbucket. It allows you to build and test your code automatically, posting
  results back to Review Board.

  Support for CircleCI is included with Review Board.

  :ref:`Learn more about using CircleCI with Review Board
  <integrations-circle-ci>`.

* **Travis CI**

  Travis CI is :term:`CI` service that works with GitHub.  It can also be used
  to perform various checks, posting results back to Review Board.

  Support for Travis CI is included with Review Board.

  :ref:`Learn more about using Travis CI with Review Board
  <integrations-travis-ci>`.

:ref:`Custom automated review tools <developing-automated-review-tools>` can
also be developed entirely in-house.


.. _Cargo Tool:
   https://www.reviewboard.org/docs/reviewbot/latest/tools/cargotool/
.. _Checkstyle:
   https://www.reviewboard.org/docs/reviewbot/latest/tools/checkstyle/
.. _Clang Static Analyzer:
   https://www.reviewboard.org/docs/reviewbot/latest/tools/clang/
.. _FBInfer: https://www.reviewboard.org/docs/reviewbot/latest/tools/fbinfer/
.. _Flake8: https://www.reviewboard.org/docs/reviewbot/latest/tools/flake8/
.. _Go Tool: https://www.reviewboard.org/docs/reviewbot/latest/tools/gotool/
.. _Jenkins plugin: https://plugins.jenkins.io/rb/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/
.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/
.. _reviewbot-docs: https://www.reviewboard.org/docs/reviewbot/
.. _RuboCop: https://www.reviewboard.org/docs/reviewbot/latest/tools/rubocop/
.. _ShellCheck:
   https://www.reviewboard.org/docs/reviewbot/latest/tools/shellcheck/


.. _configuring-automated-reviews:

Configuring Automated Reviews
=============================

Configuration depends on whether you're using a built-in automated review
solution (such as Jenkins or CircleCI), or using an extension (such as Review
Bot).

Automated reviews can be enabled for all review requests, or subsets based on
conditions (such as review requests on specific repositories or assigned to
specific review groups).

See the guides below to learn more:

* :ref:`Configuring Review Bot <reviewbot:configuration>`
* :ref:`Configuring Jenkins <integrations-jenkins-ci>`
* :ref:`Configuring CircleCI <integrations-circle-ci>`
* :ref:`Configuring Travis CI <integrations-travis-ci>`


.. _performing-automated-reviews:

Performing Automated Reviews
============================

Most automated review tools will default to running automatically when a
new review request has been published, or a new diff has been published to
a review request.

Some tools can be configured to run manually instead. This is useful for tools
that may take a long time to check (such as :term:`CI` tools that need to
build products and run test suits).

If a tool is configured to be run manually, it'll be up to the owner of a
review request to trigger the automated review through a :guilabel:`Run`
button.


.. _automated-review-status-results:
.. _status-updates:

Automated Review Status and Results
===================================

When automated reviews are active for a review request, they'll be presented
as a list of :guilabel:`Checks run` (also known as :term:`status updates`).
These will appear under the :ref:`review request overview
<review-requests-overview>` and under any
:ref:`Review request changed overview <review-request-changed-overview>`.

.. image:: status-updates.png

Each :term:`status update` lists:

* The name of the automated tool being run
* The status of the check (such as running, failed, or succeeded)
* A link to additional build output (if provided by the tool)
* A button to run the tool (if configured to run manually instead of
  automatically)

These will update as results come in.

Failing automated code reviews will come with a list of :ref:`open issues
<issue-tracking>`, helping you track what needs to be fixed. These can be
discussed and resolved like any other review.


.. _developing-automated-review-tools:

Developing Automated Review Tools
=================================

If you need a custom solution for automated code review (to integrate with
in-house tools or compliance systems), you can build it on the Review Board
Platform in one of three ways:

1. On top of Review Bot's :ref:`automated review platform <reviewbot-coderef>`
   classes.

   All tools are built on top of Review Bot's :py:mod:`reviewbot.tools.base`
   classes.

   See the `existing source code <reviewbot-tools-source_>`_ for Review Bot's
   built-in tools for examples.

2. On top of Review Board's :ref:`extensions-framework <extensions-overview>`.

   Extensions can listen to :py:data:`review_request_published signals
   <reviewboard.reviews.signals.review_request_published>`, run any necessary
   checks, and manage results with
   :py:class:`StatusUpdates
   <reviewboard.reviews.models.status_update.StatusUpdate>` entries.

3. Through a combination of :ref:`WebHooks <webhooks>` and RBTools_.

   By listening to new review requests via WebHooks, your own internal tools
   can perform checks and report back using :ref:`rbt status-update
   <rbt-status-update>`.


.. _reviewbot-tools-source:
   https://github.com/reviewboard/ReviewBot/tree/master/bot/reviewbot/tools
