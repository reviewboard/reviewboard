.. _repository-hosting-azure-devops-server:

=========================================================
Azure DevOps Server / Team Foundation Server Repositories
=========================================================

.. note::

   Azure DevOps Server support requires a license of `Power Pack`_. You
   can `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on
:rbintegration:`Azure DevOps Server <azure-devops-server>` (formerly Team
Foundation Server) repositories. Existing commits in a repository can be
browsed and put up for review.

The following types of repositories are supported:

* Git
* TFVC

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _download a trial license: https://www.reviewboard.org/powerpack/trial/
.. _purchase a license: https://www.reviewboard.org/powerpack/purchase/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure an Azure DevOps Server repository, first proceed to :ref:`add the
repository <adding-repositories>` and select
:guilabel:`(None - Custom Repository)` for the :guilabel:`Hosting service`.
For Git repositories, select :guilabel:`Azure DevOps / TFS (Git)` for the
:guilabel:`Repository type`. For TFVC repositories, select
:guilabel:`Azure DevOps / TFS (TFVC)`.

Note that you *must* use the :guilabel:`Azure DevOps / TFS (Git)` repository
type for Git repositories, and not plain :guilabel:`Git`.


Step 1: Link Your Azure DevOps Server Account
---------------------------------------------

If you are using TFS 2018+ or Azure DevOps Server, you'll need to create a
Personal Access Token to authenticate.

On Team Foundation Server, open the collection in a browser and select your
account icon in the upper right, then click :guilabel:`Security`. On the next
page, select `Personal access tokens`. On Azure DevOps Server, select your
account icon in the upper right and choose :guilabel:`Personal access tokens`
from the menu.

From this page, generate a new Personal Access token for use with Review Board.
Note that you'll need to copy this immediately, as it will not be visible after
you leave the page.

On TFS 2015 and below, use your domain login credentials for
:guilabel:`Username` and :guilabel:`Password`.

Then in the Review Board repository configuration, fill out the following
fields:

:guilabel:`Username`:
    The username used to log into your Azure DevOps Server account. This
    may be left blank.

:guilabel:`Password`:
    The Personal Access Token that you configured.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Depending on the repository type, you'll need to fill out the following fields:

Git Repositories
~~~~~~~~~~~~~~~~

:guilabel:`Path`:
    The fully-qualified clone path for the repository (i.e.
    ``http://tfs:8080/tfs/DefaultCollection/_git/git-project``).
    This should match the repository's "Clone Repository" path.


TVFC Repositories
~~~~~~~~~~~~~~~~~

:guilabel:`Path`:
    The fully-qualified path to the Azure DevOps Server or TFS server and
    collection (i.e. ``http://tfs:8080/tfs/DefaultCollection``). This should
    match the path listed in the Administration Console or the collection
    reported when running :command:`tf workfold`.


Step 3: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. At the time of this writing,
support for bug trackers on Azure DevOps Server is not supported.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Azure DevOps Server's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
