.. _what-is-code-review:

====================
What is Code Review?
====================

Code review is an integral part of modern design and development, helping
teams produce better code and better products. By making effective use of code
review, your product can be more:

* **Maintainable**, by encouraging buy-in on architecture and designs.

* **Consistent in quality**, by ensuring conventions are followed.

* **Secure**, by making human and automated security checks part of the
  process.

* **Bug-free**, as best as humanly and machinely possible.

Code review *dramatically* helps in the quality of products. By catching
issues early, a lot of potentially expensive problems can be avoided.

High-quality code reviews can lead to high-quality products. Review Board
has been helping companies achieve this since 2006.


.. _code-review-approaches:

Approaches to Code Review
=========================

There are many approaches to code review. Most companies will make use of a
combination of these approaches to achieve the highest-quality code:

.. _peer-code-review:
.. _human-code-review:
.. _automated-code-review:
.. _pre-commit-review:
.. _post-commit-review:

* **Peer code review** / **human code review**: Code is reviewed by another
  person, usually someone on the same team or someone responsible for the code
  being modified.

  People are an important part of the code review process, helping shape
  the architecture and design of the code, spotting usability problems, and
  making suggestions based on experience and procedure.

* **Automated code review**: Code is reviewed through lint, static code
  analysis, automated testing, or continuous integration tools.

  Automated tools can catch easy-to-miss mistakes, scan for security
  vulnerabilities, ensure code compliance, and make sure all your tests pass.
  This is best paired with peer/human code review.

  Products such as `Review Bot`_ or services such as :rbintegration:`CircleCI
  <circleci>` or :rbintegration:`Travis-CI <travis-ci>` can help manage your
  automated reviews.

  See :ref:`using-automated-code-review`.

* **Pre-commit review**: Code is reviewed *before* being pushed to a central
  codebase.

  The code is developed locally, put up for review, and is only pushed
  to the repository after approved by reviewers.

  See :ref:`using-pre-commit-review`.

* **Post-commit review**: Code is reviewed *after* being pushed to a central
  codebase.

  The code is committed to the repository first. Then, at some point later,
  the code is reviewed. Any fixes that need to be made are then pushed back to
  the repository later.

  See :ref:`using-post-commit-review`.


.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/
