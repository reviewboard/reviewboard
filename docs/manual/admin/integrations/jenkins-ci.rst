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

To configure integration with Jenkins CI, click :guilabel:`Add a new
configuration` on the :guilabel:`Integrations` page in the :ref:`Administration
UI <administration-ui>`. You can create multiple configurations of the
integration to do builds for each repository which supports Jenkins CI builds.

The :guilabel:`Name` field can be used to set a name for this particular
configuration. This allows you to keep track of which is which in the case
where you have multiple Jenkins CI configurations.

If at any point you want to stop triggering builds but do not want to delete
the configuration, you can uncheck :guilabel:`Enable this integration`.

:guilabel:`Conditions` allows you to set conditions for when Review Board will
trigger a build. At a minimum, you should set a condition to match a specific
repository. Even if you only have one repository configured now, you'll want to
set this up so things don't break if you connect a second one. If needed, you
can create complex rules for which review requests get matched with this config
(for example, if you only want to run a test suite for certain branches).

.. image:: images/ci-conditions.png

The :guilabel:`Server` field should be set to the base URL of your Jenkins CI
server.

The :guilabel:`Job Name` field allows you to specify which job to run on your
Jenkins CI server. This field also allows for variables like `{repository}`
and `{branch}`, which will be auto-populated with the appropriate fields from
a review request.

The :guilabel:`User` field specifies the username for a Jenkins CI user who has
the appropriate permissions for starting the above :guilabel:`Job name`.

:guilabel:`Password` should be set to the above :guilabel:`User`'s password.

:guilabel:`ReviewBoard API Token` specifies the API token to use when
configuring your Jenkins CI server.


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
