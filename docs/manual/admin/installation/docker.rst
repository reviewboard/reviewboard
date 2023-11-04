.. _installation-docker:

======================
Installing with Docker
======================

.. versionadded:: 3.0.21

Review Board ships official Docker_ images, helping you quickly get your
infrastructure set up with minimal effort.

We've designed these images to be extensible. You can deploy your own
extensions and customize your installation through environment variables on
launch, by rebuilding our image with your own settings, or by creating a new
``Dockerfile`` built on top of ours.


.. _Docker: https://www.docker.com/


Getting Started
===============

We'll walk you through the basics of setting up Review Board on Docker in two
different ways:

1. Launching the Review Board image by itself using :ref:`docker run
   <installation-docker-run>`.

2. Launching the image along with a database, web server, and memcached using
   :ref:`docker-compose <installation-docker-compose>`.

You'll also see how you can customize the Docker image for your own needs.


Before You Begin
----------------

Plan Your Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~

The Review Board Docker image requires **all** of the following:

* A database server (Postgres, MySQL, or MariaDB)
* A memcached server
* A web server (such as Apache or Nginx) that can proxy to the Docker image's
  Gunicorn server and serve static media files
* A local file system path to store the Review Board site directory (which
  will contain the static media files to serve)

If using :ref:`docker-compose <installation-docker-compose>` with our sample
configurations, this will be all be taken care of for you.


.. admonition:: A dedicated web server is required!

   The Review Board Docker instance will **not** serve up static media
   (CSS, JavaScript, or images). You will need a web server in front of it,
   such as Nginx (recommended) or Apache.


Choose a Version
~~~~~~~~~~~~~~~~

Our Docker images are available in the following forms:

* ``beanbag/reviewboard:latest``
  -- The latest stable release of Review Board.
* :samp:`beanbag/reviewboard:{X.Y}`
  -- The latest stable release in a major version series (e.g., 5.0, 6.0).
* :samp:`beanbag/reviewboard:{X.Y.Z}`
  -- A specific release of Review Board (e.g., 5.0.6, 6.0.1).

See `our Docker repository`_ for all available versions.

.. warning::

   If you're using multiple Review Board Docker containers, they must all
   use the *exact same version*. Plan your deployment accordingly.


.. _our Docker repository: https://hub.docker.com/r/beanbag/reviewboard


.. _installation-docker-run:

Using Docker Run
----------------

First, make sure you've set up memcached and a database server. Create a new
database and a user account that can write to it.

Once those are set up, you can start your backend Review Board server.

.. note::

   You won't be accessing Review Board through this webserver.

   This is the backend server, handling Review Board requests. It does not
   serve up CSS, JavaScript, or images, and is not meant to be accessed
   directly. You'll need to configure a frontend web server, such as Nginx.

   Make sure to proceed to :ref:`docker-serving-content` below to configure
   the frontend web server.


Creating a Review Board server is easy. You can use our :ref:`docker-compose
<installation-docker-compose>` instructions, or create it manually by
running:

.. code-block:: shell

    $ docker pull beanbag/reviewboard:X.Y.Z
    $ docker run -P \
                 --name <name> \
                 -v <local_path>:/site \
                 -e DOMAIN=<domain> \
                 -e COMPANY=<company> \
                 -e MEMCACHED_SERVER=<hostname>:11211 \
                 -e DATABASE_TYPE=<mysql|postgresql> \
                 -e DATABASE_SERVER=<hostname> \
                 -e DATABASE_USERNAME=<username> \
                 -e DATABASE_PASSWORD=<password> \
                 -e DATABASE_NAME=<database_name> \
                 beanbag/reviewboard:X.Y.Z


For example:

.. code-block:: shell

    $ docker pull beanbag/reviewboard:4.0.4
    $ docker run -P \
                 --name <name> \
                 -v /var/www/reviewboard:/site \
                 -e DOMAIN=reviews.corp.example.com \
                 -e COMPANY="My Company" \
                 -e MEMCACHED_SERVER=db.corp.example.com:11211 \
                 -e DATABASE_TYPE=postgresql \
                 -e DATABASE_SERVER=db.corp.example.com \
                 -e DATABASE_USERNAME=reviewboard \
                 -e DATABASE_PASSWORD=reviewboard12345 \
                 -e DATABASE_NAME=reviewboard \
                 beanbag/reviewboard:4.0.4


