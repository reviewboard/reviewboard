.. _repository-hosting-azure-devops-services:
.. _repository-hosting-visualstudio:

==================================
Azure DevOps Services Repositories
==================================

.. note::

   Azure DevOps Services support requires a license of `Power Pack`_. You
   can `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on
:rbintegration:`Azure DevOps Services <visual-studio-team-services>`
(formerly Visual Studio Team Services and Visual Studio Online) repositories.
Existing commits in a repository can be browsed and put up for review.

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

To configure an Azure DevOps Services repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Azure DevOps Services`
from the :guilabel:`Hosting service` field.


Step 1: Link Your Azure DevOps Services Account
-----------------------------------------------

In order for Review Board to connect to your Azure DevOps Services
account, you need to create a Personal Access Token. From your account on
https://dev.azure.com, click on the :guilabel:`User settings` icon in the
upper right, then choose :guilabel:`Personal access tokens` from the menu.
The token will need the :guilabel:`Full` scope under the :guilabel:`Code`
section.

Then in the Review Board repository configuration, fill out the following
fields:

:guilabel:`Account username`:
    The username used to log into your Azure DevOps Services account. This
    may be left blank.

:guilabel:`Account password`:
    The Personal Access Token that you configured.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    Choose ``Azure DevOps / TFS (Git)`` for Git repositories or
    ``Azure DevOps / TFS (TFVC)`` for TFVC repositories.

:guilabel:`Azure DevOps organization name`:
    The organization name for your team. For example, if your URL is
    ``https://dev.azure.com/example`` (or the legacy
    ``https://example.visualstudio.com``), enter ``example``.

:guilabel:`Azure DevOps project name`:
    The name of your project. For example, if your clone URL is:

    ``https://MyOrganization@dev.azure.com/MyOrganization/MyProject/_git/MyRepo``

    Then your project name would be ``MyProject``.

    This is only required for Git repositories, and is not used for TFVC.

:guilabel:`Azure DevOps repository name`:
    The name of your repository. For example, if your clone URL is:

    ``https://MyOrganization@dev.azure.com/MyOrganization/MyProject/_git/MyRepo``

    Then your repository name would be ``MyRepo``.

    This is only required for Git repositories, and is not used for TFVC.


Step 3: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. At the time of this writing,
support for bug trackers on Azure DevOps Services is not supported.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Azure DevOps Services' own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
