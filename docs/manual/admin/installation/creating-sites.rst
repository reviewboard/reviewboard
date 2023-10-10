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


1. Create the Database
======================

Before you create the Review Board site, you'll need to create a database. The
particular steps for this depend on the database server software that you
intend to use.


MySQL / MariaDB
---------------

We recommend using MySQL 8 or higher, or MariaDB. If you're using an older
version of MySQL, start by choosing the right encoding.


Choose the Encoding
~~~~~~~~~~~~~~~~~~~

If you are running a version of MySQL prior to 8.x, you will want to use the
``utf8mb4`` encoding. Version 8.x and higher use this by default. To set this

Before creating your database, make sure that your server is configured to use
the ``utf8mb4`` encoding for text. In the file :file:`my.cnf`, add the
following settings:

.. code-block:: ini

    [client]
    default-character-set=utf8mb4

    [mysqld]
    character-set-server=utf8mb4

After making these changes, restart your MySQL server.


Create the MySQL Database
~~~~~~~~~~~~~~~~~~~~~~~~~

You'll need to create the Review Board user and database through the
:command:`mysql` command prompt, as follows:

.. code-block:: console

    $ mysql -u <username> -p -h <hostname>
    mysql> CREATE DATABASE <database_name>;
    mysql> CREATE USER '<rb_user>' IDENTIFIED BY '<rb_password>';
    mysql> GRANT ALL PRIVILEGES ON <database_name>.* to '<rb_user>';


For example:

.. code-block:: console

    $ mysql -u root -p -h db.example.com
    mysql> CREATE DATABASE reviewboard;
    mysql> CREATE USER 'rbuser'@'%' IDENTIFIED BY 's3cr3t';
    mysql> GRANT ALL PRIVILEGES ON reviewboard.* to 'rbuser'@'%';


PostgreSQL
----------

Create the PostgreSQL Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You'll need to create the Review Board user and database through the
:command:`psql` command prompt, as follows:

.. code-block:: console

    $ psql -U <username> -h <hostname>
    postgres=# CREATE USER <rb_user> WITH PASSWORD '<rb_password>';
    postgres=# CREATE DATABASE <database_name> WITH OWNER <rb_user>;


For example:

.. code-block:: console

    $ psql -U postgres -h db.example.com
    postgres=# CREATE USER rbuser WITH PASSWORD 's3cr3t';
    postgres=# CREATE DATABASE reviewboard WITH OWNER rbuser;


2. Create the Site Directory
============================

1. Begin installation by running the following command:

   .. tabs::

      .. group-tab:: Python Virtual Environments

         .. code-block:: console

            $ /opt/reviewboard/bin/rb-site install <path>

         For example:

         .. code-block:: console

            $ /opt/reviewboard/bin/rb-site install /var/www/reviews.example.com

      .. group-tab:: System Installs

         .. code-block:: console

             $ rb-site install <path>

         For example:

         .. code-block:: console

            $ rb-site install /var/www/reviews.example.com

2. Answer the questions about your install. These will include:
   including:

   * The domain name for the server
   * The path for the server, relative to the domain
   * The database information (as configured above)
   * The memcached server address
   * The username and password to use for the Review Board administrator
     account

3. Once finished, follow :command:`rb-site`'s instructions to complete your
   installation.

   We'll go over those next.


3. Configure Permissions
========================

Review Board must have write access to the following directories and their
subdirectories:

* :file:`{sitedir}/data`
* :file:`{sitedir}/htdocs/media/uploaded`
* :file:`{sitedir}/htdocs/media/ext`
* :file:`{sitedir}/htdocs/static/ext`

Since Review Board is run by your web server, these must be writable by the
web server's user. If using Apache, this will likely be ``www-data`` or
``apache2``. Please check the user your web server is running as for details.

For example:

.. code-block:: console

    $ cd /var/www/reviews.example.com
    $ chown -R www-data data
    $ chown -R www-data htdocs/media/uploaded
    $ chown -R www-data htdocs/media/ext
    $ chown -R www-data htdocs/static/ext


.. _configuring-selinux:

4. Configuring SELinux (optional)
=================================

Your system may be configured for SELinux_, which is designed to keep your
Linux distribution secure. This is usually enabled by default on
`Red Hat Enterprise`_, Fedora_, and `CentOS Stream`_.

If enabled, you will need to configure additional permissions:

1. Check if SELinux is enabled:

   .. code-block:: console

      $ getenforce
      Enforcing

   If this says "Enforcing", SELinux is currently enabled, and you'll need
   to continue on with the next step.

   If this says "Permissive" or "Disabled", then SELinux is not enabled.
   If you don't plan to enable SELinux, you can skip this section.