Some of these settings aren't required, but are recommended. We'll cover all
the configuration options below.

Your new Review Board server should start up, create a new site directory,
and populate your database.

See the `docker-run documentation`_ for more information.


.. _docker-run documentation: https://docs.docker.com/engine/reference/run/


.. _docker-serving-content:

Serving Content
~~~~~~~~~~~~~~~

The backend Review Board server will be accessible over port 8080. You can
change this by passing :samp:`-p {port}:8080` to map a custom local port to
Review Board's port 8080.

You'll need a frontend web server (such as the `nginx Docker image`_), to
forward traffic to that backend port, and to serve up the following URLs:

* ``/static/`` (pointing to the site directory's ``htdocs/static/``)
* ``/media/`` (pointing to the site directory's ``htdocs/media/``)
* ``/robots.txt`` (pointing to the site directory's ``htdocs/robots.txt``)

You'll need to mount your Review Board site directory volume to an appropriate
directory (such as ``/var/www/reviewboard``, as shown below).

If using Nginx, your configuration may look something like:

.. code-block:: nginx

    upstream reviewboard {
        server reviewboard-docker1.corp.example.com:8080;
    }

    server {
        server_name reviews.corp.example.com

        # If enabling SSL on Nginx, remove the "listen ${NGINX_PORT}" lines
        # below and use these settings instead. You will also need
        # to change X-Forwarded-Ssl below.
        #
        # listen [::]:443 ssl http2;
        # listen 443 ssl http2;
        # ssl_certificate /var/www/reviewboard/conf/ssl/fullchain.pem;
        # ssl_certificate_key /var/www/reviewboard/conf/ssl/privkey.pem;
        listen [::]:80;
        listen 80;

        root /var/www/reviewboard/htdocs;

        location / {
            proxy_pass http://reviewboard;
            proxy_redirect off;

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
            alias /var/www/reviewboard/htdocs/media/;
            expires max;
            add_header Cache-Control public;
        }

        location /static/ {
            alias /var/www/reviewboard/htdocs/static/;
            expires max;
            add_header Cache-Control public;
        }

        location /errordocs/ {
            alias /var/www/reviewboard/htdocs/errordocs/;
            expires 5d;
        }

        location /robots.txt {
            alias /var/www/reviewboard/htdocs/robots.txt;
            expires 5d;
        }
    }


See :ref:`Configuring the Web Server <configuring-web-server>` for additional
web server configuration examples.


.. _nginx Docker image: https://hub.docker.com/_/nginx


.. _installation-docker-compose:

Using Docker Compose
--------------------

:command:`docker-compose` can help you define and launch all the services
needed for your Review Board deployment.

We have :rbtree:`sample docker-compose.yaml files <contrib/docker/examples/>`
and related configuration that you can download and launch:

.. code-block:: shell

    # MySQL configuration
    $ docker-compose -f docker-compose.mysql.yaml -p reviewboard_mysql up

    # Postgres configuration
    $ docker-compose -f docker-compose.postgres.yaml -p reviewboard_postgres up

You should make a copy of these and modify them for your needs. See the
`docker-compose documentation`_ for more information.

.. _docker-compose documentation: https://docs.docker.com/compose/


.. _installation-docker-cron:

Setting up Cron
---------------

.. versionadded:: 4.0.4

If your container needs to run tasks periodically (such as :ref:`search
indexing <search-indexing>`), you'll need to enable cron support.

This can be enabled by passing a ``REVIEWBOARD_CRONTAB`` environment variable
when launching a container. This should be set to the location of a crontab
file.

By default, the image ships with a :file:`/site/conf/cron.conf` file, which
will enable search indexing and user session cleanup. To activate this, you
would pass:

.. code-block:: shell

    REVIEWBOARD_CRONTAB=/site/conf/cron.conf

For instance, in :file:`docker-compose.yaml`:

.. code-block:: yaml

   reviewboard:
       environment:
           - REVIEWBOARD_CRONTAB=/site/conf/cron.conf

If you provide your own crontab file (such as through a custom image or
a bind mount), you can pass the path to that file within the container.


Configuration
=============

Your Review Board container can be customized through environment variables
on launch.

Most variables only apply when launching the container for the first time, as
they're responsible for setting up your initial Review Board configuration
file and site directory.


Web Server Configuration
------------------------

These variables apply any time a container is launched. You can stop a
container and launch with the new settings.

``NUM_WORKERS``
    The number of worker processes for the web server, Gunicorn_.

    This defaults to 4.

``NUM_THREADS``
    The number of threads per worker process for the web server.

    This defaults to 20.

``REQUEST_TIMEOUT``
    The number of seconds until a request times out.

    You may need to increase this if you find that your repositories are
    slow to respond.

    This defaults to 120 seconds.

``GUNICORN_FLAGS``
    Additional flags to pass to the Gunicorn_ executable.

    See the `Gunicorn settings documentation`_.


.. tip::

   To determine the total number of requests that can be handled at the same
   time, multiply ``NUM_WORKERS`` by ``NUM_THREADS``.

   You will need to determine which numbers work best for you, based on the
   number of available CPUs and RAM.


.. _Gunicorn: https://gunicorn.org/
.. _Gunicorn settings documentation:
   https://docs.gunicorn.org/en/latest/settings.html


Task Scheduling
---------------

``REVIEWBOARD_CRONTAB``
    The path to a crontab file containing periodic tasks to run.

    See :ref:`installation-docker-cron`.

    .. versionadded:: 4.0.4


Initial Configuration
---------------------

These variables only apply on first launch for a container. To change the
settings, remove your old containers and launch new ones.


Server Information
~~~~~~~~~~~~~~~~~~

``COMPANY``
    The name of your company.

    This can be changed in the Review Board administration UI after launch.

``DOMAIN``
    The fully-qualified domain name for your Review Board server.

    The server will only respond to requests sent to this domain.

    This *cannot* include ``http://`` or ``https://``.


Database
~~~~~~~~

``DATABASE_TYPE``
    The type of database to use for Review Board.

    This can be either ``mysql`` or ``postgresql``. It defaults to
    ``postgresql``.

``DATABASE_SERVER``
    The address to the database server. This must be reachable in the
    container.

    This defaults to ``db``, the name defined in our sample
    :file:`docker-compose.yaml` files.

``DATABASE_NAME``
    The name of the database on the database server.

    This defaults to ``db``, and must already be created before launching a
    container.

``DATABASE_USERNAME``
    The username used to connect to and modify the database identified by
    ``DATABASE_NAME``.

    This defaults to ``reviewboard``.

``DATABASE_PASSWORD``
    The password belonging to the database user.


File System
~~~~~~~~~~~

``REVIEWBOARD_GROUP_ID``
    The ID of the group that will own server-writable files and directories
    in the site directory.

    This defaults to ``1001``, and should be changed if you're working with
    an existing site directory.

``REVIEWBOARD_USER_ID``
    The ID of the user that will own server-writable files and directories in
    the site directory.

    This defaults to ``1001``, and should be changed if you're working with
    an existing site directory.


Memcached
~~~~~~~~~

``MEMCACHED_SERVER``
    The address to the memcached server. This must be reachable in the
    container.

    This defaults to ``memcached:11211``, using the name defined in our sample
    :file:`docker-compose.yaml` files.


Installing Extensions
=====================

Our official Docker image comes with `Power Pack`_ and `Review Bot`_
pre-installed.

If you need to install additional extensions, you'll need to build an image.

1. Create a directory where your :file:`Dockerfile` will live.

2. If you're installing custom extensions, create a :file:`packages/`
   directory inside it and place your extension :file:`.whl` packages in it.

3. Create a new :file:`Dockerfile` containing:

   .. code-block:: dockerfile

       # Replace <version> with the Review Board version you want to use.
       FROM beanbag/reviewboard:<version>

       # You now have two options for installing packages:
       #
       # 1) If you want to install publicly-available packages:
       RUN    set -ex \
           && pip install --no-cache rbmotd==1.0.1

       # 2) If you want to install your own private packages:
       COPY packages/*.whl /tmp/packages
       RUN    set -ex \
           && pip install --no-cache --find-links=/tmp/packages \
                  MyPackage1==1.0 MyPackage2==2.0.4 \
           && rm -rf /tmp/packages


3. Build the package:

   .. code-block:: shell

       $ docker build -t my-reviewboard .

   See the `docker build documentation`_ for more information on this command.

4. Launch a container from your new image:

   .. code-block:: shell

       $ docker run -P \
                    --name ... \
                    -v ... \
                    -e ... \
                    my-reviewboard


.. _docker build documentation:
   https://docs.docker.com/engine/reference/commandline/build/
.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/
