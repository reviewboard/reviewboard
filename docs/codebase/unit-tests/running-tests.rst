.. _running-unit-tests:

==================
Running Unit Tests
==================

Djblets, Review Board and RBTools all have unit tests that can be run
to make sure you don't break anything. It is important that you run
these before posting code for review. We also request that new code
include additions to the unit tests.

There are two types of tests that can be run: Python and JavaScript.


Running JavaScript Unit Tests
-----------------------------

To run the JavaScript tests, first launch the development web server.
Instructions on how to do so can be found in the :ref:`getting-started`
guide, under :ref:`development-web-server`. Once you have launched the
server, browse to::

    http://localhost:8080/js-tests/

The full JavaScript test suite should then run automatically.


Running Python Unit Tests
-------------------------

You can run the test suite for any of our Python modules by typing::

    $ ./tests/runtests.py

This may take additional arguments for running subsets of tests, debugging
tests, etc. See the sections below.

We use nose_ to run our test suites, which will be installed if you followed
our :ref:`getting-started` guide. You can refer to their `usage guide
<nose-usage_>`_ for additional options not covered here.

If you're updating the unit tests, you may want to see the
:ref:`unit-test-fixtures` documentation.


.. _nose: https://nose.readthedocs.org/en/latest/
.. _nose-usage: https://nose.readthedocs.org/en/latest/usage.html


Running Subsets of Tests
========================

Running all unit tests may take a while. To speed up unit testing, there are
options to run subsets of tests.

To run only the tests in a specific module::

    $ ./tests/runtests.py reviewboard.scmtools.tests

To run the tests in a specific class::

    $ ./tests/runtests.py — reviewboard.scmtools.tests.test_git:GitTests

To run only a specific test case::

    $ ./tests/runtests.py — reviewboard.scmtools.tests.test_git:GitTests.test_get_file


Working With Failed Tests
=========================

The test suites are big, and sometimes you just want to rerun the tests that
have failed. You can easily do this in a couple of ways.


Stopping After Failure
----------------------

First, you may want to stop the test runner after the first encountered
failure. You can do this with the :option:`-x` option::

    $ ./tests/runtests.py -x


Running Tests by ID
-------------------

You may also have noticed that unit tests have an ID listed beside it, like:

.. code-block:: text

    #14 Testing writing to the cache with non-ASCII data ... ok
    #15 Testing the cache with the Vary header ... ok
    #16 Testing the cache with the Vary header and different requests ... ok

These IDs are 14, 15, 16, etc.

After you've run the test suite at least once, you can pass these IDs to
the test runner instead of figuring out the full path to the test function.
For instance, to rerun tests 15 and 16::

    $ ./tests/runtests.py 15 16

Note that you can only do this once you've done a full test run once.

If you want to build this list of IDs up-front without doing a full test run,
you can generate them with::

    $ ./tests/runtests.py --collect-only

Test IDs are cached to a :file:`.noseids` file in the top-level of your source
tree. You can delete this file if you ever need to completely reset the IDs
for any reason.

See the `nose test IDs`_ documentation for more information.


.. _nose test IDs: https://nose.readthedocs.org/en/latest/plugins/testid.html


Running Only Failed Tests
-------------------------

You can also choose to run only the test IDs that had failed in your last
run::

    $ ./tests/runtests.py --failed


This is going to be much faster than running through the entire test suite
again.


Debugging Test Failures
=======================

If a unit test fails, you're going to want to find out why. You can do this by
jumping to the code for that test and begin adding print statements, or you
can do this by running PDB (the Python Debugger).

Passing :option:`--pdb` to the test runner will drop you into PDB if a test
error occurs (a crash/exception, but not an assertion failure)::

    $ ./tests/runtests.py --pdb

If you want to be dropped in when an assertion fails, try
:option:`--pdb-failures`::

    $ ./tests/runtests.py --pdb-failures

You can combine the two::

    $ ./tests/runtests.py --pdb --pdb-failures

You can then rerun the failed tests once you believe you've corrected the
problem.

See the `nose debugger`_ documentation for more information.


.. _nose debugger: https://nose.readthedocs.org/en/latest/plugins/debug.html


Showing Test Coverage
=====================

When writing unit tests, it's important to know whether your unit tests
were comprehensive, covering the various cases in the code you've written.
With our test suites, you can generate a coverage report which will show all
the files in the project, how many statements were executed or missed, the
line ranges not yet covered under the executed tests, and the coverage
percentages.

This looks like::

    Name                          Stmts   Miss  Cover   Missing
    -----------------------------------------------------------
    rbtools/api/transport.py         17      7    59%   13, 17, 21, 29, 38,
    47, 61
    rbtools/api/utils.py             19     14    26%   6-28, 40
    rbtools/testing.py                3      0   100%
    rbtools/testing/testcase.py      11      0   100%
    [...]

    -----------------------------------------------------------
    TOTAL                          1787    651    64%
    ----------------------------------------------------------------------
    Ran 39 tests in 0.168s


You can generate a coverage report by passing :option:`--with-coverage` when
executing tests. For example::

    $ ./tests/runtests.py --with-coverage
    $ ./tests/runtests.py --with-coverage rbtools.tests:CapabilitiesTests

Cached information previous test runs are stored in the :file:`.coverage`
file in the top-level of the source tree. The test runners use this to show
you a more comprehensive coverage report. You can erase this file to generate
fresh coverage reports for your next test run, or you can pass
:option:`--cover-erase`.

See the `nose coverage`_ documentation for more information.


.. _nose coverage: https://nose.readthedocs.org/en/latest/plugins/cover.html


Analyzing Performance
=====================

If your unit test runs are slow, there may be a bug in the test code or in the
code the tests are calling that are leading to performance issues. To diagnose
this, you'll want to generate a performance profile, which will show every
call made and how long each one took.

This looks like::

    11825 function calls (11566 primitive calls) in 0.033 seconds

    Ordered by: cumulative time

    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      10/1    0.000    0.000    0.033    0.033 /Library/Python/2.7/site-packages/nose-1.3.0-py2.7.egg/nose/suite.py:175(__call__)
      10/1    0.000    0.000    0.033    0.033 /Library/Python/2.7/site-packages/nose-1.3.0-py2.7.egg/nose/suite.py:196(run)
        39    0.000    0.000    0.032    0.001 /Library/Python/2.7/site-packages/nose-1.3.0-py2.7.egg/nose/case.py:44(__call__)
        39    0.000    0.000    0.032    0.001 /Library/Python/2.7/site-packages/nose-1.3.0-py2.7.egg/nose/case.py:115(run)
    [...]

You can run this report by passing the :option:`--with-profile` option when
executing tests. For example::

    $ ./tests/runtests.py --with-profile
    $ ./tests/runtests.py --with-profile rbtools.tests:CapabilitiesTests


See the `nose profiling`_ documentation for more information.


.. _nose profiling: https://nose.readthedocs.org/en/latest/plugins/prof.html
