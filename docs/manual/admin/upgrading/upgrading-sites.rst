.. _upgrading-sites:

============================
Upgrading Review Board Sites
============================

After upgrading Review Board, you will need to upgrade each :term:`site
directory`. This performs the following actions:

* Applies new changes to your database
* Adds new media files to your site directory
* Migrates data for the new version

Minor version upgrades are generally very quick, completing in seconds.

Major version upgrades may take longer, depending on your database.

We **strongly recommend** backing up your database and testing the upgrade on
a staging server, in case anything goes wrong!


.. tip::

   Enable read-only mode from the :ref:`general-settings` page to alert your
   users before performing an upgrade.

   This will prevent users from posting changes or working on reviews during
   upgrade.

   Don't forget to disable read-only mode once the upgrade is finished!


To upgrade a Review Board site:

1. Run:

   .. tabs::

      .. group-tab:: Python Virtual Environments

         .. code-block:: console

            $ /opt/reviewboard/bin/rb-site upgrade /path/to/sitedir

         For example:

         .. code-block:: console

            $ /opt/reviewboard/bin/rb-site upgrade /var/www/reviews.example.com

      .. group-tab:: System Installs

         .. code-block:: console

            $ rb-site upgrade /path/to/sitedir

         For example:

         .. code-block:: console

            $ rb-site upgrade /var/www/reviews.example.com

   This will report the progress of the upgrade. If it fails to report a
   successful upgrade, stop and `reach out to support <support_>`_ for help.

2. If you're :ref:`using SELinux <configuring-selinux>`, re-apply your site
   permissions:

   .. code-block:: console

      $ restorecon -Rv /path/to/sitedir

   For example:

   .. code-block:: console

      $ restorecon -Rv /var/www/reviews.example.com

   This requires that you followed the SELinux steps linked above.

2. Restart your web server.

Your site should be ready!


.. _support: https://www.reviewboard.org/support/
