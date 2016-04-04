.. _database-evolutions:

===========================
Writing Database Evolutions
===========================

Overview
========

Review Board uses a tool called `Django Evolution`_ for handling changes to
the database. This makes it possible to write rules for seamlessly adding,
removing or changing fields on tables in a database, regardless of database
platform. Users upgrading their copies of Review Board will automatically
have these rules applied.

Django Evolution works by processing "evolution files," which are little bits
of Python code that lives in :file:`reviewboard/{app_dir}/evolutions/`.
These are processed at upgrade time. Each app directory should have evolution
files unique to its own :file:`models.py` file.

This guide will cover working with Django Evolution, writing evolution files,
and working around common problems.

.. _`Django Evolution`: https://github.com/beanbaginc/django-evolution


Writing an Evolution
====================

Prior to writing an evolution, or even making any database changes, you should
make a copy of your database. We recommend using SQLite for development,
since it's very easy to make multiple copies.

Writing and applying an evolution is very simple:

1. Make the changes to the :file:`models.py` files. You may be adding
   a column, removing one, or whatever.

2. Output a sample evolution file for your change by doing::

    ./reviewboard/manage.py evolve --hint

   Note that if you are using a third party model field (such as one
   supplied by Djblets), you will need to fix the import and field's class
   name to point to the right class.

3. Save the sample evolution to
   :file:`reviewboard/{app_dir}/evolutions/{filename}.py`.

   You should pick a descriptive name for your file that indicates what change
   you are making. It may be helpful to prefix the name with the name of the
   model you are modifying.

4. Edit (or create) :file:`reviewboard/{app_dir}/evolutions/__init__.py`
   and place the name of the evolution (without the ``.py``) in the
   ``SEQUENCE`` list.

   For example::

    SEQUENCE = [
        'my_evolution',
    ]

5. Test that the evolution is valid by running::

    ./reviewboard/manage.py evolve

   This won't apply the evolution. It will just say if it passed.

6. Apply the evolution to your database by running::

    ./reviewboard/manage.py evolve --execute

7. Place your code up for review!


Tips and Tricks
===============

* Back up your database before applying an evolution. This will allow you
  to go back and re-apply it if you make further changes to the evolution.

* Only ever have one evolution per app directory per change. If you're making
  incremental changes, do them on your database backup, instead of making
  new evolution files.

* Never run ``./reviewboard/manage.py evolve --hint --execute`` unless we
  tell you to! Ignore the instructions that come from Django Evolution
  telling you to run this.

* Don't forget to add the evolution files to your change when you're posting
  for review.


Troubleshooting
===============

"The stored evolutions do not completely resolve all model changes."
--------------------------------------------------------------------

This error means that you have changes to your database models that aren't
reflected in your evolution files. You may have made further changes since
generating the evolution.

Another cause is that your database and code tree are inconsistent. For
example, you may have applied your database evolution on one branch and then
switched branches. This is why it's important to keep a backup of the
database.

To fix this:

.. _recreate-db:

1. Commit or stash your changes in your branch and switch back to ``master``.

2. Delete your database.

3. Re-create the database.

4. Back up your new database.

5. Switch back to you branch and re-run the evolution.


"No evolution required"
-----------------------

Django Evolution compared your database and your models and found that they
match, so it doesn't have to do anything. This is due to one of the following:

* You already applied your evolution to the database.

* You haven't made any changes to your models on this branch.


I wrote an evolution but Django Evolution isn't seeing it
---------------------------------------------------------

You may have forgotten to add it to the :file:`evolutions/__init__.py`
file.

To fix this, make sure it's in the ``SEQUENCE`` list, without a file
extension.


There's an ImportError in my evolution
--------------------------------------

This is usually caused when using a model field that isn't part of Django.
For example, a Djblets field. Django Evolution assumes all fields are part of
Django and won't generate valid code.

To fix this:

1. Add an ``import`` statement to import the field you're referencing.

2. Use that field in the evolution instead of ``models.FieldName``.


I ran evolve --hint --execute
-----------------------------

Hopefully you have a backup of the database. If not, you will need to
re-create it. See the :ref:`instructions <recreate-db>` above.