2. Grant your web server access to the necessary services:

   .. code-block:: console

      $ setsebool -P httpd_can_connect_ldap 1
      $ setsebool -P httpd_can_network_connect 1
      $ setsebool -P httpd_can_network_connect_db 1
      $ setsebool -P httpd_can_network_memcache 1
      $ setsebool -P httpd_can_sendmail 1
      $ setsebool -P httpd_unified 1

3. Register permissions on your Review Board site directory.

   This tells SELinux what policies to set when applying permissions. They'll
   be applied in the next step.

   We'll use :file:`/var/www/reviews.example.com` for this example:

   .. code-block:: console

      $ semanage fcontext -a -t httpd_sys_content_t \
            "/var/www/reviews.example.com/(conf|htdocs)(/.*)?"
      $ semanage fcontext -a -t httpd_sys_rw_content_t \
            "/var/www/reviews.example.com/(data|tmp|htdocs/static/ext)(/.*)?"
      $ semanage fcontext -a -t httpd_sys_rw_content_t \
            "/var/www/reviews.example.com/htdocs/media/(ext|uploaded)(/.*)?"
      $ semanage fcontext -a -t httpd_log_t \
            "/var/www/reviews.example.com/logs(/.*)?"

4. Apply the new policies to your site directory.

   .. code-block:: console

      $ restorecon -Rv /var/www/reviews.example.com

   .. important::

      You may need to re-run this when :ref:`upgrading your site directory
      <upgrading-sites>`.


If you need any help with SELinux, `reach out to us for support <support_>`_.


.. _SELinux:
   https://docs.fedoraproject.org/en-US/quick-docs/getting-started-with-selinux/
.. _support: https://www.reviewboard.org/support/


.. _configuring-web-server:

5. Configure the Web Server
===========================

Your web server must be configured to serve Review Board. This section
will go over different configurations that are available.

Review Board is known to work well with the following configurations:

* Apache_ + mod_wsgi_ (the most common configuration)
* Nginx_ + Gunicorn_
* Nginx_ + uWSGI_


.. _Apache: https://www.apache.org/
.. _Gunicorn: https://gunicorn.org/
.. _Nginx: https://www.nginx.com/
.. _mod_wsgi: https://modwsgi.readthedocs.io/


.. _configuring-apache:

Apache
------

Apache is commonly used along with mod_wsgi_ to serve Python applications.

Review Board ships a sample :file:`{sitedir}/conf/webconfs/apache-wsgi.conf`
file built for your site. You can use this as-is or customize it. A sample
configuration is also provided below.

How you enable your Apache configuration depends on the Linux distribution.
We'll provide examples, using ``reviews.example.com``.

.. tabs::

   .. code-tab:: console Debian/Ubuntu

      $ cd /etc/apache2
      $ cp /var/www/reviews.example.com/conf/webconfs/apache-wsgi.conf \
           sites-available/reviews.example.com.conf
      $ ln -s sites-available/reviews.example.com.conf \
              sites-enabled/

   .. code-tab:: console RHEL/Fedora/CentOS

      $ cd /etc/httpd/conf.d
      $ cp /var/www/reviews.example.com/conf/webconfs/apache-wsgi.conf \
           reviews.example.com.conf

Once set up, you'll need to restart Apache.


.. note::

    Some Apache installations ship with a default Virtual Host configuration
    that you may want to disable.

    If you visit your Review Board site and see a default Apache page or
    a directory listing, look for a file named :file:`default`,
    :file:`000-default`, or similar, and disable it.


Embedded Mode vs. Daemon Mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

mod_wsgi_ can be run in one of two modes: Embedded mode, or daemon mode.

Embedded mode is simpler to set up, but less flexible. You may want to
start with embedded mode, and switch to daemon mode once you're ready for
production use.


In embedded mode, Review Board is run directly within the Apache process. This
has a couple of important restrictions:

1. After upgrading Review Board, Apache will need to be restarted.

   This may be important to note if your Apache server is also serving other
   high-traffic sites.

2. Apache can only serve one Review Board instance.

   If you need to host multiple instances, you may want to consider daemon
   mode.

In daemon mode, Review Board is run as separate processes, all managed by
Apache. This requires some decisions on the number of processes and threads
needed, which will be based on your system settings, traffic, and other sites
served by Apache.

See the `mod_wsgi configuration guide`_ for additional details.

.. _mod_wsgi configuration guide:
    https://modwsgi.readthedocs.io/en/master/user-guides/configuration-guidelines.html


