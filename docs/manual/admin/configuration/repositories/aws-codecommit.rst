.. _repository-hosting-aws-codecommit:

===========================
AWS CodeCommit Repositories
===========================

.. note::

   AWS CodeCommit support requires a license of `Power Pack`_. You can
   `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on Git repositories hosted on
:rbintegration:`AWS CodeCommit <aws-codecommit>`.

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

To configure a CodeCommit repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`AWS CodeCommit`
from the :guilabel:`Hosting type` field.


Step 1: Link Your CodeCommit Account
------------------------------------

You will need to link an account on CodeCommit to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to `create an IAM user`_
that can access CodeCommit on your AWS organization. This user only needs to
read from CodeCommit repositories and does not need any write access, or
access to other services. You'll need to make sure you have your Access Key ID
and Secret Access Key to continue.

Fill out the following fields:

:guilabel:`AWS access key ID`:
    The access key ID for your IAM user.

:guilabel:`AWS secret access key`:
    Your secret access key for your IAM user.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


.. _create an IAM user:
   https://docs.aws.amazon.com/codecommit/latest/userguide/auth-and-access-control.html


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`AWS region`:
    The region where your CodeCommit repository is hosted. For example,
    ``us-east-1``.

:guilabel:`Repository name`:
    The name of the repository as configured on CodeCommit. This is the same
    name you would find in your clone URL.


Step 3: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. CodeCommit, at the time of
this writing, does not provide one, but you can choose one on another service
or provide a custom URL to your own bug tracker.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


.. _repository-hosting-aws-codecommit-access-control:

Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from CodeCommit's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
