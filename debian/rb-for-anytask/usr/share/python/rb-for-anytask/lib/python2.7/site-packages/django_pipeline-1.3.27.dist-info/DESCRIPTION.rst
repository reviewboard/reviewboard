Pipeline
========

Pipeline is an asset packaging library for Django, providing both CSS and
JavaScript concatenation and compression, built-in JavaScript template support,
and optional data-URI image and font embedding.

Installation
------------

To install it, simply: ::

    pip install django-pipeline


Documentation
-------------

For documentation, usage, and examples, see :
http://django-pipeline.readthedocs.org


.. :changelog:

History
=======

1.3.27
------

* Fix bug in URL rewriting. Thanks to Clinton Blackburn for the report.
* Ignore stylus files in finders. Thanks to Evandro Myller.

1.3.26
------

* Fix default javscript mimetype to be more IE friendly.
* Fix storage documentation. Thanks to Jacob Haslehurst.

1.3.25
------

* Many documentation improvements. Thanks to Brad Pitcher, Jaromir Fojtu and Feanil Patel.
* Add no-op compressors. Thanks to Zachary Kazanski.

1.3.24
------

* Quote path before passing them to compilers.
* Add documentation around PIPELINE_MIMETYPES.

1.3.23
------

* Fix gzip mixin regression. Thanks to Sayed Raianul Kabir.
* Improve PipelineStorage listdir method. Thanks to Julien Hartmann.
* Fix setup.py. Thanks to Benjamin Peterson and Colin Dunklau.

1.3.22
------

* Fix mimetype declaration. Thanks to Thomas Parslow.
* Fix gzip mixin. Thanks to Sayed Raianul Kabir.
* Small documentation improvements. Thanks to Kristoffer Smedlund for the report.

1.3.21
------

* Fix whitespace and charset in templates tags output. Thanks to Philipp Wollermann.
* Various documentation fixes. Thanks to Chris Applegate, Natal Ngetal, DJ Sharkey and Andy Kish.
* Fix bug in data-uri handling when running Python 3. Thanks to Sander Steffann.

1.3.20
------

* Allow to run compilation without multiprocessing. Thanks to Rajiv Bose.
* Don't rewrite data-uri. Thanks to Tomek Paczkowski.
* Fix manifesto support.

1.3.19
------

* Allow to pre-compress files via ``pipeline.storage.GZIPMixin``. Thanks to Edwin Lunando for the suggestion and early prototype.
* Improve post processing.

1.3.18
------

* Performance improvements. Thanks to Miguel Araujo Perez.

1.3.17
------

* Improve tests.
* Escape url in template tags. Thanks to Joshua Kehn.
* Allow to change javascript templates separator. Thanks to Axel Haustant.

1.3.16
------

* Fix python3 compatibility. Thanks to Stephan Wienczny.
* Various documentation improvements. Thanks to Chrish Clark, Michael Angeletti and Gokmen Gorgen.
* Tests improvements. Thanks to Michał Górny.

1.3.15
------

* Fix unicode handling in sub-process commands. Thanks to Caio Ariede.
* MinifyHTMLMiddleware use PIPELINE_ENABLED. Thanks to Caio Ariede.
* Add useful finders. Thanks to Danielle Madeley.

1.3.14
------

* Fix prefix handling. Thanks to Brian Montgomery.
* Recalculate Content-Length after minifying HTML. Thanks to Camilo Nova.
* Improve compiler outdated detection. Thanks to Hannes Ljungberg.

1.3.13
------

* Don't hardcode SASS arguments. Thanks to Cal Leeming.
* Fix tests packaging (again). Thanks to Andrew Grigorev.

1.3.12
------

* Add minimal GAE support.
* Make file globing deterministic. Thanks to Adam Charnock.
* Fix tests packaging. Thanks to Mike Gilbert.

1.3.11
------

* Fix Windows specific bug. Thanks to Tom Yam.

1.3.10
------

* Add ``PIPELINE_ENABLED`` settings. Huge thanks to Carl Meyer.
* Update compass compiler documentation. Thanks to Camilo Nova.

1.3.9
-----

* Fix regression in Compiler. Thanks to David Hughes.

1.3.8
-----

* Improve compiler API. Thanks to Remy Sanchez.
* Improve documentation on cache busting via staticfiles. Thanks to Rami Chowdhury.
* Fix url() bug for url with querystring and hash in them. Thanks to Miroslav Shubernetskiy.
* Add third party compilers in documentation. Thanks to Jared Scott.
* Fix extension compatibility with both jinja2 and coffin. Thanks to Mark Sandstrom.
* Add Livescript compiler. Thanks to Arnar Yngvason.

1.3.7
-----

* Don't require Django in setup.py. Thanks to Jannis Leidel.
* A lot of documentation improvements. Thanks to Jared Scott and Christopher Dilorenzo.

1.3.6
-----

* Make our threaded code compatible with python 3.

1.3.5
-----

* Run compilers in threads, should improve performance in DEBUG mode.

1.3.4
-----

* Fix false errors on subprocess. Thanks to Fabian Büchler.
* Don't run MinifyHTMLMiddleware when DEBUG is True. Thanks to Venelin Stoykov.

1.3.3
-----

