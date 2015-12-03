.. _unit-test-fixtures:

==================
Unit Test Fixtures
==================

Overview
========

Fixtures in Django_ are essentially dumps of part of the database. They
contain data for the various models and can be loaded in automatically for
unit tests. This makes it quite easy for us to have various sets of data to
test against.

For our tests, we currently have three sets of fixtures:

1. :file:`reviewboard/accounts/fixtures/test_users.json`
   - accounts/auth apps
2. :file:`reviewboard/scmtools/fixtures/test_scmtools.json`
   - scmtools app
3. :file:`reviewboard/site/fixtures/test_site.json`
   - site app

In addition to fixtures, the :py:class::`reviewboard.testing.testcase.TestCase`
base class includes several methods for creating objects in the database, such
as Review Requests, Reviews, Comments, Repositories, and others. These are not
included in fixtures because of the variety of data that can be included, and
loading fixtures incurs a noticible cost on the time to run the test suite.

.. _Django: https://www.djangoproject.com/


Updating Fixtures
=================

If you're going to add to the existing fixtures, you'll first want to modify
:file:`settings_local.py`, set your database to be ``sqlite3`` (if it's
not already) and change the database name to something like
:file:`unittests.db`. You'll also need to install the ``django-reset`` package.
Then::

   ./reviewboard/manage.py syncdb --noinput
   ./reviewboard/manage.py reset --noinput scmtools
   ./reviewboard/manage.py loaddata test_users test_scmtools test_site

This should populate your database with the test data.

After you've added to the data set, dump them back out::

   ./reviewboard/manage.py dumpdata --indent=4 auth accounts > reviewboard/accounts/fixtures/test_users.json
   ./reviewboard/manage.py dumpdata --indent=4 scmtools > reviewboard/scmtools/fixtures/test_scmtools.json
   ./reviewboard/manage.py dumpdata --indent=4 site > reviewboard/scmtools/fixtures/test_site.json

You can choose to only dump the data you've actually modified. If you've only
created a user, you can just dump the auth and accounts apps.


Using Fixtures in Tests
=======================

Using fixtures in tests is really easy. In your test class (which must be
derived from :class:`django.test.TestCase`), add a ``fixtures = [...]`` line
listing the fixtures you intend to use. For example::

   class MyTests(TestCase):
       fixtures = ['test_users', 'test_scmtools']

       ...

Note that there are some dependencies to remember. ``test_users`` can be
included by itself, as can ``test_scmtools``, but if you want to use
``test_site``, you must also include ``test_users``.
