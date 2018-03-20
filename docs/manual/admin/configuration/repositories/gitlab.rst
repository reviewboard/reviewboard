.. _repository-hosting-gitlab:

===================
GitLab Repositories
===================

Review Board supports posting and reviewing code on :rbintegration:`GitLab
<gitlab>` repositories.

Existing commits in a repository can be browsed and put up for review. Pull
requests, however, are not currently supported (though planned for a future
release).

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` for
more information.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a GitLab repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`GitLab` from the
:guilabel:`Hosting type` field.


Step 1: Link Your GitLab Account
--------------------------------

You will need to link an account on GitLab to Review Board, so that Review
Board can access content from the repository. If you've already linked an
account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your GitLab server. This should *not* have a
    trailing ``/``.

    If you're using `GitLab.com <https://gitlab.com>`_ for your project,
    provide ``https://gitlab.com``.

:guilabel:`Account username`:
    The username used to log into your GitLab account. This is *not* your
    e-mail address.

:guilabel:`API Token`:
    An API token that Review Board will use to communicate with GitLab.

    You can create this token by going to your GitLab instance and navigating
    to :guilabel:`Settings -> Access Tokens -> Personal Access Tokens`. The
    token will need the ``api`` scope.

    On older versions of GitLab, you can find your API token by navigating to
    :guilabel:`Profile Settings -> Account -> Private Token`.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository plan`:
    This specifies the type of the repository, whether it's owned by your user
    or by another group. You'll have one of the following choices:

    * **Personal:** The repository is owned by the linked user account.

    * **Group:** The repository is owned by a group account. You'll need to
      specify the group name.

:guilabel:`GitLab group name`:
    If you're using a Group repository plan, you'll specify the group name
    here. This is the group name as shown in the URL. For example, if your
    repository was ``https://gitlab.com/mygroup/myrepo``, your group name
    would be ``mygroup``.

:guilabel:`Repository name`:
    The name of the repository. This must be the name found in the clone URL.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate repository on GitLab,
you can leave the checkbox unchecked and choose a bug tracker from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from GitLab's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
