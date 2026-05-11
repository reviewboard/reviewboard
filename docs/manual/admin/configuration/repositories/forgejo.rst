.. _repository-hosting-forgejo:

====================
Forgejo Repositories
====================

.. versionadded:: 8.0

Review Board supports posting and reviewing code on :rbintegration:`Forgejo
<forgejo>` repositories.

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

To configure a Forgejo repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`Forgejo` from the
:guilabel:`Hosting type` field.


Step 1: Link Your Forgejo Account
---------------------------------

You will need to link an account on Forgejo to Review Board, so that Review
Board can access content from the repository. If you've already linked an
account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your Forgejo server. This should *not* have a
    trailing ``/``.

    For example: ``https://codeberg.org`` or ``https://forgejo.example.com``.

:guilabel:`Account username`:
    The username used to log into your Forgejo account. This is *not* your
    e-mail address.

:guilabel:`Account password`:
    The password used to log into your Forgejo account.

    Review Board will use this to create an API token. The password itself
    will not be stored.

:guilabel:`Two-factor auth code`:
    If your account has two-factor authentication enabled, you will be
    prompted for the current authentication code after submitting your
    username and password.

When the repository is saved, Review Board will request an API token from
Forgejo on your behalf. Only the resulting token is stored; your password is
not retained. If there are errors authenticating the user or retrieving an
access token, you will be prompted to fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository owner`:
    The username (or organization name) that owns the repository on Forgejo.

    For example, if your repository was
    ``https://codeberg.org/myorg/myrepo``, the repository owner would be
    ``myorg``.

:guilabel:`Repository name`:
    The name of the repository.

    For example, if your repository was
    ``https://codeberg.org/myorg/myrepo``, the repository name would be
    ``myrepo``.


Step 3: Choose a Bug Tracker
----------------------------

If you're using Forgejo's built-in issue tracker for this repository, you can
simply check the :guilabel:`Use hosting service's bug tracker` checkbox. All
bug IDs will link to the appropriate issues for your repository.

If you're using a separate bug tracker, or a separate repository on Forgejo,
you can leave the checkbox unchecked and choose a bug tracker from the list.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from Forgejo's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.


Configuring Webhooks
====================

Review Board can automatically close review requests when matching commits are
pushed to a Forgejo repository. To enable this, you'll need to configure an
outgoing WebHook on the Forgejo repository.


Add the WebHook
---------------

After saving the repository, navigate to the repository's page in the Review
Board administration UI. The :guilabel:`Hooks` section will show the specific
values to enter (the payload URL and the secret will be tailored to your
server and repository).

In Forgejo, navigate to your repository, then go to
:menuselection:`Settings --> Webhooks` and add a new Forgejo webhook. Fill in:

* **Target URL:** The payload URL shown in Review Board.
* **HTTP Method:** ``POST``
* **POST Content Type:** ``application/json``
* **Secret:** The secret shown in Review Board.
* **Trigger On:** Push events.

.. admonition:: Allow outgoing WebHooks to Review Board

   By default, Forgejo restricts outgoing WebHooks to non-private network
   ranges. If your Review Board server is on an internal network, you may
   need to update Forgejo's ``webhook.ALLOWED_HOST_LIST`` setting to allow
   delivery to your Review Board server. See the `Forgejo webhook
   configuration documentation
   <https://forgejo.org/docs/latest/admin/config-cheat-sheet/#webhook-webhook>`_
   for details.


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
