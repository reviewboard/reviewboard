.. _creating-sites:

============================
Creating a Review Board Site
============================

Once Review Board is installed, a site must be created. Each site maps to
a domain, subdomain, or directory installation.

To create a site, you will use the ``rb-site install`` command.

You will need to decide on a place to install the site. In the examples
here, we will use :file:`/var/www/reviews.example.com`. The directory
should not exist yet. :command:`rb-site` will create it.


Creating the Database
=====================

Before you create the Review Board site, you'll need to create a database. The
particular steps for this depend on the database server software that you
intend to use.

.. admonition:: SQLite should only be used for test installations.

   While useful and portable, SQLite does not handle large loads with many
   concurrent users very well. We strongly recommend using MySQL or
   PostgreSQL for a real deployment.

   We don't officially support converting a database from SQLite to other
   databases, so it's important that you choose something that will work
   for you long-term.


MySQL
-----

In MySQL, before creating your database, make sure that your server is
configured to use the UTF-8 encoding for text. In the file :file:`my.cnf`, add
the following settings::

    [client]
    default-character-set=utf8

    [mysqld]
    character-set-server=utf8

After making these changes, restart your MySQL server.

Next, start up the mysql command prompt as your root user, and create a new
database and user (replacing ``myuser`` and ``myspassword`` with your desired
username and password, respectively)::

    $ mysql -u root -p
    mysql> CREATE DATABASE reviewboard CHARACTER SET utf8;
    mysql> CREATE USER 'myuser'@'localhost' IDENTIFIED BY 'mypassword';
    mysql> GRANT ALL PRIVILEGES ON reviewboard.* to 'myuser'@'localhost';


PostgreSQL
----------

To create a Postgres database, you'll need to run several commands as the
``postgres`` user. Start by running the following command (the particular
username may depend on your choice of operating system)::

    $ sudo su - postgres

Next, as the postgres user, create a database and a user to access it::

    $ createdb reviewboard
    $ createuser -P --interactive

The second of these commands will ask you several questions. For the last three
questions (relating to permissions), reply 'n'.

Finally, grant permissions for this user to your new database::

    $ psql
    => GRANT ALL PRIVILEGES ON DATABASE reviewboard to myuser


Beginning Installation
======================

Begin installation by running the following command::

    $ rb-site install /var/www/reviews.example.com

You will now be asked a series of questions about your site setup. It is
expected that you will know the answers to these questions. If not, you'll
have to decide what software you want to use for your services and refer to
their documentation on how to set them up and configure them.

.. admonition:: We recommend mod_wsgi and memcached

   If you're using Apache, we highly recommend using mod_wsgi. fastcgi
   has been known to have several issues (including memory leaks and problems
   when using the LDAP authentication backend), and mod_python is no longer
   developed or shipped with Apache.

   We also strongly recommend installing and using memcached. This will
   greatly improve performance of your Review Board installation. If
   possible, put this on a server with a lot of RAM.

.. admonition:: Apache should use the Prefork MPM

   The Worker MPM uses multiple threads, which can cause numerous problems
   with Review Board's dashboard and extensions implementations. In order for
   Review Board to work correctly, it should use the single-threaded Prefork
   MPM.

Once you have answered all the questions and completed the installation,
you'll need to change some directory permissions and install your web server
configuration files.


Changing Permissions
====================

Review Board expects to be able to write to the following directories and
their subdirectories:

* :file:`{sitedir}/data`
* :file:`{sitedir}/htdocs/media/uploaded`
* :file:`{sitedir}/htdocs/media/ext`
* :file:`{sitedir}/htdocs/static/ext`

Since Review Board is run by your web server, these directories and all
subdirectories and files must be writable by the user your web server runs
as.

This user varies by operating system, distribution and web server, so you may
need to look it up. If your web server is currently running, you can look at
what user it's running as.

Once you've figured this out, go ahead and change the permissions on the
directories. For example, in Linux/UNIX/MacOS X with a ``www-data`` user::

    $ chown -R www-data /var/www/reviews.example.com/data
    $ chown -R www-data /var/www/reviews.example.com/htdocs/media/uploaded
    $ chown -R www-data /var/www/reviews.example.com/htdocs/media/ext
    $ chown -R www-data /var/www/reviews.example.com/htdocs/static/ext

