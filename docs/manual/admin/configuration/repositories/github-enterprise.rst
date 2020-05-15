.. _repository-hosting-github-enterprise:

==============================
GitHub Enterprise Repositories
==============================

.. note::

   GitHub Enterprise support requires a license of `Power Pack`_. You can
   `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on :rbintegration:`GitHub
Enterprise <github-enterprise>` repositories, using public or private personal
repositories or organization-owned repositories.

Existing commits in a repository can be browsed and put up for review. Pull
requests, however, are not currently supported (though planned for a future
release).

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

To configure a GitHub Enterprise repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`GitHub Enterprise`
from the :guilabel:`Hosting type` field.


Step 1: Link Your GitHub Enterprise Account
-------------------------------------------

You will need to link an account on GitHub Enterprise to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and Personal Access Token handy.


.. admonition:: Linking requirements changed in Review Board 3.0.18

   Older versions of Review Board and Power Pack accepted a standard GitHub
   account password, which would be used to automatically create an access
   token on your behalf. Since this capability is `deprecated in GitHub
   <https://developer.github.com/changes/2020-02-14-deprecating-oauth-auth-endpoint/>`_,
   Review Board 3.0.18/Power Pack 3.0.3 and higher require that you create
   this token yourself.

   If you are running an older version and cannot link an account, you will
   need to upgrade Review Board and Power Pack.


Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your GitHub Enterprise server. For example,
    ``https://github.example.com/``.

:guilabel:`GitHub Username`:
    The username used to log into your GitHub account. This is *not* your
    e-mail address.

:guilabel:`Personal Access Token`:
    A GitHub Personal Access Token, created in your GitHub account under
    :guilabel:`Settings -> Developer Settings -> Personal Access Tokens`.

    When creating a new token, give it a descriptive name and enable the
    following scopes:

    * ``admin:repo_hook``
    * ``repo``
    * ``user``

    See `GitHub's guide on Personal Access Tokens
    <https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line>`_.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository plan`:
    This specifies the type of the repository, whether it's public/private or
    personal/team. You'll have one of the following choices:

    * **Public:** The repository is owned by the linked user account, and is
      publicly-accessible to any user.

    * **Public Organization:** The repository is owned by an organization, and
      is publicly accessible to any user.

    * **Private:** The repository is owned by the linked user account, and is
      accessible only to the linked user and other GitHub Enterprise users who
      were granted permission.

    * **Private Organization:** The repository is owned by an organization,
      and is accessible only to the linked user and other GitHub Enterprise
      users who were granted permission.

    .. note::

       The public/private options have no bearing on who can access review
       requests on this repository in Review Board. See
       :ref:`repository-hosting-github-enterprise-access-control`.

:guilabel:`Organization name`:
    If you're using an organization-based plan, you will need to specify the
    organization name in the :guilabel:`Organization name` field. This is the
    same value you would find in the URL. For example, if your repository was
    ``https://github.example.com/myorg/myrepo/``, your organization name
    would be ``myorg``.

:guilabel:`Repository name`:
    You'll then need to specify the name of your repository in the
    :guilabel:`Repository name` field. This is the same value you would find
    in the URL. In the above example, your repository name would be
    ``myrepo``.


Step 3: Choose a Bug Tracker
----------------------------

If you're using the issue tracking feature on this repository, you can simply
check the :guilabel:`Use hosting service's bug tracker` checkbox. All bug IDs
will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate repository on GitHub
Enterprise, you can leave the checkbox unchecked and choose a bug tracker from
the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


.. _repository-hosting-github-enterprise-access-control:

Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from GitHub Enterprise's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.


Configuring Repository Hooks
============================

Review Board can close review requests automatically when pushing commits to
GitHub Enterprise. This is done by configuring a WebHook and pointing it to
your Review Board server, and then referencing the review request in your
commit message (which is done for you when using :ref:`rbt land <rbt-land>`).

Let's go over how to set this up.


Add the WebHook
---------------

On Review Board, view the list of repositories and locate the repository you
want to configure hooks for. Beside the repository name, you'll see a
:guilabel:`Hooks` link. Click that and you'll see instructions for configuring
the hook.

.. image:: images/github-enterprise/hooks.png

The instructions will contain a link taking you to the page on GitHub
Enterprise for adding a new WebHook, along with all the information you need
in order to add the hook. Simply follow the instructions and you'll be ready
to go.


Tag Your Commit Messages
------------------------

To close a review request for a given commit, you'll need to add some special
text to your commit message that references the review request. This can be in
the form of :samp:`Reviewed at {review_request_url}` or :samp:`Review request
#{id}`. This must be on its own line, but can appear anywhere in the commit
message.

For example:

.. code-block:: text

    Reviewed at https://reviewboard.example.com/r/123/

Or:

.. code-block:: text

    Review request #123

If you use :ref:`rbt land <rbt-land>`, this will be automatically added for
you when landing your changes.
