Example Docker Compose for Review Board
=======================================

This directory contains some sample files for `docker-compose`, helping you
get [Review Board](https://www.reviewboard.org) up and running fast;

* `docker-compose.mysql.yaml`: A configuration using MySQL for the database.
* `docker-compose.postgres.yaml`: A configuration using Postgres for the
  database.

To get started, see the instructions in these files, or keep reading.

Please note that these are only examples. You'll want to tailor these to your
infrastructure. We can help you design this under a
[support contract](https://www.reviewboard.org/support/).


Instructions
------------

1. Copy the following to a new directory:

    * `docker-compose.yaml` (based on your chosen configuration)
    * `nginx_templates/`
    * `postgres/` (if using `docker-compose.postgres.yaml`)

2. Change the hostname below to a fully-qualified domain name you'll be
   able to use for the server. Search for `localhost` for the default.

   See `DOMAIN` and `NGINX_HOST` in the `docker-compose.yaml` file for the
   settings.

   To temporarily test a hostname, you can modify `/etc/hosts` on Linux
   or macOS and alias it to your IP address.

   **NOTE:** If you change this later, you will need to edit the sitedir
   volume's `conf/settings_local.py` to include the new hostname in
   `ALLOWED_HOSTS`, and change the hostname in Review Board's **Admin UI ->
   General Settings** page.

3. Change the database passwords below to something secure.

   For MySQL, see `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, and
   `DATABASE_PASSWORD` in the `docker-compose.yaml` file.

   For Postgres, see `POSTGRES_PASSWORD`, `POSTGRES_RB_PASSWORD`, and
   `DATABASE_PASSWORD`.

4. Change the company name for your server.

   See `COMPANY` in the `docker-compose.yaml` file.

5. Go through this file and search for `CHANGEME` for other settings you
   may want to change.

6. Run: `docker-compose up`

7. Access `http://<hostname>/`


Data Storage
------------

This example configuration will create two directories for storage:

* `db_data/`

  The database contents.

  This *cannot* be shared across multiple database servers.

* `sitedir/`

  Review Board site directory content (static media files, data, and
  configuration).

  This *can* be shared across multiple Review Board server instances, and
  Nginx instances.


Production Use
--------------

As these are only sample configurations, you'll likely want to make other
changes for production use, such as:

1. Setting up a load balancer with SSL enabled.

2. Separating out the database and memcached server for other Review Board
   instances to use.

3. Making sure only port 80 is accessible on the network.

These are all beyond the scope of these example configurations.
[We can help](https://www.reviewboard.org/support/) plan your architecture.

You should also go through your configuration file, read the comments, and
change any configuration needed for your install.


Further Reading
---------------

See the [Review Board Docker documentation](https://www.reviewboard.org/docs/manual/latest/admin/installation/docker/)
to help configure your Review Board Docker containers.
