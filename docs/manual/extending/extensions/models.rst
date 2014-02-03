.. _extension-models:

===============
Database Models
===============

Extensions are able to provide `Django Models`_, which are database tables
under the control of the extension. Review Board handles registering these
models, creating the database tables, and performing any database schema
migrations the extension defines.

Extensions use the same convention as `Django apps`_ when defining
Models. In order to define new Models, a :file:`models.py` file, or a
:file:`models/` directory constituting a Python package needs to be created.

Here is an example :file:`models.py` file:

.. code-block:: python

   from django.db import models


   class MyExtensionsSampleModel(models.Model):
       name = models.CharField(max_length=128)
       enabled = models.BooleanField(default=False)

See the `Django Models`_ documentation for more information on how to
write a model, and `Django Evolution`_ for information on how to write
database schema migrations.

.. note::
   When an extension is disabled, tables for its models remain in the
   database. These should generally not interfere with anything.


.. _`Django Models`: https://docs.djangoproject.com/en/dev/topics/db/models/
.. _`Django Evolution`: http://django-evolution.googlecode.com/
