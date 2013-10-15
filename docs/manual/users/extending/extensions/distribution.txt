.. _extension-distribution:

======================
Extension Distribution
======================


.. _extension-python-egg:

Python Egg
==========

Extensions are packaged and distributed as Python Eggs. This allows for
automatic detection of installed extensions, packaging of static files,
and dependency checking.

The :py:mod:`setuptools` module is used to create a Python Egg. A
:file:`setup.py` file is created for this purpose. See the :py:mod:`setuptools`
documentation for a full description of features.


.. _extension-entry-point:

Entry Point
-----------

.. highlight:: python

To facilitate the auto-detection of installed extensions, a
``reviewboard.extensions`` entry point must be defined for each
:ref:`extension-class`. Here is an example entry point definition::

      entry_points={
           'reviewboard.extensions':
               'sample_extension = sample_extension.extension:SampleExtension',
      },

This defines an entry point for the :py:class:`SampleExtension` class from
the :py:mod:`sample_extension.extension` module. Here is an example of
a full :file:`setup.py` file defining this entry point::

   from reviewboard.extensions.packaging import setup


   PACKAGE = "sample_extension"
   VERSION = "0.1"

   setup(
       name=PACKAGE,
       version=VERSION,
       description="Description of extension",
       author="Your Name",
       packages=["sample_extension"],
       entry_points={
           'reviewboard.extensions':
               'sample_extension = sample_extension.extension:SampleExtension',
       },
   )


.. _extension-egg-static-files:

Static Files
------------

Any static files (such as css, html, and javascript) the extension requires
should be listed in the extension class's ``css_bundles`` or ``js_bundles``
attributes. Providing you are using the py:func:`setup` method from
:py:mod:`reviewboard.extensions.packaging`, all listed CSS and JavaScript
media bundles will be automatically compiled, minified, combined, and packaged
along with your extension.

See :ref:`extension-static-files` for more information on bundles.

If you have other files you need to include, such as templates, you can list
them in the ``package_data`` section in setup.py. For example::

       package_data={
           'sample_extension': [
               'templates/rbreports/*.html',
               'templates/rbreports/*.txt',
           ],
       }

Here is an example of a full setup.py file including the static files::

   from reviewboard.extensions.packaging import setup


   PACKAGE = "sample_extension"
   VERSION = "0.1"

   setup(
       name=PACKAGE,
       version=VERSION,
       description="Description of extension",
       author="Your Name",
       packages=["sample_extension"],
       entry_points={
           'reviewboard.extensions':
               'sample_extension = sample_extension.extension:SampleExtension',
       },
       package_data={
           'sample_extension': [
               'templates/rbreports/*.html',
               'templates/rbreports/*.txt',
           ],
       }
   )


.. _extension-egg-dependencies:

Dependencies
------------

Any dependencies of the extension are defined in the :file:`setup.py` file
using :py:attr:`install_requires`. Here is an example of a full
:file`setup.py` file including a dependency::

   from reviewboard.extensions.packaging import setup


   PACKAGE = "sample_extension"
   VERSION = "0.1"

   setup(
       name=PACKAGE,
       version=VERSION,
       description="Description of extension",
       author="Your Name",
       packages=["sample_extension"],
       entry_points={
           'reviewboard.extensions':
               'sample_extension = sample_extension.extension:SampleExtension',
       },
       install_requires=['PythonPackageIDependOn>=0.1']
   )

This will ensure any packages the extension requires will be installed.
See the `Setuptools`_ documentation for more information on
:py:attr:`install_requires`.

.. _`Setuptools`: http://pypi.python.org/pypi/setuptools#using-setuptools-and-easyinstall

In addition to requiring python packages when installing, an extension can
declare a list of additional extensions it requires. This requirements list
gives the name of each extension that must be enabled before allowing the
extension itself to be enabled. This list is declared by setting the
:py:attr:`requirements` attribute. Here is an example of an extension
defining a requirements list::

   class SampleExtension(Extension):
       requirements = ['other_extension.extension.OtherExtension']

       def __init__(self, *args, **kwargs):
           super(RBWebHooksExtension, self).__init__(*args, **kwargs)


.. _extension-egg-developing:

Developing With a Python Egg
----------------------------

In order for Review Board to detect an extension, the Python Egg must be
generated using the :file:`setup.py` file, and installed. During development
this can be done by installing a link in the Python installation to the
source directory of your extension. This is accomplished by running::

   python setup.py develop

If changes are made to the setup.py file this should be executed again.

See the `Setuptools`_ documentation for more information.


.. comment: vim: ft=rst et ts=3
