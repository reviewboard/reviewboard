.. _testing-extensions:

==================
Testing Extensions
==================

Before you deploy your extension in production or release it to the public,
you'll want to ensure it's properly tested and works as expected. A great way
to do this is to write unit tests for your extension, which will ensure not
only that your extension works now, but will continue to work in the future
with newer versions of Review Board.


Writing Extension Unit Tests
============================

.. currentmodule:: reviewboard.extensions.testing.testcases

Extension test cases work like most any other test cases in Python. You'll
create a :file:`tests.py` file, or files starting with ``tests_`` inside a
:file:`tests` directory, and build test suites in there. See the
:py:mod:`unittest` documentation for more information on Python unit testing.

For extension tests, you'll want to use
:py:class:`reviewboard.extensions.testing.ExtensionTestCase
<ExtensionTestCase>` as your base class. You'll also need to define the
extension class being tested, as a class attribute.

For example:

.. code-block:: python

    from reviewboard.extensions.testing import ExtensionTestCase

    from my_extension.extension import MyExtension


    class MyExtensionTests(ExtensionTestCase):
        extension_class = MyExtension

        def test_something(self):
            self.assertEqual(self.extension.some_call(), 'some value')


Extensions may want to create a base class that defines the
:py:attr:`~ExtensionTestCase.extension_class` attribute, and subclass that for
all individual test suites. For example:

.. code-block:: python

    from reviewboard.extensions.testing import ExtensionTestCase

    from my_extension.extension import MyExtension


    class MyExtensionTestCase(ExtensionTestCase):
        extension_class = MyExtension


    class MyExtensionTests(MyExtensionTestCase):
        def test_something(self):
            self.assertEqual(self.extension.some_call(), 'some value')


As you can see above, tests will have access to an
:py:attr:`~ExtensionTestCase.extension` attribute. This will be an instance of
your extension, registered and enabled. You can call any function on it.

Next, we'll focus on some ways you can test your extension.


Testing Initialization
----------------------

Your unit test functions will be run after your extension has been
instantiated and enabled. If you need to check that everything was set up
right, you can simply create a test function for that and check the state.

You may want to run some code before an extension is enabled, to make sure
you can impact some of the initialization state beforehand. For example, you
may want to set some Review Board settings first. You can do this in one of
two ways:

1. Override :py:meth:`ExtensionTestCase.setUp`, set up your code, and then
   call the parent function to trigger the extension initialization:

   .. code-block:: python

       class MyExtensionTests(MyExtensionTestCase):
           def setUp(self):
               # Your pre-initialization setup goes here.

               super(MyExtensionTests, self).setUp()

2. Disable the extension in your test, set up some state, and then
   re-initialize it:

   .. code-block:: python

       class MyExtensionTests(MyExtensionTestCase):
           def test_init(self):
               self.extension_mgr.disable_extension(self.extension.id)

               # Your pre-initialization setup goes here.

               self.extension = \
                   self.extension_mgr.enable_extension(self.extension.id)


.. tip::

   If you want to check that certain functions were called during
   initialization, use our kgb_ module, which provides function spies for
   unit tests.

   You can use this to test whether certain functions were called, and with
   what arguments, and how many times. You can also override functions safely,
   helping simulate different behavior or provide hard-coded results from
   functions (even those provided by Python, Review Board, or other
   third-party modules).


.. _kgb: https://github.com/beanbaginc/kgb/


Testing Shut Down
-----------------

After your unit test has run, the extension will be shut down (if not already
shut down by the unit test).

If you're manually registering/unregistering state, you'll want to test this.
You can do this by creating a test function that disables the extension and
then checks the state.

.. code-block:: python

    class MyExtensionTests(MyExtensionTestCase):
        def test_init(self):
            self.extension_mgr.disable_extension(self.extension.id)

            # Check the extension state here.


Testing Signal Response
-----------------------

If your extension responds on behalf of signals, you can easily emit those
signals in order to simulate behavior. Tests are run in a sandbox, so you can
manipulate database state all you want without breaking other tests.

Let's say your extension listens to the
:py:data:`~reviewboard.reviews.signals.review_request_published` signal. You
can trigger your extension's behavior by manually emitting the signal:

