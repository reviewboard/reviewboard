.. _repository-hosting-visualstudio:

=============================
VisualStudio.com Repositories
=============================

.. note::

   VisualStudio.com support requires a license of `Power Pack`_. You can
   `download a trial license`_ or `purchase a license`_ for your team.

Review Board supports posting and reviewing code on
:rbintegration:`VisualStudio.com <visual-studio-team-services>` repositories.
Existing commits in a repository can be browsed and put up for review.

The following types of Assembla repositories are supported:

* Git
* TFS

To simplify posting changes to Review Board, we recommend using RBTools_. This
ensures that the diffs are in the correct format, and makes managing review
requests much easier. If you're using TFS, this is a requirement.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _download a trial license: https://www.reviewboard.org/powerpack/trial/
.. _purchase a license: https://www.reviewboard.org/powerpack/purchase/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Adding the Repository
=====================

To configure a VisualStudio.com repository, first proceed to :ref:`add the
repository <adding-repositories>` and select :guilabel:`VisualStudio.com` from
the :guilabel:`Hosting type` field.


Step 1: Link Your VisualStudio.com Account
------------------------------------------

You will need to link an account on VisualStudio.com to Review Board, so that
Review Board can access content from the repository. If you've already linked
an account with sufficient access to the repository, you can use that instead.

If you're linking for the first time, you'll need to make sure you have your
username and password handy.

Fill out the following fields:

:guilabel:`Account username`:
    The username used to log into your VisualStudio.com account. This is *not*
    your e-mail address.

:guilabel:`Account password`:
    The password used to log into your VisualStudio.com account.

    Due to the way the VisualStudio.com API and repositories must be accessed,
    your password will be stored in encrypted form in the database.

The account will be linked when the repository is saved. If there are errors
authenticating the user or retrieving an access token, you will be prompted to
fix them.


Step 2: Provide Repository Information
--------------------------------------

Next, you'll need to fill out the following fields:

:guilabel:`VisualStudio.com account name`:
    The account name for your team. This is the ``my_account`` in
    :samp:`https://{my_account}.visualstudio.com/`.

:guilabel:`VisualStudio.com project name`:
    The name of your project on VisualStudio.com.

    This is only required for Git repositories, and is not used for TFS.

:guilabel:`VisualStudio.com repository name`:
    The name of your Git repository on VisualStudio.com.

    This is only required for Git repositories, and is not used for TFS.


Step 3: Choose a Bug Tracker
----------------------------

You can specify a bug tracker on another service. At the time of this writing,
support for bug trackers on VisualStudio.com is not supported.

:ref:`Learn more about bug tracker configuration <repository-bug-tracker>`.


Step 4: Manage Access Control
-----------------------------

You can now choose who should have access to this repository (both posting
against it and viewing review requests posted against it). This is separate
from VisualStudio.com's own access controls.

:ref:`Learn more about access control <repository-access-control>`.


Step 5: Save the Repository
---------------------------

At this point, you should be able to save the repository. If saving succeeds,
you're done! You can start posting changes for review.
