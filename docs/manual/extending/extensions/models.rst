.. _extension-models:

===============
Database Models
===============

Writing Database Models
=======================

Extensions are able to provide :djangodoc:`Django models <topics/db/models>`,
which are database tables under the control of the extension. Review Board
handles registering these models, creating the database tables, and performing
any database schema migrations the extension defines.

Extensions use the same convention as `Django apps`_ when defining models. In
order to define new models, a :file:`models.py` file, or a :file:`models/`
directory constituting a Python module needs to be created.

Here is an example :file:`models.py` file:

.. code-block:: python

   from django.db import models


   class MyExtensionsSampleModel(models.Model):
       name = models.CharField(max_length=128)
       enabled = models.BooleanField(default=False)

See the :djangodoc:`Django models <topics/db/models>` documentation for more
information on how to write a model.

.. note::
   When an extension is disabled, tables for its models remain in the
   database. These should generally not interfere with anything, but is
   important to know.


.. _Django apps: http://django-best-practices.readthedocs.io/en/latest/applications.html


.. _extension-models-evolution:

Making Changes to Custom Models
===============================

Over time, you may need to make changes to your custom models. For instance,
you might add another field to a model, or remove a field, or change some of
the defaults for the field. When you make these changes, you'll need to create
an :term:`evolution file`.

Evolution files are Python files that describe the changes being made to
models. These are used by `Django Evolution`_ (a component used by Review
Board) to make updates to your database the next time the extension is updated
and re-enabled.

After you've made changes to your models, you can auto-generate a suitable
evolution file for your changes by running:

.. code-block:: sh

    $ ./reviewboard/manage.py evolve --hint

.. warning::

   This assumes that you're developing your extension against a standalone
   development install of Review Board. You should *never* develop against a
   production server!

   You will also need to have the extension enabled for the above command to
   work.

   Finally, *never* run ``evolve --hint --execute``. Some of Django
   Evolution's output may suggest these options, but these are not suitable
   for developing extensions. Don't even be tempted to use these options.

This command will output a Python script for your evolution. It will look
something like this:

.. code-block:: python

    from django_evolution.mutations import AddField
    from django.db import models


    MUTATIONS = [
        AddField('MyExtensionSampleModel', 'new_field',
                 models.BooleanField, initial=False),
    ]

For simple additions and changes, the generated file will be sufficient. For
more advanced usage, please see the `Django Evolution documentation`_.

You will want to save the file in the :file:`evolutions/` directory. This
directory would be located in the same directory containing :file:`models.py`.
You can name the saved file whatever you like, so long as it ends in
:file:`.py`.

Next, you'll need to add this evolution file's name to the "sequence" list in
:file:`evolutions/__init__.py`. This should look like:

.. code-block:: python

    SEQUENCE = [
        'my_evolution_name',
    ]

(Note the lack of a ``.py`` on the name.)

Test this on your development system by disabling and re-enabling the
extension. If all goes well, the extension should be enabled, and your
database should contain the modified fields.


.. _Django Evolution: https://github.com/beanbaginc/django-evolution
.. _Django Evolution documentation:
   https://github.com/beanbaginc/django-evolution/blob/master/docs/evolution.txt


Adding Data to Review Board Models
==================================

Review Board ships with many different models for storing information on
users, review requests, diffs, and more.

Your extension *cannot* modify these models! Trying to hack new fields onto
the models by modifying the source code or monkey-patching will just result in
database upgrade failures (which may require more extensive work by us to
fix as part of a `support incident`_).

You have a couple of options for augmenting data:

1. Store data in the ``extra_data`` fields of models.

   Many of our models contain an ``extra_data`` field, which stores standard
   Python data types like strings, dictionaries, and lists. The field itself
   works like a dictionary.

   You can store data under a namespace within that field. We recommend using
   the extension's ID for the namespace.

   For example:

   .. code-block:: python

       custom_data = review_request.extra_data.getdefault(MyExtension.id, {})
       custom_data['my_list'] = [1, 2, 3]
       custom_data['my_dict'] = {'foo': 'bar'}
       review_request.save(update_fields=['extra_data'])

   This data can be used by your extension and can be accessed and modified
   through the API. However, you *cannot* perform database queries based on
   the contents of this field.

2. Use custom models.

   If you need to work with indexable fields, use a custom model as described
   above. You can associate this with
   :py:class:`~reviewboard.reviews.models.review_request.ReviewRequest` or
   other models using a :py:class:`django.db.models.ForeignKey`, if you like:

   .. code-block:: python

       class MyCustomModel(models.Model):
           review_request = models.ForeignKey(ReviewRequest)

   You can then query your custom models based on the review request you want
   using Django's standard querying capabilities.


.. _support incident: https://www.reviewboard.org/support/


.. _extension-admin-site:

Adding Models to the Admin Database Browser
===========================================

By setting :py:attr:`Extension.has_admin_site
<djblets.extensions.extension.Extension.has_admin_site>` to ``True``, an
extension will be given its own database browser in the administration UI.
This is also known as a "Django administration site," but it's not a
full-fledged administration UI like Review Board's.

To get to this "site," you'll click :guilabel:`Database` on the list of links
for the extension, where you'd normally go to enable or disable the extension.

The extension will also have an :py:attr:`Extension.admin_site
<djblets.extensions.extension.Extension.admin_site>` attribute that points to
the :py:class:`~django.contrib.admin.sites.AdminSite` object used. This is
provided automatically, and is used primarily for the registration of models.

Only models that are registered will appear in the database browser. You can
see the documentation on the :djangodoc:`Django admin site
<ref/contrib/admin/index>` for details on how this works. For example:

.. code-block:: python

   from sample_extension.extension import SampleExtension
   from sample_extension.models import SampleModel


   # Register the Model so it will show up in the admin site.
   SampleExtension.instance.admin_site.register(SampleModel)
