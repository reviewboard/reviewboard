.. _extension-static-files:

============================
Extension Static Media Files
============================

Static Media Bundles
====================

Extensions can define sets of CSS and JavaScript files that should be packaged
and made available for use on a page. These are called "bundles," and are
listed in the extension class's :py:attr:`Extension.css_bundles
<djblets.extensions.extension.Extension.css_bundles>` and
:py:attr:`Extension.js_bundles
<djblets.extensions.extension.Extension.js_bundles>` attributes.

Each bundle has a name and a list of source files pertaining to that type of
bundle. The format for a bundle is the same for CSS and JavaScript. Here's an
example:

.. code-block:: python

    class SampleExtension(Extension):
        css_bundles = {
            'default': {
                'source_filenames': (
                    'css/common.less',
                ),
            },
        }

        js_bundles = {
            'default': {
                'source_filenames': (
                    'js/extension.js',
                    'js/common.js',
                ),
            },
            'admin': {
                'source_filenames': (
                    'js/admin.js',
                ),
            }
        }

A bundle can have any name. Bundle names will not conflict between extensions.

There's one special bundle named "default". If a "default" bundle is defined,
it will appear on all pages without having to be manually loaded. This is a
good place to put code you know will always need to execute, such as your
JavaScript :py:class:`~reviewboard.extensions.base.JSExtension` subclass, or
to place CSS overrides you want to apply to all pages.

A bundle may also define an ``output_filename``, if it cares to specifically
name it. This is the name that will be used for the combined file during
packaging. If not provided, the file will be named based on the bundle name.
Usually, you will not need to provide your own name.


Packaging Bundles
-----------------

Static bundles are packaged along with your extension automatically. You don't
have to do anything special. You will, however, need some node.js_
dependencies in order to package static media bundles.

If you're running Review Board 2.5.7+, these dependencies will be installed
for you when you begin to build the package.

If you're running an older version, you will need to manually install them
yourself. First, make sure you have a modern version of node.js installed and
then run:

.. code-block:: sh

    $ sudo npm install -g less uglifyjs


.. _node.js: https://nodejs.org/en/


.. _extension-js-file-types:

JavaScript File Types
---------------------

Depending on the filename for your JavaScript code, the files will be run
through a compilation step. Files with a :file:`*.es6.js` or :file:`*.ts`
extension will be compiled with Babel_, as either `ES6+`_ or TypeScript_
respectively.

This allows you to use modern JavaScript features while still targeting your
code to the same browsers as supported by Review Board. Using this is highly
recommended if you expect to use features such as:

* `ES6 classes
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes>`_
* `ES6 modules
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules>`_
* `async/await
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function>`_
* `Generators
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Generator>`_
* `Destructuring
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment>`_
* `Template literals
  <https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Template_literals>`_

.. versionchanged:: 6.0

    Support for TypeScript files was added in Review Board 6.0.


.. _Babel: https://babeljs.io/
.. _TypeScript: https://typescriptlang.org/
.. _ES6+: https://tc39.es/ecma262/


.. _extension-es6-modules:

ES6 Modules
-----------

Starting with Review Board 6.0, you can additionally use ES6 modules to
organize your code.

To use this, you'll need to write a :file:`rollup.config.js` file with your
rollup configuration. This should live somewhere in your extension's codebase
in a directory at or above the location of your javascript files.

This can be customized to your liking. At a minimum it will need to define the
output module type, some common plugins, and the output namespace:

.. code-block:: javascript

    import babel from '@rollup/plugin-babel';
    import commonjs from '@rollup/plugin-commonjs';
    import resolve from '@rollup/plugin-node-resolve';

    export default args => ({
        external: [
            'RB',
        ],
        output: {
            exports: 'named',
            freeze: false,
            sourcemap: true,
            format: 'umd',
            generatedCode: 'es2015',

            // Put all code into window.MyExtension
            name: 'MyExtension',
            extend: true,
        },
        plugins: {
            babel: babel({
                babelHelpers: 'external',
                extensions: extensions,
            }),
            commonjs: commonjs({
                ignoreTryCatch: false,
                transformMixedEsModules: true,
            }),
            resolve: resolve({
                browser: true,
                extensions: [
                    '.es6.js',
                    '.js',
                    '.ts',
                ],
            }),
        },
    });


Any files with a basename of `index` (for example, `index.ts` or
`index.es6.js`) will be compiled using rollup.js_. You can then use the ES6
`export` and `import` keywords to manage your dependencies. Anything exported
from your index file(s) will be made available in the bundle.

With the :file:`rollup.config.js` example above, the following view would be
available as ``MyExtension.MyView`` within the runtime context.

.. code-block:: javascript

    export const MyView = Backbone.View.extend({
        ...
    });


.. todo: explain externalGlobals/resolve configuration to allow to import from
   RB codebase.


.. versionadded:: 6.0
.. _rollup.js: https://rollupjs.org


.. _extension-static-media:

Writing Static Media
====================

CSS/Less
--------

Files listed in :py:attr:`Extension.css_bundles
<djblets.extensions.extension.Extension.css_bundles>` can either be plain CSS
files, or less_ (:file:`*.less`) files.

Less is an extension of CSS that allows for variables, macros, calculations,
conditionals, includes, and more. When used with your extension, these files
will be automatically compiled to CSS for you.

We recommend using less_ over plain CSS files.

No matter which you use, you will want to take care to namespace your class
names and IDs appropriately, in order to not conflict with rules from either
Review Board or other extensions.

.. _less: http://lesscss.org/


Including Review Board Styles
-----------------------------

If you're using less_, you can reference definitions (variables and macros)
from Review Board's stylesheets by adding:

.. code-block:: less

    @import (reference) "@{STATIC_ROOT}rb/css/defs.less";

This will allow you to use any variable or macro we have defined. You can see
the list by viewing the contents of
:rbsource:`reviewboard/static/rb/css/defs.less` (and the contents of any
files it includes) in the branch for the version you're developing against.


JavaScript
----------

JavaScript files have access to the Review Board JavaScript codebase,
jQuery_, Backbone.js_, and other shipped libraries.

If you're not using ES6 modules to structure your code, it is recommended that
you namespace all the code in your JavaScript file, and wrap the file in a
closure, as so:

.. code-block:: javascript

    (function() {

    // Your code here.

    })();

This will ensure that your variables do not leak and interfere with other
extensions or the Review Board codebase.


.. _jQuery: https://jquery.com/
.. _Backbone.js: http://backbonejs.org/


Loading Static Media
====================

When creating a template for a :ref:`extensions-template-hook`, you may need
to load one of your bundles. There are a couple of ways to do this: By using
the ``apply_to`` option for a bundle, or by manually loading using template
tags.


.. _static-media-apply-to:

Applying To Specific Pages
--------------------------

You can make a bundle apply to specific pages by listing their
:djangodoc:`URL names <topics/http/urls#naming-url-patterns>` in the
``apply_to`` option in the bundle. This looks something like:

