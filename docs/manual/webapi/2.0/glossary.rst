.. _webapi2.0-glossary:

========
Glossary
========

.. glossary::

   date/time format
       The standard date/time format used in the web API is in the format
       of ``YYYY-MM-DD HH:MM:SS``. All date/times shown in resources will
       be in this format.

       When passing a date/time as a value to a resource or to a query
       parameter, you can use this format or :term:`ISO8601 format`.

   ISO8601 format
       ISO8601 format defines a date as being in ``{yyyy}-{mm}-{dd}`` format,
       and a date/time as being in ``{yyyy}-{mm}-{dd}T{HH}:{MM}:{SS}``.
       A timezone can also be appended to this, using ``-{HH:MM}``.

       The following examples are valid dates and date/times:

       * ``2010-06-27``
       * ``2010-06-27T16:26:30``
       * ``2010-06-27T16:26:30-08:00``
