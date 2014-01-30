.. _general-settings:

================
General Settings
================

The General Settings page contains most of the settings you'll want to change
for a new site. It's split up into the following sections:

* :ref:`site-settings`
* :ref:`cache-settings`
* :ref:`search-settings`


.. _site-settings:

Site Settings
=============

In this section you'll specify where the server lives (on the Internet and
geographically) and administrator contacts.

The following settings can be configured:

* **Server:**
    The URL of the site. This should include the ``http://`` or
    ``https://`` but should not contain the subdirectory Review Board
    is set up to use.

    This setting is required.

* **Media URL:**
    The URL to the media files. This can point to a dedicated
    server, or it can be a path relative to installed Review Board
    site.

    This setting is optional, and if left blank, the default
    media path of ``/media/`` is used.

* **Administrator Name:**
    The full name of the primary administrator for this Review Board site.

    This setting is required.

* **Administrator E-Mail:**
    The e-mail address of the primary administrator for this Review Board
    site.

    This setting is required.

* **Time Zone:**
    The time zone where the server resides. All the timestamps shown for
    review requests will be based on this time zone.

    New review requests created in Review Board 1.7 or higher will have
    this timezone stored. Users will see the correct date and time in their
    own timezone.


.. _cache-settings:

Cache Settings
==============

* **Cache Backend:**
    The type of cache backend to use for your server.

    We **strongly** recommend using Memcached.

    Depending on the cache backend, other settings fields may be available.

    Available options are:

    * Memcached
    * File cache

* **Cache Hosts:**
    The list of Memcached servers to use for all cache storage. More than
    one server can be listed by separating the servers with semicolons.

    Servers should be in ``hostname:port`` format.

    This is only shown if choosing "Memcached" as the cache backend.


* **Cache Path:**
    The file path on the server where Review Board can cache data.

    This is only shown if choosing "File cache" as the cache backend.


.. _search-settings:

Search
======

* **Enable search:**
    If enabled, a search field is provided at the top of every page to
    quickly search through review requests.

    An up-to-date index is required to provide useful search results. See
    :ref:`search-indexing` for more information.


.. _search-index-directory:

* **Search index directory:**
    The directory on the server's file system where the search index files
    will be stored. This defaults to a directory named "search-index" in the
    site's directory, if left blank.

    Either absolute or relative paths can be provided. A relative path will
    always be relative to the site directory.

    This option is only available if search is enabled.