Sample Apache Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: apache

   <VirtualHost *:80>
     # NOTE: If you change the ServerName or add ServerAlias, you must change
     #       ALLOWED_HOSTS to match. This can be found in:
     #
     #       /var/www/reviews.example.com/conf/settings_local.py
     ServerName reviews.example.com


     # Enable HTTP/2 support, if available.
     Protocols h2 h2c http/1.1


     # If enabling SSL on Apache, uncomment these lines and specify the
     # SSL paths.
     #
     # You may also need to add additional options, depending on your setup.
     # Please refer to the Apache documentation.
     #
     # SSLEngine On
     # SSLCertificateFile /var/www/reviews.example.com/conf/ssl/fullchain.pem
     # SSLCertificateKeyFile /var/www/reviews.example.com/conf/ssl/privkey.pem


     # mod_wsgi Embedded Mode configuration
     #
     # This default configuration enables Embedded Mode, but you can remove
     # this and uncomment Daemon Mode below.
     #
     # Embedded mode is simpler to configure, but daemon mode is recommended
     # in production environments.
     WSGIPassAuthorization On
     WSGIScriptAlias "/" "/var/www/reviews.example.com/htdocs/reviewboard.wsgi/"


     # mod_wsgi Daemon Mode configuration
     #
     # Uncomment this to use daemon mode.
     #
     # Make sure to choose a suitable number of processes and threads for your
     # server.
     #
     # WSGIPassAuthorization On
     # WSGIProcessGroup reviews_example_com
     # WSGIDaemonProcess \
     #     reviews_example_com \
     #     display-name=%{GROUP} \
     #     processes=6 threads=30
     # WSGIScriptAlias \
     #     "/" \
     #     "/var/www/reviews.example.com/htdocs/reviewboard.wsgi" \
     #     process-group=reviews_example_com application-group=%{GROUP}
     # WSGIImportScript \
     #     /var/www/reviews.example.com/htdocs/reviewboard.wsgi \
     #     process-group=reviews_example_com application-group=%{GROUP}


     # Log configuration
     #
     # NOTE: We recommend adding these to your logrotate configuration.
     ErrorLog /var/www/reviews.example.com/logs/error_log
     CustomLog /var/www/reviews.example.com/logs/access_log combined


     # Aliases for serving static files.
     DocumentRoot "/var/www/reviews.example.com/htdocs"
     ErrorDocument 500 /errordocs/500.html
     Alias /media "/var/www/reviews.example.com/htdocs/media"
     Alias /static "/var/www/reviews.example.com/htdocs/static"
     Alias /errordocs "/var/www/reviews.example.com/htdocs/errordocs"
     Alias /robots.txt "/var/www/reviews.example.com/htdocs/robots.txt"

     <Directory "/var/www/reviews.example.com/htdocs">
       AllowOverride All
       Options -Indexes +FollowSymLinks

       <IfVersion < 2.4>
         Allow from all
       </IfVersion>

       <IfVersion >= 2.4>
         Require all granted
       </IfVersion>
     </Directory>

     # Prevent the server from processing or allowing the rendering of
     # certain file types.
     <LocationMatch ^(/(static|media|errordocs))>
       SetHandler None
       Options None

       AddType text/plain .html .htm .shtml .php .php3 .php4 .php5 .phps .asp
       AddType text/plain .pl .py .fcgi .cgi .phtml .phtm .pht .jsp .sh .rb

       <IfModule mod_php5.c>
         php_flag engine off
       </IfModule>
     </LocationMatch>

     <Location "/media/uploaded">
       # Force all uploaded media files to download.
       <IfModule mod_headers.c>
         Header set Content-Disposition "attachment"
       </IfModule>
     </Location>
   </VirtualHost>


.. _configuring-nginx-gunicorn:

Nginx + Gunicorn
----------------

Gunicorn_ is a web server built for efficiently running Python-based web
applications, such as Review Board. It's often paired with another web server,
like Nginx, in the following setup:

1. Nginx listens to ports 80/443, handling all HTTP(S) requests.

   This will serve up static media files and forward anything else to
   Gunicorn over port 8000.

2. Gunicorn listens to port 8000, handling all Review Board requests.

Review Board ships two sample files:

1. :file:`{sitedir}/conf/webconfs/nginx-to-gunicorn.conf`: A configuration
   file for Nginx.

2. :file:`{sitedir}/conf/webconfs/run-gunicorn.sh`: A sample script for running
   Gunicorn.

You can use these as-is for testing or customize them for production. They are
also listed below for reference.

See the official `Gunicorn documentation`_ for installation and deployment
instructions.


.. _Gunicorn documentation: https://gunicorn.org/