.. code-block:: python

    class SampleExtension(Extension):
        css_bundles = {
            'my-bundle': {
                'source_filenames': (
                    'css/common.less',
                ),
                'apply_to': [
                    'review-request-detail',
                    'my-custom-view',
                ],
            },
        }

There are a few useful predefined lists of URL names that might be useful to
you:

:py:data:`reviewboard.urls.diffviewer_url_names`:
    URLs for all diff viewer pages.

:py:data:`reviewboard.urls.review_request_url_names`:
    URLs for the review request and diff viewer pages.

:py:data:`reviewboard.urls.reviewable_url_names`:
    URLs for the file attachment review and diff viewer pages.

Some other common URL names you might want to use include:

``review-request-detail``:
    The review request page itself.

``file-attachment``:
    The file attachment review UI pages (note that this will apply to *all*
    types of file attachments with review UIs!).

``user-preferences``:
    The My Account page.

``login``:
    The login page.

``register``:
    The user registration page.

``dashboard``:
    The Dashboard page.

You can look at the :ref:`Review Board codebase reference
<reviewboard-coderef>` for all the URL names (they'll be listed in the
:file:`urls.py` files).


Loading Using Template Tags
---------------------------

This can be done through the
:py:func:`{% ext_css_bundle %}
<djblets.extensions.templatetags.djblets_extensions.ext_css_bundle>` or
:py:func:`{% ext_js_bundle %}
<djblets.extensions.templatetags.djblets_extensions.ext_js_bundle>` or
template tags by passing the extension variable (provided to your template)
and the bundle name to load. For example:

.. code-block:: html+django

    {% load djblets_extensions %}

    {% ext_css_bundle extension "my-css-bundle" %}
    {% ext_js_bundle extension "my-js-bundle" %}


.. tip::

   Any bundles named "default" will be loaded automatically. You won't need to
   manually load them on the page.


If you need to reference a static file (such as an image), you can use the
:py:func:`{% ext_static %}
<djblets.extensions.templatetags.djblets_extensions.ext_static>` template tag:

.. code-block:: html+django

    {% load djblets_extensions %}

    <img src="{% ext_static extension 'images/my-image.png' %}" />
