.. _database-management:

===================
Database Management
===================

The Database section of the :ref:`Administration UI <administration-ui>`
allows you to view and modify the actual contents of the Review Board database
in a simple, human-readable fashion.

With the exception of the `management tables`_, most tables are used for
`data storage`_ only and should not be modified unless you know what you're
doing.

.. warning:: If not handled carefully, modifying entries in the database
             can lead to data loss or corruption.


Management Tables
=================

The management tables are the areas of the database you're most likely to
modify in your installation.


+-------------------------+----------------------------------------------+
| Table                   | Description                                  |
+=========================+==============================================+
| :ref:`Default reviewers | Default reviewers applied to review requests |
| <default-reviewers>`    |                                              |
+-------------------------+----------------------------------------------+
| :ref:`Groups            | User permission/authentication groups        |
| <permission-groups>`    |                                              |
+-------------------------+----------------------------------------------+
| :ref:`Repositories      | Source code repository configuration         |
| <repositories>`         |                                              |
+-------------------------+----------------------------------------------+
| :ref:`Review groups     | Target reviewer groups                       |
| <review-groups>`        |                                              |
+-------------------------+----------------------------------------------+
| Sites                   | Basic site information                       |
+-------------------------+----------------------------------------------+
| :ref:`Users <users>`    | User account information                     |
+-------------------------+----------------------------------------------+


.. _data storage:

Data Storage Tables
===================

As the name suggests, data storage tables contain data for such things as
review requests, raw site settings, diffs, and so on. These should usually be
left untouched, but there may be occasions when you'll need to fix something
for another user by modifying one of these tables.

The table below is grouped by the sections listed in the Database page in the
:ref:`Administration UI <administration-ui>`.


======================== ==================================================
Table                    Description
======================== ==================================================
**Accounts**
------------------------ --------------------------------------------------
Local site profiles      User profile and configuration specific to
                         partitioned :term:`local sites`.
Profiles                 General site-wide user profile and configuration
Review request visits    Tracking of review request visits for user
                         accounts.

**Attachments**
------------------------ --------------------------------------------------
File attachments         File attachments associated with review requests.

**Auth**
------------------------ --------------------------------------------------
Groups                   User permission/authentication groups.
Users                    User account information.

**Changedescs**
------------------------ --------------------------------------------------
Change descriptions      Review request change description logging.

**Diffviewer**
------------------------ --------------------------------------------------
Diff set histories       Groupings of revisioned diff sets, each owned by a
                         review request.
Diff sets                A revisioned set of file diffs owned by a diff set
                         history.
File diffs               Per-file diffs, along with the path and revision
                         of the referenced files in the repository.

**Django_Evolution**
------------------------ --------------------------------------------------
Evolutions               A history of database migrations applied.
                         **Do not modify this!**
Versions                 A history of database schemas.
                         **Do not modify this!**

**Reviews**
------------------------ --------------------------------------------------
Comments                 Comments made on diffs.
Default reviewers        Default reviewers applied to review requests.
File attachment comments Comments made on file attachments.
Review groups            Target reviewer groups.
Review request drafts    Drafts of review requests.
Review requests          All review requests, public and private.
Reviews                  All reviews, public and private.
Screenshot comments      Comments made on screenshots.
Screenshots              All uploaded screenshots.

**Scmtools**
------------------------ --------------------------------------------------
Tools                    All registered SCMTools for talking to repositories.

**Site**
------------------------ --------------------------------------------------
Local sites              Partitioned :term:`local sites`.

**Siteconfig**
------------------------ --------------------------------------------------
Site configurations      Stored configuration for the site.
                         **Do not modify this!**

**Sites**
------------------------ --------------------------------------------------
Sites                    Basic site information.

======================== ==================================================