If you're using SQLite as your database, you will also need to change the
ownership of the site's :file:`db` directory to match the web server's
user. Otherwise, you may receive an Internal Server Error when accessing
the site.


Web Server Configuration
========================

:command:`rb-site` provides sample web server configuration files in the newly
created :file:`conf/` directory under your new site directory. In many installs,
these files will work out of the box, but they may require modification
depending on the rest of your web server configuration.

The configuration file will be based on the web server type and Python loader
you've specified. For example, if you used Apache and wsgi, you would
use :file:`apache-wsgi.conf`.

Installing these files is also dependent on the web server and operating
system/distribution.


Apache
------

There are two possible Apache configuration files that will be generated,
depending on whether you selected ``mod_wsgi``, ``mod_python`` or ``fastcgi``
during :command:`rb-site install`.

If you selected ``mod_wsgi``, your configuration file will be
:file:`conf/apache-wsgi.conf`.

If you selected ``mod_python``, your configuration file will be
:file:`conf/apache-modpython.conf`.

If you selected ``fastcgi``, your configuration file will be
:file:`conf/apache-fastcgi.conf`.

Depending on your operating system or Linux distribution, the configuration
file can be installed in a couple different ways.

If you have a :file:`sites-available` directory in your Apache
configuration directory (for example, :file:`/etc/apache2/sites-available`,
then you should rename your configuration file to match your site
(e.g., :file:`reviews.example.com.conf`) and put it in that directory. Then
create a symbolic link from that file to the :file:`sites-enabled`
directory. This is the most common setup on Debian or Ubuntu-based
distributions. So for example::

    $ cd /etc/apache2/sites-available
    $ cp /var/www/reviews.example.com/conf/apache-wsgi.conf reviews.example.com.conf
    $ cd ../sites-enabled
    $ ln -s ../sites-available/reviews.example.com.conf .

If you do not have a :file:`sites-available` or :file:`sites-enabled`
directory, you'll need to embed the configuration file in your global
Apache configuration file (usually :file:`/etc/httpd/httpd.conf` or
:file:`/etc/httpd/apache2.conf`).

.. note::

   On Fedora, you can do::

      $ ln -s /path/to/apache-wsgi.conf /etc/httpd/conf.d/reviewboard-sitename.conf

Of course, the configuration file can be placed anywhere so long as it's
at some point included by your main Apache configuration file.

Once you've installed the configuration file, restart Apache and then
try going to your site.

.. note::

    Some Apache installations (such as the default installs on Debian
    and Ubuntu) by default define a global virtual host that shares
    :file:`/var/www` as the document root. This may lead to problems
    with your install. If you access your site and see nothing but
    a directory listing, then you're affected by this problem.

    The solution is to remove the "default" site from your
    :file:`/etc/apache2/sites-enabled` directory. This may be
    called something like :file:`default` or :file:`000-default`.

.. note::

   On Fedora and Red Hat-derived systems, the following commands
   should be run (as root) to avoid SELinux denials::

      $ setsebool -P httpd_can_sendmail 1
      $ setsebool -P httpd_can_network_connect 1
      $ setsebool -P httpd_can_network_memcache 1
      $ setsebool -P httpd_can_network_connect_db 1
      $ setsebool -P httpd_unified 1

   These lighten the SELinux enforcement to allow the web server
   process to be able to send email, access the caching server,
   connect to a remote database server and support uploading diffs,
   respectively.

   Additionally, if you are using Review Board with a remote LDAP
   server, you should also run (as root)::

      $ setsebool -P httpd_can_connect_ldap 1

lighttpd
--------

The generated configuration file for lighttpd will be saved as
:file:`conf/lighttpd.conf`.

You should either add the contents of this file to your
:file:`/etc/lighttpd/lighttpd.conf`, or include it directly from
:file:`lighttpd.conf` using the ``include`` directive. See the
`lighttpd documentation`_ for more information.

.. _`lighttpd documentation`: https://redmine.lighttpd.net/projects/lighttpd/wiki
