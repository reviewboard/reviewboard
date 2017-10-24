.. _full-text-search:

================
Full-Text Search
================

If your Review Board server has full-text search enabled, you will be able to
search through all review requests using the search field on any page. This
will match text in the review request, the files modified, and other fields
using our query syntax.

Logical operators, such as AND, OR, and NOT, can be used to narrow down your
search. Individual fields on review requests can also be searched.


Query Syntax
============

There are a variety of ways to combine terms in the search field. By default,
the search results will be an "AND" of any words entered in the box. This means
searching for ``window javascript`` will give pages that have both of those
terms in them.

In order to narrow down your results, there are a few useful operators you can
use.

* **OR**:

  This operator will change the relationship from "AND" to "OR". This will
  make it so search results will contain any of the words instead of all.
  Searching for ``window OR javascript`` will yield all review requests that
  contain either of those words.

* **NOT**:

  This works a lot like ``OR``, except it will filter out results containing
  the NOT term. For example, ``window NOT javascript`` will return matches
  that have "window" but not "javascript".

* **Phrase**:

  Sticking something in double-quotes will search for the exact phrase instead
  of splitting it up into terms.

There are a number of other operators you can use to tweak the results. For a
full explanation of the Whoosh query syntax (including a couple features not
mentioned here), see `The default query language`_.


.. _`The default query language`:
   https://whoosh.readthedocs.io/en/latest/querylang.html


Fields
======

In addition to searching the full text of a review request, you can search
individual fields for better results. To search for a term inside a specific
field, prefix that term with *field*:, where *field* is one of the below:

* ``summary``:

  This field searches only the summary. ``summary: window`` will match
  requests with window in the summary only.

* ``description``:

  This field searches only the description. ``description: javascript`` will
  match requests with javascript in the description only.

* ``testing_done``:

  This field searches only Testing Done. ``testing_done: tested`` will match
  requests with tested in Testing Done only

* ``author`` and ``username``:

  These two fields search the review request poster. ``author`` will search
  both the username and full name, whereas ``username`` is just the username.

* ``bug``:

  This field searches by bug identifier. Searching for ``bug:83724`` will find
  any review requests which address that bug.

* ``file``:

  This field indexes filenames in the diff. Searching for ``file:frob.c`` will
  yield any review requests which altered that file.

These fields can be combined like any other terms. Searches like
``file:frob.c AND author:Jim`` can make it easy to quickly find old review
requests.


What's Indexed
==============

The full text of review requests, including the summary, description, and
testing, is indexed.

Filenames in the diffs are also indexed, but the contents of the code in the
diffs are not.

Reviews are not indexed.

:term:`Private review requests` are indexed, but will only show up in search
results for users who have permission to access them.
