.. _repository-hosting-gerrit:

===================
Gerrit Repositories
===================

Review Board supports posting and reviewing code on
:rbintegration:`Gerrit <gerrit>` repositories.

Existing commits in a repository can be browsed and put up for review. Change
requests in Gerrit, however, are not currently supported.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` for
more information.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a Gerrit repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Gerrit` from the
:guilabel:`Hosting type` field.


Step 1: Installing gerrit-reviewboard-plugin
--------------------------------------------

Review Board requires additional API endpoints to effectively use Gerrit as a
hosting service. We provide a `Gerrit plugin`_ which, when
installed, allows Gerrit to function as a hosting service.

Download the plugin into your Gerrit server's plugin directory at
:file:`/path/to/gerrit/plugins` and restart the Gerrit server.

.. _Gerrit plugin:
   https://downloads.reviewboard.org/releases/gerrit-reviewboard-plugin/


Step 2: Link your Gerrit Account
--------------------------------

You will need to link an account on Gerrit to Review Board, so that Review
Board can access content from the repository. If you've already linked an
account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and HTTP password handy.

Fill out the following fields:

:guilabel:`Account Username`:
   Your Gerrit username.

   You can find this on your Gerrit instance by navigating to
   :guilabel:`Settings -> HTTP Password``.

:guilabel:`Account Password`:
   Your account's HTTP password.

   You can find this on your Gerrit instance by navigating to
   :guilabel:`Settings -> HTTP Password`.

The account will be linked when the repository is saved. If there are errors
authenticating the user, you will be prompted to fix them.


Step 3: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Gerrit URL`:
   The URL to the root of your Gerrit instance.

:guilabel:`SSH port`:
   The port configured for SSH access to your Gerrit instance.

:guilabel:`Project name`:
   The name of the project on your Gerrit instance.


Step 4: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. Gerrit, at the time of
this writing, does not provide one, but you can choose one on another service
or provide a custom URL to your own bug tracker.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 5: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Gerrit's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 6: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
