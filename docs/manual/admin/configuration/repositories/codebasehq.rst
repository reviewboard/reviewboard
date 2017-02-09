.. _repository-hosting-codebasehq:

========================
Codebase HQ Repositories
========================

Review Board supports posting and reviewing code on :rbintegration:`Codebase
HQ <codebase>` repositories.

The following types of Codebase HQ repositories are supported:

* Git
* Mercurial
* Subversion

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a Codebase HQ repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Codebase HQ` from the
:guilabel:`Hosting type` field.


Step 1: Link Your Codebase HQ Account
-------------------------------------

You will need to link an account on Codebase HQ to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username, password, API key, and Codebase HQ domain handy.

Fill out the following fields:

:guilabel:`Account username`:
    The username used to log into your Codebase HQ account. This is *not*
    your e-mail address.

    If you're unsure of your password, click the Settings icon in the
    top-right of your Codebase HQ page (the one that looks like a wrench)
    and then click :guilabel:`My Profile`. You'll see your username.

:guilabel:`Account password`:
    The password used to log into your Codebase HQ account.

    Due to some requirements when accessing your repositories, your password
    will be stored in encrypted form in the database.

:guilabel:`API key`:
    The API key configured for your account.

    You can see your API key in the :guilabel:`API Credentials` section
    of your My Profile page.

:guilabel:`Codebase domain`:
    The subdomain of your Codebase HQ account. This is the ``<your-domain>``
    of :samp:`{<your-domain>}.codebasehq.com`.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    The type of repository you're adding. This can be either "Git",
    "Mercurial", or "Subversion".

:guilabel:`Project name`:
    The name of the project owning the repository.

:guilabel:`Repository name`:
    The name (identifier) of the repository. This must be the name found in
    the checkout/clone URL, not the displayed name (for instance, "myrepo"
    and not "My Repository").


Step 3: Choose a Bug Tracker
----------------------------

Review Board 2.5.8 and higher support using Codebase HQ's ticket tracker. If
you want to use the ticket tracker for your repository, you can simply enable
the :guilabel:`Use hosting service's bug tracker` option.

For older versions, you can choose :guilabel:`(Custom Bug Tracker)` and
specify
:samp:`https://{<your-domain>}.codebasehq.com/projects/{<your-project>}/tickets/%s`,
where ``<your-domain>`` matches your :guilabel:`Codebase domain` field and
``<your-project>`` matches your :guilabel:`Project name` field.

If you're using a separate bug tracker, or a separate project on Codebase HQ,
you can leave the checkbox unchecked and choose a bug tracker from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Codebase HQ's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
