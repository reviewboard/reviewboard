.. _integrations-jenkins-ci:

======================
Jenkins CI Integration
======================

`Jenkins CI`_ is a popular service for :term:`continuous integration`, allowing
you to run test suites, perform builds, and even deploy to servers in an
automated fashion.

Review Board can integrate with Jenkins CI to do test builds of code changes
and report the results back as a :ref:`status update <status-updates>` on the
review request.


Integration Configuration
=========================

To configure an integration with Jenkins CI:

1. Click :guilabel:`Add Integration` on the :guilabel:`Integrations` page
   in the :ref:`Administration UI <administration-ui>` and select
   :guilabel:`Jenkins CI` from the list.

   .. image:: images/add-integration.png

2. Fill out the general fields:

   :guilabel:`Name`:
       A name for this particular configuration.

       Each integration must have its own name. You can provide any name
       you choose. This will be shown whenever a build is in progress.

   :guilabel:`Enable this integration`:
       This will be on by default. You can turn this off to temporarily or
       permanently disable this Jenkins configuration without having to
       delete it.

   :guilabel:`Local Site`:
       If you're using the advanced :term:`Local Site` (multi-server
       partition) support, you can specify which site contains this
       configuration.

       Most users can leave this blank.

3. Set the :guilabel:`Conditions` for when Review Board will trigger a build.

   At a minimum, you should set a condition to match a specific repository.
   Even if you only have one repository configured now, you'll want to set
   this up so things don't break if you connect a second one. If needed, you
   can create complex rules for which review requests get matched with this
   config (for example, if you only want to run a test suite for certain
   branches).

   .. image:: images/config-conditions.png

4. Fill out the address and authentication credentials for the Jenkins server
   handling your builds:

   :guilabel:`Server`:
       The base URL of your Jenkins server.

   :guilabel:`Username`:
       The username for a Jenkins user who has the appropriate permissions
       for starting the above :guilabel:`Job name`.

   :guilabel:`API Token / Password`:
       The API token used for authentication. Older versions may require
       the user's password instead.

5. Fill out the information for the build processes in Jenkins.

   :guilabel:`Job Name`:
       This allows you to specify which job to run on your Jenkins server.

       This field allows for the following variables, which will be
       auto-populated with the appropriate fields from a review request:

       ``{branch_name}``:
           The branch name.

       ``{repository_name}``:
           The repository name.

       ``{noslash_branch_name}``:
           The branch name with slashes converted to underscores.

       ``{noslash_repository_name}``:
           The repository name with slashes converted to underscores.

       Older versions of Jenkins disallowed using slashes in job names, and
       required normalizing them to underscores. In newer versions, slashes
       are required. Use the appropriate variables for your version of
       Jenkins.

   :guilabel:`Review Board API Token`:
       This specifies the API token to use when configuring your Jenkins CI
       server.

       If you switch the local site, this will be regenerated upon saving.

6. Set the information for when to run builds.

   :guilabel:`Run builds manually`:
       Enable this if you want Jenkins builds to only run when manually
       started.

       When enabled, this will add a :guilabel:`Run` button to the build
       entry.

   :guilabel:`Build timeout`:
       The amount of time until the build is considered to have timed out.

       If the build takes longer than this, it will be marked as timed out
       and can be re-run.

You can create multiple configurations of the integration to do builds for
each repository which supports Jenkins builds.


Jenkins Plugin Installation
===========================

1. On your Jenkins server, navigate to :guilabel:`Manage Jenkins`, then select
   :guilabel:`Manage Plugins`.

2. On the plugins page, select the :guilabel:`Available` tab, then type "Review
   Board" into the :guilabel:`Filter` box. You should see one result (but you
   can click the link and verify that the ID listed is ``rb`` if multiple
   results appear).

3. Select the checkbox and click :guilabel:`Install without restart`.

4. Restart your Jenkins server.


Jenkins Configuration
=====================

To create a Review Board server configuration for your Jenkins server, perform
the following steps:

1. On your Jenkins server, navigate to :guilabel:`Manage Jenkins`, then select
   :guilabel:`Configure System`.

2. Scroll down until you reach the :guilabel:`Review Board` configuration
   section.

3. Click :guilabel:`Add Review Board Server` to create a new Review Board
   server configuration.

4. Enter your Review Board server URL into the :guilabel:`Review Board URL`
   field. This must match *exactly* the server URL set in the Review Board
   :guilabel:`General Settings` page.

5. If you have previously created a credential for your Review Board API token,
   select it here and skip to the job configuration.

6. If you have not yet created a credential for the Review Board API token,
   click :guilabel:`Add` and select :guilabel:`Jenkins`.

7. In the prompt, set :guilabel:`Kind` to :guilabel:`Secret text`.

8. Set :guilabel:`Scope` to :guilabel:`Global`.

9. Fill in :guilabel:`Secret` with the :guilabel:`Review Board API Token`
   found in the Jenkins CI integration configuration page in the Review Board
   administration UI.

10. Give your secret a unique identifier in the :guilabel:`ID` field and click
    :guilabel:`Add`.

11. Click :guilabel:`Save` to save your server configuration.

For each job you wish to use on Jenkins, you must add four new build parameters
that will be used to give Jenkins information on the incoming review request.
To add these, perform the following steps:

1. Navigate to your job's page and click :guilabel:`Configure`.

2. Ensure the :guilabel:`This project is parameterized` checkbox is checked.

3. For each of the following parameter names, repeat these two steps:

   * ``REVIEWBOARD_REVIEW_ID``
   * ``REVIEWBOARD_REVIEW_BRANCH``
   * ``REVIEWBOARD_DIFF_REVISION``
   * ``REVIEWBOARD_STATUS_UPDATE_ID``
   * ``REVIEWBOARD_SERVER``

   1. Click :guilabel:`Add parameter` and select :guilabel:`String parameter`.
   2. Input the parameter name into :guilabel:`Name` and leave all other fields
      blank.

4. Scroll down to the :guilabel:`Build` section. Here we can add the
   :guilabel:`Apply patch from Review Board` step by clicking
   :guilabel:`Add build step` and choosing it from the dropdown menu.

   .. note::

       This step uses RBTools to apply the patch from Review Board. It will
       attempt to install the package using pip, but if it lacks permission you
       will need to manually install it. Additionally, the order of your build
       steps matter, so this step should likely be the first build step so all
       later build steps see the correct source code.

5. Scroll down to the :guilabel:`Post-build actions` section. Here we can add
   the :guilabel:`Publish build status to Review Board` step by clicking
   :guilabel:`Add post-build action` and choosing it from the dropdown menu.

6. Click :guilabel:`Save` to save these changes.

.. _Jenkins CI: https://jenkins.io/
