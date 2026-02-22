.. _repository-hosting-bitbucket-server:

=============================
Bitbucket Server Repositories
=============================

.. note::

   Bitbucket Server support requires a license of `Power Pack`_. You can
   `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on Git repositories hosted on
:rbintegration:`Bitbucket Server <bitbucket-server>`.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` for
more information.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _download a trial license: https://www.reviewboard.org/powerpack/trial/
.. _purchase a license: https://www.reviewboard.org/powerpack/purchase/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a Bitbucket Server repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Bitbucket Server`
from the :guilabel:`Hosting type` field.


Step 1: Link Your Bitbucket Server Account
------------------------------------------

You will need to link an account on Bitbucket Server to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your Bitbucket Server. For example,
    ``https://bitbucket.example.com/``.

:guilabel:`Account username`:
    The username used to log into your Bitbucket Server account.

:guilabel:`Account password`:
    The password used to log into your Bitbucket Server account.

    Due to some requirements when accessing your repositories, your password
    will be stored in encrypted form in the database.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository plan`:
    This specifies whether you're linking a user-owned (personal) repository
    or a group (project) repository. Depending on your choice, you'll see
    different options.

:guilabel:`Project key`:
    If you selected a Project Repository above, you'll need to provide your
    project key here. This can be found in your project settings on Bitbucket
    Server.

:guilabel:`Repository owner username`:
    If you selected a Personal Repository above, you'll need to specify the
    username of the user who owns the repository.

:guilabel:`Repository name`:
    You'll then need to specify the name of your repository in the
    :guilabel:`Repository name` field. This is the same value you would find
    in the URL.


Step 3: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. For example, if you're using
JIRA as your bug tracker, you can configure it so that any references to bug
numbers will link to the appropriate ticket.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


.. _repository-hosting-bitbucket-server-access-control:

Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Bitbucket Server's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