Running Gunicorn
~~~~~~~~~~~~~~~~

To manually run Gunicorn for an example :file:`/var/www/reviews.example.com`:

.. code-block:: console

   $ gunicorn \
         --bind=0.0.0.0:8000 \
         --log-level=info \
         --timeout=120 \
         --workers=6 \
         --threads=30 \
         --log-file=/var/www/reviews.example.com/logs/gunicorn.log \
         --env REVIEWBOARD_SITEDIR=/var/www/reviews.example.com \
         reviewboard.wsgi

This is also available as :file:`{sitedir}/conf/webconfs/run-gunicorn.sh`.

You will want to change the workers and threads above. This will be based on
on your system settings and server load.

Gunicorn does not ship as a service. You will likely want to set it up to run
automatically through ``systemd``, ``supervisord``, ``runit``, or another
service monitoring method. See `Gunicorn's Monitoring documentation`_ for
examples.


.. _Gunicorn's Monitoring documentation:
   https://docs.gunicorn.org/en/stable/deploy.html#monitoring


Sample Nginx Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: nginx

   # This is a sample configuration file for a Nginx -> Gunicorn deployment for
   # Review Board.
   #
   # Please go through this file and make sure it's suitable for your setup
   # before using it.

   server {
     # NOTE: If you change the server_name, you must change ALLOWED_HOSTS to
     #     match. This can be found in:
     #
     #     /var/www/reviews.example.com/conf/settings_local.py
     server_name reviews.example.com;

     # If enabling SSL on Nginx, remove the "listen 80" lines below and use
     # configure these settings instead. You will also need to change
     # X-Forwarded-Ssl below.
     #
     # listen [::]:443 ssl http2;
     # listen 443 ssl http2;
     # ssl_certificate /var/www/reviews.example.com/conf/ssl/fullchain.pem;
     # ssl_certificate_key /var/www/reviews.example.com/conf/ssl/privkey.pem;
     listen [::]:80;
     listen 80;

     # Log configuration
     #
     # NOTE: We recommend adding these to your logrotate configuration.
     access_log /var/www/reviews.example.com/logs/nginx_access_log;
     error_log /var/www/reviews.example.com/logs/nginx_error_log;

     location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_redirect        off;

       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Port $server_port;
       proxy_set_header X-Forwarded-Proto $scheme;

       # NOTE: Set this to "on" if using SSL.
       proxy_set_header X-Forwarded-Ssl off;

       client_max_body_size        10m;
       client_body_buffer_size     128k;
       proxy_connect_timeout       90;
       proxy_send_timeout          90;
       proxy_read_timeout          90;
       proxy_headers_hash_max_size 512;
       proxy_buffer_size           4k;
       proxy_buffers               4 32k;
       proxy_busy_buffers_size     64k;
       proxy_temp_file_write_size  64k;
     }

     location /media/ {
       alias /var/www/reviews.example.com/htdocs/media/;
       expires max;
       add_header Cache-Control public;
     }

     location /static/ {
       alias /var/www/reviews.example.com/htdocs/static/;
       expires max;
       add_header Cache-Control public;
     }

     location /errordocs/ {
       alias /var/www/reviews.example.com/htdocs/errordocs/;
       expires 5d;
     }

     location /robots.txt {
       alias /var/www/reviews.example.com/htdocs/robots.txt;
       expires 5d;
     }
   }


.. _configuring-nginx-uwsgi:

Nginx + uWSGI
-------------

uWSGI_ is another web server built for efficiently running Python-based web
applications, such as Review Board. It's often paired with another web server,
like Nginx, in the following setup:

1. Nginx listens to ports 80/443, handling all HTTP(S) requests.

   This will serve up static media files and forward anything else to
   uWSGI over a local UNIX socket.

2. uWSGI listens on the socket, handling all Review Board requests.

Review Board ships two sample files:

1. :file:`{sitedir}/conf/webconfs/nginx-to-uwsgi.conf`: A configuration
   file for Nginx.

2. :file:`{sitedir}/conf/webconfs/uwsgi.ini`: A configuration file for uWSGI.

You can use these as-is for testing or customize them for production. They are
also listed below for reference.

See the official `uWSGI documentation`_ for installation and deployment
instructions.


.. _uWSGI: https://uwsgi-docs.readthedocs.io/
.. _uWSGI documentation:
   https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html


Running uWSGI
~~~~~~~~~~~~~

To manually run uWSGI for an example
:file:`/var/www/reviews.example.com/conf/webconfs/uwsgi.ini`:

.. code-block:: console

   $ uwsgi /var/www/reviews.example.com/conf/webconfs/uwsgi.ini

