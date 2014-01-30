.. _using-markdown:

==============
Using Markdown
==============

.. versionadded:: 2.0

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


Tables
------

Simple tables can be inserted by drawing the table using a combination of
vertical bars and hyphens::

    Header | Header | Header
    -------|--------|-------
    Cell   | Cell   | Cell
    Cell   | Cell   | Cell


Code Samples
============

When writing reviews, It's often very useful to write small snippets of code.
Markdown allows you to notate which parts of your text are code, and the result
will be rendered with syntax highlighting. This can be especially nice for
proposing changes.

Code can be formatted inside a line by enclosing the text in single backticks.
This is often useful when referring to symbols from the code::

    I think it would be nice if you moved this code up near the `do_foo` method.

Longer code samples can be denoted using block notation. Any blocks which are
indented at least 4 spaces will be treated as a code block. In addition, code
blocks can be notated without indentation by surrounding the block with triple
backticks, using the syntax from GitHub Flavored Markdown. This also allows
you to explicitly state what language the code is written in, for syntax
highlighting::

    Here's an indented code block:

        def test():
	    logging.error('Test failed')

    And a "fenced" code block:

    ```javascript
    function test() {
        console.log('Test failed');
    }
    ```


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
