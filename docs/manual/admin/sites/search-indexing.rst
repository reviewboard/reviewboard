.. _search-indexing:

===============
Search Indexing
===============

You can enable search indexing by selecting :guilabel:`Search` under
:guilabel:`System Settings`, and then toggling :guilabel:`Enable search`.

There are two available search backends, Whoosh_ and Elasticsearch_. For larger
systems, we recommend Elasticsearch, which can be scaled up much more easily
than Whoosh.

.. _Elasticsearch: https://www.elastic.co/products/elasticsearch
.. _Whoosh: https://pypi.python.org/pypi/Whoosh/


Whoosh Configuration
====================

When using Whoosh, the :guilabel:`Search index directory` field must be filled
out to specify the desired directory where the search index will be stored.
This must be writable by the web server. We recommend creating this within your
site's ``data/`` directory.


Elasticsearch Configuration
===========================

Elasticsearch requires a running server to connect to. After selecting
Elasticsearch, you can enter the :guilabel:`Elasticsearch URL` and
:guilabel:`Elasticsearch index name` in the search settings form.

.. caution:: This currently requires a version of Elasticsearch prior to 5.0.
             Elasticsearch 5+ introduced some non-trivial changes which are not
             yet supported by the framework that Review Board uses for search.


.. _search-indexing-methods:

Scheduled Indexing vs. On-The-Fly Indexing
==========================================

Whichever configuration you use, you will need to set up indexing. This can be
done either with a scheduled crontab or on-the-fly.

Enabling :guilabel:`on-the-fly indexing` will cause Review Board to update the
search index whenever a relevant change is made. Because of performance
concerns, we recommend only using this with the Elasticsearch backend.

If you want to use scheduled indexes, you will need to set up a scheduled
command to run periodically to update the search index. On Linux or other
Unix-based systems with :command:`cron`, you can install the provided
``crontab`` file. This is available at :file:`conf/cron.conf` under your site
directory. For example, to install the crontab for the current user, type::

    $ crontab /path/to/site/conf/cron.conf

We recommend doing this as the web server user, to ensure that permissions are
correct to write to the index directory.

The default crontab will perform an index update every 10 minutes.

Whether you are using scheduled indexing or on-the-fly, you will need to
perform one full index when you first enable search. To do this, type the
following (as the web server user, if using Whoosh)::

    $ rb-site manage /path/to/site rebuild_index


For more information on generating search indexes, see the section on the
:ref:`rebuild_index and update_index <search-indexing-management-command>`
management commands.

Users should now be able to use the search box located on any page. See the
documentation on :ref:`full-text-search` to see what types of things you can
search for.
