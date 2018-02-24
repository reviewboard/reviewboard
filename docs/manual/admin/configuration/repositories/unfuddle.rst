.. _repository-hosting-unfuddle:

===========================
Unfuddle STACK Repositories
===========================

Review Board supports posting and reviewing code on :rbintegration:`Unfuddle
STACK <unfuddle-stack>` repositories.

The following types of Unfuddle STACK repositories are supported:

* Git
* Subversion

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier.

.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure an Unfuddle STACK repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Unfuddle` from the
:guilabel:`Hosting type` field.


Step 1: Link Your Unfuddle STACK Account
----------------------------------------

You will need to link an account on Unfuddle STACK to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Account username`:
    The username used to log into your Unfuddle STACK account. This is *not*
    your e-mail address.

:guilabel:`Account password`:
    The password used to log into your Unfuddle STACK account.

    Due to the way the Unfuddle STACK API must be accessed, your password will
    be stored in encrypted form in the database.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    The type of repository you're adding. This can be either "Git" or
    "Subversion".

:guilabel:`Unfuddle account domain`:
    Your Unfuddle STACK domain. This would be the ``domain_name`` in
    :samp:`https://{domain_name}.unfuddle.com/`.

:guilabel:`Unfuddle project ID`:
    The numeric ID for your project, found in the URL on your Project page.

    This would be ``project_id`` in
    :samp:`https://{domain_name}.unfuddle.com/a#/projects/{project_id}`.

:guilabel:`Repository name`:
    The name of your repository, as you'd see it in the checkout/clone URL.
    This is not the customizable display name.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate domain or project ID
Unfuddle STACK, you can leave the checkbox unchecked and choose a bug tracker
from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Unfuddle STACK's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
