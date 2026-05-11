.. _repository-hosting-rb-gateway:

=================================
Review Board Gateway Repositories
=================================

`Review Board Gateway`_ (RB Gateway) is a lightweight, self-installed source
hosting service from Beanbag, Inc. It wraps a set of locally-hosted Git or
Mercurial repositories with an HTTP API that Review Board can talk to. This
is the recommended way to use Review Board with self-hosted Git or Mercurial
repositories that aren't already exposed through a hosting service such as
GitHub, GitLab, Bitbucket, or Forgejo.

Existing commits in a repository can be browsed and put up for review.

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. See :ref:`Using RBTools with Git <rbt-post-git>` or
:ref:`Using RBTools with Mercurial <rbt-post-mercurial>` for more information.

.. _Review Board Gateway: https://www.reviewboard.org/downloads/rbgateway/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing RB Gateway
=====================

Before configuring a repository in Review Board, you'll need a running RB
Gateway server. See the `RB Gateway downloads page`_ for installation
instructions and binaries.

You will need to :ref:`configure RB Gateway <rb-gateway-configuration>` for
each repository you want to expose. The name you put into the
:file:`config.json` for each repository will be the name you use in the
repository configuration in Review Board.

.. _RB Gateway downloads page:
   https://www.reviewboard.org/downloads/rbgateway/


Adding the Repository
=====================

To configure an RB Gateway repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`Review Board Gateway`
from the :guilabel:`Hosting type` field.


Step 1: Link Your RB Gateway Account
------------------------------------

You will need to link an account on RB Gateway to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access, you can use that instead.

Fill out the following fields:

:guilabel:`Service URL`:
    The URL to the root of your RB Gateway server.

    For example: ``https://rbgateway.example.com``.

:guilabel:`Account username`:
    The username used to log into your RB Gateway server.

:guilabel:`Account password`:
    The password used to log into your RB Gateway server.

If there are errors authenticating the user, you will be prompted to fix
them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`Repository type`:
    Select either :guilabel:`Git` or :guilabel:`Mercurial`, depending on the
    repository configured in RB Gateway.

:guilabel:`Repository name`:
    The name of the repository. This must match the name specified for the
    repository in the RB Gateway configuration file.


Step 3: Choose a Bug Tracker
----------------------------

RB Gateway does not provide a bug tracker, but you can choose a bug tracker
on another service or provide a custom URL to your own bug tracker.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it).

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.


Configuring Webhooks
====================

Review Board can automatically close review requests when matching commits
are pushed to a repository served by RB Gateway. To enable this, configure an
outgoing webhook on the RB Gateway server.


Add the WebHook
---------------

After saving the repository, navigate to the repository's page in the Review
Board administration UI. The :guilabel:`Hooks` section will show the specific
``close_url`` and secret to use for your repository.

Webhooks are configured in the :ref:`webhooks.json
<rb-gateway-webhooks-configuration>` file on the RB Gateway server. Add an
entry to that, substituting the ``url`` and ``secret`` values with those shown
in the Review Board administration UI, and list the RB Gateway repository name
in ``repos``.

After updating the file, reload the ``rb-gateway`` service so the new webhook
configuration takes effect. For example::

    $ kill -HUP $(pgrep rb-gateway)

Or, if you're running RB Gateway under ``systemd``::

    $ systemctl reload rb-gateway.service


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
