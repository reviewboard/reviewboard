.. _extension-static-files:

============
Static Files
============

Bundles
=======

Extensions can define the list of CSS and JavaScript files they as one or more
bundles, listed in the extension class's :py:attr:`css_bundles` or
:py:attr:`js_bundles` attributes. A bundle is a collection of static files of
the same type that are grouped together under a name.

The format for a bundle is the same for CSS and JavaScript. Here's an
example::

    class MyExtension(Extension):
        css_bundles = {
            'default': {
                'source_filenames': ['css/common.less'],
            },
        }

        js_bundles = {
            'default': {
                'source_filenames': [
                    'js/extension.js',
                    'js/common.js',
                ]
            },
            'admin': {
                'source_filenames': ['js/admin.js'],
            }
        }

A bundle can have any name. Bundle names will not conflict between extensions.

There's one special bundle named "default". If a "default" bundle is defined,
it will appear on all pages. This is a good place to put code you know will
always need to execute, such as your JavaScript Extension subclass, or
to place CSS overrides you want to apply to all pages.

A bundle may also define an ``output_filename``, if it cares to specifically
name it. This is the name that will be used for the combined file during
packaging. If not provided, the file will be named based on the bundle name.


Required Tools
--------------

To take advantage of static bundles, you will need to install
node.js_, LESS_, and UglifyJS_.

Most Linux distributions have a package for node.js. Otherwise, follow the
instructions on the node.js_ home page.

Once you install node.js, run::

    $ sudo npm install -g less uglifyjs


.. _node.js: http://nodejs.org/
.. _LESS: http://lesscss.org/
.. _UglifyJS: https://github.com/mishoo/UglifyJS


Loading Bundles in Templates
----------------------------

.. highlight:: django

When creating a template for a :ref:`extensions-template-hook`, you may need
to load one of your bundles. This can be done through the ``ext_css_bundle``
or ``ext_js_bundle`` template tags, by passing the extension variable
(provided to your template) and the bundle name to load. For example::

    {% ext_css_bundle extension "my-bundle" %}


Best Practices
==============

CSS/LESS
--------

Files listed in :py:attr:`css_bundles` can either be plain CSS files, or
LESS_ (``.less``) files. In the latter case, they will be compiled to CSS
before packaging. They do not need to be compiled during development, though,
as long as the package is being tested against a Review Board development
installation.

We recommend using LESS_ over plain CSS files.

Be sure to namespace your class names and IDs appropriately, in order to
not conflict with other extensions' rules.


JavaScript
----------

.. highlight:: javascript

JavaScript files have access to the Review Board JavaScript codebase,
jQuery, Backbone.js, and other shipped libraries.

It is recommended that you namespace all the code in your JavaScript file, and
wrap the file in a closure, as so::

    (function() {

    // Your code here.

    })();

This will ensure that your variables do not leak and interfere with other
extensions or the Review Board codebase.

When bundling, your JavaScript files will be minified using UglifyJS_.


.. comment: vim: ft=rst et ts=3
