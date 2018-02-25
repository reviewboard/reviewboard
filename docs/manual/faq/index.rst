.. _frequentlyaskedquestions:

==========================
Frequently Asked Questions
==========================


General Usage
=============


Is Review Board free for commercial use?
----------------------------------------

Yes, Review Board is absolutely free for commercial use.


What license is Review Board under?
-----------------------------------

Review Board is under the MIT license, which basically means you are free to
do as you want. You must however keep the software under the MIT license.

This permits companies to create custom modifications of Review Board for
their setups without contributing back. However, we strongly encourage people
to contribute back to the project, as it benefits everybody and will ease
upgrades by helping to keep your codebase from straying too far from ours.


Does Review Board support post-commit review?
---------------------------------------------

Yes, Review Board can handle :term:`post-commit review`, though currently you
need to use the command-line tool :command:`post-review` for this. See
:ref:`posting-committed-code` for more information. Note that for this usage,
the tool is only coincidentally named "post-review" (the "post" meaning
"put up"). You can use post-review for both pre-commit and post-commit reviews.

Review Board was initially designed for :term:`pre-commit review` and large
changes need to be made before post-commit reviews can be handled in the web
UI. We plan to implement this in a future release.


What are pre-commit and post-commit reviews?
--------------------------------------------

Pre-commit reviews are where code is reviewed before it's checked into a
public repository and mainline, non-developer branch. Code isn't committed
until reviewers sign off on it, leaving the tree stable and easing changes.

Post-commit reviews are where code is first committed to a public repository
and then reviewed. This makes the code available to others to develop against
until the code is reviewed, but large-scale changes to the architecture of the
code can then be hard to make without disrupting others. Post-commit reviews
sometimes happen by individuals or by a large group sitting together and
reading over the code together.


Does Review Board support git?
------------------------------

Review Board provides basic support for git. If you have a central
"official" git repository, Review Board will work well for you.

A basic pre-commit workflow with git would look like this:

* Clone the central repository.
* Make a change you want reviewed, but do not commit it yet.
* Run post-review (or otherwise submit a diff).
* Get reviews, update your change as needed.
* When the change is marked to ship, commit it to master and push it to
  the origin.

A workflow that takes advantage of local branches would look like this:

* Clone the central repository.
* Create a local branch and make a change you want reviewed.
* Run post-review (or otherwise submit a diff), comparing the branch to master.
* Get reviews, make additional changes on the branch as needed.
* When the change is marked to ship, merge it into master and push it to
  the origin.

Be sure to review the instructions on :ref:`repositories` for more information
on getting started with Review Board and git.


Troubleshooting
===============

I'm getting a 404 for every page
--------------------------------

This points to a configuration error in your web server configuration.

If you're using lighttpd as your web server, add the following to
``settings_local.py`` file::

    FORCE_SCRIPT_NAME = "/"

If this is a subdirectory install on lighttpd, set this variable to the
subdirectory name (making sure to keep leading and trailing slashes).


When I go to my site, I just see a directory listing
----------------------------------------------------

This may be due to your Apache installation using your :file:`/var/www`
directory as a global document root for your virtual hosts by default.
Look for a file called :file:`default` or :file:`000-default` (or similar)
in :file:`/etc/apache2/sites-enabled` and delete it. Then restart Apache.
You should be able to see your site now.


I'm getting the error: ``OperationalError at /dashboard/ near "DISTINCT": syntax error``
----------------------------------------------------------------------------------------

Your version of sqlite is too old. Make sure you're running sqlite 3.2.1 or
higher.


I get a page telling me to run syncdb, but I've done that already
-----------------------------------------------------------------

Generally this page is there to let you know when we've updated the database
schema so you can make the appropriate changes. Be sure to run
``rb-site upgrade /path/to/site``. See :ref:`upgrading-sites` for more
information on this.

If you've done that already and you're still getting the error, and you're
using sqlite for your database, you may need to set DATABASE_NAME in
your site's ``conf/settings_local.py`` file to the absolute path of the
database instead of the relative path. See `this thread
<http://groups.google.com/group/reviewboard/browse_thread/thread/9836ff1bcb501cc4>`_
for more information.


I installed a site using SQLite and every page generates an error
-----------------------------------------------------------------

This may mean the database isn't able to be written. If you see
``OperationalError: attempt to write to a readonly database`` in your
Apache's :file:`error_log`, then this is certainly the case.

Make sure you've set the permissions of the site's :file:`db` directory to
match the user for the web server.


I'm having trouble installing post-review on Windows Vista
----------------------------------------------------------

.. note:: These instructions were tested with simplejson 1.9.2. They may
          not be needed in more recent versions, but you should give them
          a try if you have problems.

You may need to modify a copy of simplejson (a Python module needed by
post-review).

1. `Download <https://pypi.python.org/pypi/simplejson>`_ the latest
   release of simplejson.
2. Extract the file to a local directory (using 7Zip_, WinRAR_ or another
   program).
3. Edit the file
   :file:`simplejson-{x}.{y}.{z}/simplejson.egg-info/SOURCES.txt`
   (where ``x.y.z`` is the version number of simplejson) and remove the line
   containing ``native_libs.txt``.
4. Run: ``easy_install simplejson-x.y.z``

If you don't have ``easy_install``, run the `Python Setuptools Installer`_.
Then repeat step 4 above.

Thanks to Daniel Wexler for this information.

.. _7Zip: http://www.7-zip.org/
.. _WinRAR: https://www.rarlab.com/
.. _`Python Setuptools Installer`: https://pypi.python.org/pypi/setuptools


I get the error "Unable to parse the server response" when uploading screenshots
--------------------------------------------------------------------------------

The permissions on your :file:`htdocs/media/uploaded` directory and
subdirectories are wrong. You need to make sure the contents are writable by
the web server.


The Edit Review page is really slow on Firefox
----------------------------------------------

The "It's All Text" extension has been known to have problems with
Review Board. If you're encountering problems related to text areas or
slowdown in the Edit Review page, try disabling this extension and seeing if
it makes a difference.


I'm using post-review (or a third party program) with Review Board on WSGI and can't log in.
--------------------------------------------------------------------------------------------

By default, mod_wsgi filters out the authentication requests that are used
for logging in with our API. Any brand new installations created using
Review Board 1.5.2 or higher should work, but if you're upgrading from an
older install, you will need to add the following to your web server's
configuration file::

    WSGIPassAuthorization On

This would usually go right above your ``WSGIScriptAlias`` line.

Once you've added this, restart your web server and try again. If it still
won't work, contact us on our mailing list.


URLs are shown with an internal host/port and not the URL configured in Settings
================================================================================

This is caused by a `security-related change
<https://www.djangoproject.com/weblog/2011/sep/09/security-releases-issued/>`
in Django 1.3.1. You can disable this behavior by adding the following to
your :file:`conf/settings_local.py`::

    USE_X_FORWARDED_HOST = True


Developing Review Board
=======================

What is Review Board written in?
--------------------------------

Review Board is written in Python_, using the Django_ web framework.

.. _Python: https://www.python.org/
.. _Django: https://www.djangoproject.com/


Where do I submit patches for Review Board?
-------------------------------------------

Patches to Review Board or Djblets should be submitted to our own Review Board
instance, https://reviews.reviewboard.org. If you submit patches to the
mailing list or bug tracker, we'll ask you to move them here for review.