.. code-block:: python

    from django.contrib.auth.models import User
    from reviewboard.reviews.models import ChangeDescription, ReviewRequest
    from reviewboard.reviews.signals import review_request_published


    class MyExtensionTests(MyExtensionTestCase):
        def test_review_request_published_handler(self):
            # In a real test, you'll want to set state for these objects.
            user = User(...)
            changedesc = ChangeDescription(...)
            review_request = ReviewRequest(...)

            # Trigger the signal.
            review_request_published.emit(user=user,
                                          review_request=review_request,
                                          changedesc=changedesc,
                                          trivial=False)

            # Check the extension's state or behavior here.


.. tip::

   Once again, kgb_ is useful here for checking that handlers were called,
   and for preventing unwanted methods from being triggered in response to
   the signals.


.. _extensions-running-unit-tests:

Running Unit Tests
==================

Review Board comes with a helpful program to run your extension's unit tests:
:ref:`rbext-test`. This is given one or more top-level Python modules
containing extensions and unit tests that you want to run, like so:

.. code-block:: text

    $ rbext test -e myextension.exension.MyExtension


That would set up your extension in a test environment and run any unit tests
found in ``myextension.tests``, ``myextension.submodule.tests``,
``myextension.anothermodule.tests.test_foo``, etc.


Running Subsets of Tests
------------------------

Running all unit tests may take a while. To speed up unit testing, there are
options to run subsets of tests.

To run only the tests in a specific module:

.. code-block:: text

   $ rbext test -e myextension.extension.MyExtension \
     myextension.submodule.tests

To run the tests in a specific class:

.. code-block:: text

   $ rbext test -e myextension.extension.MyExtension \
     myextension.submodule.tests:MyTests

To run only a specific test case:

.. code-block:: text

   $ rbext test -e myextension.extension.MyExtension \
     myextension.submodule.tests:MyTests.test_foo


.. _extensions-test-coverage:

Showing Test Coverage
---------------------

When writing unit tests, it's important to know whether your unit tests
were comprehensive, covering the various cases in the code you've written.
With our test suites, you can generate a coverage report which will show all
the files in the project, how many statements were executed or missed, the
line ranges not yet covered under the executed tests, and the coverage
percentages.

This looks like:

.. code-block:: text

    Name                          Stmts   Miss  Cover   Missing
    -----------------------------------------------------------
    myextension/extension.py         17      7    59%   13, 17, 21, 29, 38
    myextension/utils.py             19     14    26%   6-28, 40
    [...]

    -----------------------------------------------------------
    TOTAL                          1787    651    64%
    ----------------------------------------------------------------------
    Ran 39 tests in 0.168s


You can generate a coverage report by passing :option:`--with-coverage` when
executing tests. For example:

.. code-block:: text

   $ rbext test -e myextension.extension.MyExtension --with-coverage
   $ rbext test -e myextension.extension.MyExtension --with-coverage \
     myextension.submodule.tests

Cached information previous test runs are stored in the :file:`.coverage`
file in the top-level of the source tree. The test runners use this to show
you a more comprehensive coverage report. You can erase this file to generate
fresh coverage reports for your next test run.

See the `nose coverage`_ documentation for more information.


.. _nose coverage: https://nose.readthedocs.io/en/latest/plugins/cover.html


Additional Testing Options
--------------------------

Our test runner is based off nose_, which provides a large number of useful
options for working with unit tests. You can enable them by specifying
``-- <nose options>`` (Note the space after the ``--``).

For example, to run only the tests that failed last time:

.. code-block:: text

    $ rbext test -e myextension.extension.MyExtension -- --failed


See the `nose usage guide <nose-usage>`_ for more information.


.. _nose: https://nose.readthedocs.io/en/latest/
.. _nose-usage: https://nose.readthedocs.io/en/latest/usage.html


Custom Test Settings Files
--------------------------

When running unit tests, :command:`rbext` will put together a
:file:`settings_local.py` file with your extension modules and their
submodules added to :django:setting:`INSTALLED_APPS`, allowing their models,
admin state, etc. to be registered.

If you need a full custom environment, you can create a test settings file.

This can be named anything, but we recommend calling this
:file:`test_settings.py` and placing it somewhere in your source tree outside
of your extension's modules. You'd then specify this using :option:`-s`.

For example:

.. code-block:: text

   $ rbext test -s test_settings.py -e myextension.extension.MyExtension