* Fix subprocess calls.

1.3.2
-----

* Jinja2 support is back.
* Many small improvements in documentation.

1.3.1
-----

* Improve exceptions hierarchy.
* Improve our sub-process calls.
* Update uglify-js documentation. Thanks to Andrey Antukh.

1.3.0
-----

* Add support Python 3, with some help from Alan Lu.
* Add support for Django 1.5.
* Remove support for Django < 1.4.
* Drop support for Python < 2.6.
* Drop support for ``staticfiles`` app, in favor of ``django.contrib.staticfiles``.
* Drop ``PIPELINE`` settings, in favor of ``DEBUG`` to avoid confusion.
* Drop support for ``jinja2`` temporarily.

1.2.24
------

* Fix yui/yuglify settings overriding each other. Thanks to Fábio Santos.

1.2.23
------

* Separate yuglify compressor from YUI compressor.
* Improve HTML compression middleware.

1.2.22
------

* Better compressor error messages. Thanks to Steven Cummings.
* Improve installation documentation. Thanks to Steven Cummings.
* Fix packaging metadata. Thanks to Rui Coelho for noticing it.
* Add documentation about non-packing storage.

1.2.21
------

* Run stylus even if file is considered outdated.

1.1.20
------

* Ensure yui-compressor can still use YUICompressor.

1.2.19
------

* **BACKWARD INCOMPATIBLE** : Replace python cssmin compressor to run the command (works for python or node implementation)

1.2.18
------

* **BACKWARD INCOMPATIBLE** : Replace yui-compressor by yuglify, check your configuration.
* Use finders in manifest. Thanks to Sjoerd Arendsen.

1.2.17
------

* Fully tested windows compatibility. Thanks to Idan Zalzberg.

1.2.16
------

* Fix manifesto module. Thanks to Zenobius Jiricek.
* Ensure coffee-script compiler don't try to overwrite file. Thanks to Teo Klestrup Röijezon.

1.2.15
------

* Ensure asset url are build with ``posixpath``.
* Deal with storage prefix properly.

1.2.14
------

* Jinja2 support, thanks to Christopher Reeves.
* Add read/save_file method to CompilerBase.

1.2.13
------

* Fix unicode bug in compressor. Thanks to Victor Shnayder.
* Fix outdated detection bug. Thanks to Victor Shnayder and Erwan Ameil.
* Add slimit compressor. Thanks to Brant Young.

1.2.12
------

* Fix IO error when creating new compiled file. Thanks to Melvin Laplanche.

1.2.11
------

* Add a small contribution guide
* Add mimetype settings for sass and scss
* Change compiler interface to let compiler determine if file is outdated

1.2.10
------

* Use ``/usr/bin/env`` by default to find compiler executable. Thanks to Michael Weibel.
* Allow to change embed settings : max size and directory. Thanks to Pierre Drescher.
* Some documentation improvements. Thanks to Florent Messa.

1.2.9
-----

* Don't compile non-outdated files.
* Add non-packing storage.

1.2.8
-----

* Fix bugs in our glob implementation.


1.2.7
-----

* Many documentation improvements. Thanks to Alexis Svinartchouk.
* Improve python packaging.
* Don't write silently to STATIC_ROOT when we shouldn't.
* Accept new .sass extension in SASSCompiler. Thanks to Jonas Geiregat for the report.


1.2.6
-----

* New lines in templates are now escaper rather than deleted. Thanks to Trey Smith for the report and the patch.
* Improve how we find where to write compiled file. Thanks to sirex for the patch.


1.2.5
-----

* Fix import error for cssmin and jsmin compressors. Thanks to Berker Peksag for the report.
* Fix error with default template function. Thanks to David Charbonnier for the patch and report.


1.2.4
-----

* Fix encoding problem.
* Improve storage documentation
* Add mention of the IRC channel #django-pipeline in documentation


1.2.3
-----

* Fix javascript mime type bug. Thanks to Chase Seibert for the report.


1.2.2.1
-------

* License clarification. Thanks to Dmitry Nezhevenko for the report.


1.2.2
-----

* Allow to disable javascript closure wrapper with ``PIPELINE_DISABLE_WRAPPER``.
* Various improvements to documentation.
* Slightly improve how we find where to write compiled file.
* Simplify module hierarchy.
* Allow templatetag to output mimetype to be able to use less.js and other javascript compilers.


1.2.1
-----

* Fixing a bug in ``FinderStorage`` when using prefix in staticfiles. Thanks to Christian Hammond for the report and testing.
* Make ``PIPELINE_ROOT`` defaults more sane. Thanks to Konstantinos Pachnis for the report.


1.2.0
-----

* Dropped ``synccompress`` command in favor of staticfiles ``collecstatic`` command.
* Added file versionning via staticfiles ``CachedStaticFilesStorage``.
* Added a default js template language.
* Dropped ``PIPELINE_AUTO`` settings in favor of simple ``PIPELINE``.
* Renamed ``absolute_asset_paths`` to ``absolute_paths`` for brevity.
* Made packages lazy to avoid doing unnecessary I/O.
* Dropped ``external_urls`` support for now.
* Add cssmin compressor. Thanks to Steven Cummings.
* Jsmin is no more bundle with pipeline.