You will want to change the workers and threads in that file. This will be
based on on your system settings and server load.

uWSGI does not ship as a service. You will likely want to set it up to run
automatically through a service monitoring method. See the
`uWSGI systemd documentation`_ for examples.


.. _uWSGI systemd documentation:
   https://uwsgi-docs.readthedocs.io/en/latest/Systemd.html


Sample uWSGI Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   [uwsgi]
   module = reviewboard.wsgi:application
   env=REVIEWBOARD_SITEDIR=/var/www/reviews.example.com

   master = true
   processes = 6
   threads = 30

   socket = /var/www/reviews.example.com/data/uwsgi.sock
   cmod-socket = 664
   vacuum = true

   die-on-term = true


Sample Nginx Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: nginx

   # This is a sample configuration file for a Nginx -> uWSGI deployment for
   # Review Board.
   #
   # Please go through this file and make sure it's suitable for your setup
   # before using it.

   server {
     # NOTE: If you change the server_name, you must change ALLOWED_HOSTS to
     #     match. This can be found in:
     #
     #     /var/www/reviews.example.com/conf/settings_local.py
     server_name reviews.example.com;

     # If enabling SSL on Nginx, remove the "listen 80" lines below and use
     # configure these settings instead:
     #
     # listen [::]:443 ssl http2;
     # listen 443 ssl http2;
     # ssl_certificate /var/www/reviews.example.com/conf/ssl/fullchain.pem;
     # ssl_certificate_key /var/www/reviews.example.com/conf/ssl/privkey.pem;
     listen [::]:80;
     listen 80;

     # Log configuration
     #
     # NOTE: We recommend adding these to your logrotate configuration.
     access_log /var/www/reviews.example.com/logs/nginx_access_log;
     error_log /var/www/reviews.example.com/logs/nginx_error_log;

     location / {
       include uwsgi_params;
       uwsgi_pass unix:/var/www/reviews.example.com/data/uwsgi.sock;
     }

     location /media/ {
       alias /var/www/reviews.example.com/htdocs/media/;
       expires max;
       add_header Cache-Control public;
     }

     location /static/ {
       alias /var/www/reviews.example.com/htdocs/static/;
       expires max;
       add_header Cache-Control public;
     }

     location /errordocs/ {
       alias /var/www/reviews.example.com/htdocs/errordocs/;
       expires 5d;
     }

     location /robots.txt {
       alias /var/www/reviews.example.com/htdocs/robots.txt;
       expires 5d;
     }
   }


.. _configuring-cron:

6. Configure Task Scheduling
============================

Cron is used for automatically running periodic maintenance tasks, including:

* Updating the search index
* Clearing expired login sessions

Your site directory contains a sample Crontab file at
:file:`{sitedir}/conf/cron.conf`. You can customize this and then register
it with Cron as the web server:

.. code-block:: console

   $ sudo -u <web_server_user> crontab /path/to/sitedir/conf/cron.conf

For example:

.. code-block:: console

   $ sudo -u apache2 crontab /var/www/reviews.example.com/conf/cron.conf

A sample Crontab configuration looks like:

.. tabs::

   .. code-tab:: shell Python Virtual Environments

      # Update search index every 10 minutes
      0,10,20,30,40,50 * * * * "/opt/reviewboard/bin/rb-site" \
          manage "/var/www/reviews.example.com" update_index -- -a 1

      # Clear expired sessions once a day at 2am
      0 2 * * * "/opt/reviewboard/bin/rb-site" \
          manage "/var/www/reviews.example.com" clearsessions

   .. code-tab:: shell System Installs

      # Update search index every 10 minutes
      0,10,20,30,40,50 * * * * "/usr/bin/python3.11" "/usr/bin/rb-site" \
          manage "/var/www/reviews.example.com" update_index -- -a 1

      # Clear expired sessions once a day at 2am
      0 2 * * * "/usr/bin/python3.11" "/usr/bin/rb-site" \
          manage "/var/www/reviews.example.com" clearsessions


You're Done!
============

Now that Review Board is installed and your site directory is created,
you can start your web server and navigate to Review Board.

You'll want to configure Review Board and connect it to any source code
management systems you're using.

To learn more:

* :ref:`Configuring Review Board <configuration-topics>`
* :ref:`Managing Repositories <repositories>`
* :ref:`Administration Guide <administration-guide>`


.. _CentOS Stream: https://www.centos.org/
.. _Debian: https://www.debian.org/
.. _Fedora: https://getfedora.org/
.. _Red Hat Enterprise: https://www.redhat.com/en
.. _Ubuntu: https://www.ubuntu.com/
