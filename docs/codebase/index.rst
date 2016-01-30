====================================
Review Board Code Base Documentation
====================================


Introduction
============

This is a set of guides on the Review Board codebase. They cover the
process for developing Review Board, information on writing third party
modules, and contributing to the project.

Review Board is written in the `Python`_ programming language and makes use
of the `Django`_ web framework.

The source code for Review Board is available from our `Git repository`_.

.. _`Git repository`: https://github.com/reviewboard/reviewboard/
.. _Python: https://www.python.org/
.. _Django: https://www.djangoproject.com/


Contributor Guides
==================

.. toctree::
   :maxdepth: 1

   getting-started
   generating-documentation
   coding-standards
   contributing-patches
   writing-good-descriptions
   custom-forks
   unit-tests/running-tests
   unit-tests/fixtures

.. `Creating SCMTools`


Common Tasks
============

.. toctree::
   :maxdepth: 1

   tasks/database-evolutions


Git Guides
==========

.. toctree::
   :maxdepth: 1

   git/clean-commits


Related Resources
=================

* `Django documentation`_
* `The Django Book`_
* `Git Cheat Sheets`_

.. _`Django documentation`: https://docs.djangoproject.com/
.. _`The Django Book`: http://djangobook.com/
.. _`Git Cheat Sheets`:
   https://training.github.com/kit/downloads/github-git-cheat-sheet.pdf
