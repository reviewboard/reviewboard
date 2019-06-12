.. _using-markdown:

==============
Using Markdown
==============

Many of the multi-line text fields in Review Board support a simple markup
language called :term:`Markdown`. This allows you to perform basic formatting
of your text (such as creating lists or denoting emphasis), as well as more
complex things like including syntax-highlighted code samples or images.

This document does not intend to be a full reference on the Markdown language,
but rather a quick primer on the basic features that are useful when writing
review requests or reviews.

.. note::

    Review Board's implementation of Markdown shares a lot in common with
    `GitHub Flavored Markdown
    <https://help.github.com/articles/github-flavored-markdown>`_. While it's
    part of the basic Markdown spec, embedding raw HTML is *not* allowed, to
    prevent cross-site scripting attacks. If you include HTML tags, they will
    be shown to the user as-is, rather than treated as HTML.


.. _markdown-basic-syntax:

Basic Markdown Syntax
=====================

Headers
-------

Headers are added by underlining the relevant text with equals signs or
dashes::

    Header
    ======


Lists
-----

Markdown supports both ordered (numbered) and unordered (bulleted) lists. These
are written using a natural syntax. Ordered lists use numbers followed by
periods::

    1. First item
    2. Second item
    3. Third item

While unordered lists can be defined with asterisks, plus signs, or hyphens::

    * First item
    * Second item
    * Third item


Emphasis
--------

Text can be emphasized by surrounding it with asterisks or underscores. The
resulting text will be shown in a heavier font::

    This text is *italic*

    This text is **emphasized**


Links
-----

Basic links can be added to your text using a combination of square brackets
and parentheses::

    This text has a [link to wikipedia](http://wikipedia.org/).

.. note::

    In most cases, you won't need to build your links yourself. Any URLs that
    are included in your text will automatically be turned into links. In
    addition, certain special strings like "bug 234" or "/r/583" will be
    automatically linked to the relevant bug or review request.


Images
------

If you have images which are accessible from a URL, you can embed them into
your text using a syntax similar to links. These start with an exclamation
mark, followed by square brackets containing the "alt" attribute, followed by
parentheses with the URL to the image::

    ![Image description](http://example.com/image.png)

You can also :ref:`upload images via drag-and-drop <markdown-upload-images>`
into any Markdown-capable text field.


Tables
------

Simple tables can be inserted by drawing the table using a combination of
vertical bars and hyphens::

    Header | Header | Header
    -------|--------|-------
    Cell   | Cell   | Cell
    Cell   | Cell   | Cell


.. _markdown-code-syntax:

Code Samples
============

When writing reviews, It's often very useful to write small snippets of code.
Markdown allows you to notate which parts of your text are code or terminal
text, and optionally render code with syntax highlighting. This can be
especially nice for proposing changes.

Code can be formatted inside a line by enclosing the text in single backticks.
This is often useful when referring to symbols from the code::

    I think it would be nice if you moved this code up near the `do_foo` method.

Longer code samples can be denoted using block notation. Any blocks which are
indented at least 4 spaces will be treated as a code block. This code will not
be syntax-highlighted, but instead will be shown as plain text.

.. code-block:: text

    The following code block will not be syntax-highlighted.

        def test():
            logging.error('Test failed')

In addition, code blocks can be notated without indentation by surrounding
the block with triple backticks using the syntax from GitHub Flavored
Markdown.

.. code-block:: text

    The following code block will not be syntax-highlighted.

    ```
    function test() {
        console.log('Test failed');
    }
    ```

You can specify a language name after the first set of backticks in order to
enable syntax highlighting for the code. For instance:

.. code-block:: text

    The following code block WILL be syntax-highlighted.

    ```javascript
    function test() {
        console.log('Test passed!');
    }
    ```

Some of the most common language codes you may want to use include:

* C: ``c``
* C++: ``cpp``, ``c++``
* C#: ``csharp``
* CSS: ``css``
* CoffeeScript: ``coffeescript``
* HTML: ``html``
* JSON: ``json``
* Java: ``java``
* JavaScript: ``javascript``, ``js``
* Objective-C: ``objective-c``, ``obj-c``, ``objc``
* Objective-C++: ``objective-c++``, ``obj-c++``, ``objc++``
* PHP: ``php``
* Perl: ``perl``, ``pl``
* Python 3: ``python3``, ``py3``
* Python: ``python``, ``py``
* Ruby: ``ruby``, ``rb``
* Snobol: ``snobol``
* XML: ``xml``

For the complete list, look through the Pygments
`list of lexers <http://pygments.org/docs/lexers/>`_. Any of the
"short names" listed can be used.


.. _emoji:

Emoji
=====

.. versionadded:: 3.0

Review Board's Markdown mode supports Emoji Shortcodes. These allow for
referencing Emoji characters by name (such as ``:thumbsup:``), and should be
familiar to people using Slack, GitHub, and other services (in fact, we use
GitHub's Gemoji_ set for Review Board).

The advantage of Emoji Shortcodes is that they work on any database setup
(MySQL users cannot use normal Unicode-based Emoji by default), and are safer
for inclusion in commit messages.

Here are some examples of Emoji Shortcodes:

|smile| ``:smile:``

|heart| ``:heart:``

|thumbsup| ``:thumbsup:`` ``:+1:``

|thumbsdown| ``:thumbsdown:`` ``:-1:``

|bug| ``:bug:``

|cloud| ``:cloud:``

|bulb| ``:bulb:``

|trophy| ``:trophy:``

You can see a standard list of Emoji Shortcodes on this `Emoji cheat sheet`_.
(Note that this is maintained by a third-party, and may not always be
accurate).


.. |smile| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f604.png
   :width: 16
   :height: 16
.. |heart| image:: https://github.githubassets.com/images/icons/emoji/unicode/2764.png
   :width: 16
   :height: 16
.. |thumbsup| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f44d.png
   :width: 16
   :height: 16
.. |thumbsdown| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f44e.png
   :width: 16
   :height: 16
.. |bug| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f41b.png
   :width: 16
   :height: 16
.. |cloud| image:: https://github.githubassets.com/images/icons/emoji/unicode/2601.png
   :width: 16
   :height: 16
.. |bulb| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f4a1.png
   :width: 16
   :height: 16
.. |trophy| image:: https://github.githubassets.com/images/icons/emoji/unicode/1f3c6.png
   :width: 16
   :height: 16

.. _Gemoji: https://github.com/github/gemoji
.. _Emoji Cheat Sheet: https://gist.github.com/rxaviers/7360908


.. _markdown-escaping:

Escaping
========

Because Markdown syntax endows many common punctuation symbols with special
meaning, these can sometimes unintentionally trigger formatting. In this case,
you can avoid this by escaping the relevant character with a backslash::

    I really want a \` backtick in this line.

Backslash escapes can be used for the following characters::

    \ backslash
    ` backtick
    * asterisk
    _ underscore
    {} curly braces
    [] square brackets
    () parentheses
    # hash mark
    + plus sign
    - minus sign
    . period
    ! exclamation mark


.. _markdown-upload-images:

Uploading Images
================

.. versionadded:: 3.0

You can upload images into any Markdown-capable text field (comments, replies,
review request fields, etc.) by dragging-and-dropping from your file manager
into the field. This will upload the image and then create a Markdown
reference to it.

While the image is uploading, the text field should be left open in order for
the Markdown reference to update.
