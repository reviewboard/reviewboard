.. _integrations-gitlab-ci:

========================
GitLab CI/CD Integration
========================

`GitLab CI/CD`_ is a popular service for :term:`continuous integration`,
allowing you to run test suites, perform builds, and even deploy to servers in
an automated fashion.

Review Board can integrate with GitLab CI/CD to do test builds of code changes
and report the results back as a :ref:`status update <status-updates>` on the
review request.


.. _GitLab CI/CD: https://docs.gitlab.com/ci/


Integration Configuration
=========================

To configure an integration with GitLab CI:

1. Click :guilabel:`Add Integration` on the :guilabel:`Integrations`
   page in the :ref:`Administration UI <administration-ui>` and select
   :guilabel:`GitLab CI` from the list.

   .. image:: images/add-integration.png

2. Fill out the general fields:

   :guilabel:`Name`:
      A name for this particular configuration. This can be anything you
      choose, and is only important if you plan to have multiple
      configurations.

   :guilabel:`Enable this integration`:
      This will be on by default. You can turn this off to temporarily or
      permanently disable this GitLab CI configuration without having to delete
      it.

   :guilabel:`Local Site`:
      If you're using the advanced :term:`Local Site` (multi-server partition)
      support, you can specify which site contains this configuration.

      Most users can leave this blank.

3. Set the :guilabel:`Conditions` for when Review Board will trigger a build.

   At a minimum, you should set a condition to match a specific repository.
   Even if you only have one repository configured now, you'll want to set
   this up so things don't break if you connect a second one. If needed, you
   can create complex rules for which review requests get matched with this
   config (for example, if you only want to run a test suite for certain
   branches).

   .. image:: images/config-conditions.png

4. Fill out the endpoint and authentication credentials for the GitLab server
   handling your project:

   :guilabel:`Server`:
      The URL of your GitLab server. If your project is hosted on GitLab.com,
      this should be ``https://gitlab.com``.

   :guilabel:`Token type`:
      The type of API token used for authentication.

   :guilabel:`Token`:
      The GitLab API token to use for authentication.

5. Fill out the configuration for the build processes in GitLab CI.

   :guilabel:`Project name or ID`:
      The name of the GitLab project. For example, if your project is located
      at https://gitlab.example.com/org/myproject/, you would put
      ``org/myproject`` in for this field.

      The special variable ``{repository_name}`` will be replaced with the content
      of the repository name as configured in Review Board.

   :guilabel:`Git refname`:
      The branch or reference name which will be checked out by GitLab CI
      before attempting to apply the patch.

      The special variable ``{branch}`` will be replaced with the content of
      the review request's :guilabel:`Branch` field.

   :guilabel:`Pipeline inputs`:
      Additional inputs to send to the GitLab CI pipeline. This should be
      formatted as a JSON_ object. Attribute values in this object can include
      the special variables ``{branch}`` and ``{repository_name}``.

   :guilabel:`Additional variables`:
      Additional CI variables to send to the GitLab CI pipeline. This should be
      formatted as a JSON_ object. Attribute values in this object can include
      the special variables ``{branch}`` and ``{repository_name}``.

6. Set the information for when to run builds.

   :guilabel:`Run builds manually`:
       Enable this if you want GitLab CI builds to only run when manually
       started.

       When enabled, this will add a :guilabel:`Run` button to the build
       entry.

   :guilabel:`Build timeout`:
       The amount of time until the build is considered to have timed out.

       If the build takes longer than this, it will be marked as timed out
       and can be re-run.

7. Decide how to report results back to Review Board.

   :guilabel:`Report job state`:
      If this is checked, results from GitLab will include a summary of all of
      the jobs in the pipeline.

   :guilabel:`GitLab WebHook secret token`:
      When creating a WebHook in GitLab, you can provide a secret token that
      will be included as a header. If you do so, that value should also be
      entered here, and will be used to prevent possibly malicious attempts to
      update the pipeline state.


You can create multiple configurations of the integration to do builds for
each repository which supports GitLab CI builds.


.. _JSON: https://www.json.org/


.gitlab-ci.yml Configuration
============================

GitLab CI has no built-in support for doing test builds of patches, so Review
Board will trigger a build and pass in information in the environment which
will allow you to set up the build using :file:`.gitlab-ci.yml`.

There are several environment variables which will be passed in to your build:

:envvar:`REVIEWBOARD_API_TOKEN`
    An API token to use when communicating with Review Board.

:envvar:`REVIEWBOARD_DIFF_REVISION`
    The revision of the diff to build.

:envvar:`REVIEWBOARD_GITLAB_INTEGRATION_CONFIG_ID`
    An internal identifier used when reporting status back to the Review Board
    server. integration configuration.

:envvar:`REVIEWBOARD_PIPELINE_NAME`
    The name to assign to the pipeline.

:envvar:`REVIEWBOARD_SERVER`
    The Review Board server name.

:envvar:`REVIEWBOARD_REVIEW_REQUEST`
    The ID of the review request.

:envvar:`REVIEWBOARD_STATUS_UPDATE_ID`
    An internal identifier used when reporting status back to the Review Board
    server.

In order for builds with Review Board to work, the :file:`.gitlab-ci.yml` file
must define a job, but with the addition of a step at the beginning to apply
the patch from Review Board.

This is an example :file:`.gitlab-ci.yml` file which sets up an Alpine Linux
environment. The ``before_script`` block will check if the pipeline appears to
be coming from the Review Board integration, and will apply the patch to the
source tree.

.. code-block:: yaml

    image: alpine:latest

    .reviewboard:
      patch:
        - |
        if [ -n "$REVIEWBOARD_REVIEW_REQUEST" ]; then
          apk add rbtools git
          rbt patch --api-token "$REVIEWBOARD_API_TOKEN" --server "$REVIEWBOARD_SERVER" --diff-revision "$REVIEWBOARD_DIFF_REVISION" "$REVIEWBOARD_REVIEW_REQUEST"
        fi

    default:
      before_script:
        - !reference [.reviewboard, patch]

    run-tests:
      script:
        - pip install -e .
        - python ./tests/runtests.py


GitLab WebHook Configuration
============================

In order for Review Board to be updated when the GitLab CI pipeline is done,
you need to create a WebHook.

From your GitLab project, select
:guilabel:`Settings -> Webhooks -> Add New Webhook`. Configure the WebHook with
the following details:

:guilabel:`URL`:
   https://reviewboard.example.com/rbintegrations/gitlab-ci/webhook/

:guilabel:`Secret token`:
   If you want to use a secret token to authenticate WebHook delivery, set this
   to the same value that you set in the
   :guilabel:`GitLab WebHook secret token` field in the integration configuration
   form.

:guilabel:`Trigger`:
   :guilabel:`Pipeline events`

.. important::
   At the moment, pipeline events sent to WebHooks will include *all* of the
   pipeline variables, including the :envvar:`REVIEWBOARD_API_TOKEN`. Ensure
   that all configured WebHooks for your GitLab project are trusted.

For more details, see the `GitLab WebHook documentation`_.


.. _GitLab WebHook documentation: https://docs.gitlab.com/user/project/integrations/webhooks/#create-a-webhook


Customizing Pipeline Names
==========================

GitLab allows customizing the pipeline name, which can make it much easier to
see which pipeline runs correspond to review requests. Review Board will pass
in a ``$REVIEWBOARD_PIPELINE_NAME`` variable, which can be used to override the
name:

.. code-block:: yaml

    variables:
      PIPELINE_NAME: "$CI_COMMIT_TITLE"

    workflow:
      name: "$PIPELINE_NAME"
      rules:
        - if: "$REVIEWBOARD_PIPELINE_NAME != null"
          variables:
            PIPELINE_NAME: "$REVIEWBOARD_PIPELINE_NAME"
        - when: always


Working With Child Pipelines
============================

With complex CI setups, you may have many pipelines which run using triggers.
These can even be dynamic, where a parent pipeline creates the YAML
configuration for a child.

When using parent/child pipelines triggered from Review Board, there are a
couple important considerations.

1. When starting a pipeline, Review Board passes in all of the relevant details
   via pipeline variables. By default, GitLab CI does not forward these
   variables to child pipelines. This could result in child pipelines building
   the wrong commit(s) and being unable to report any job status back to Review
   Board.

   The easiest way to forward pipeline variables is to set the ``forward`` key
   in the trigger. If you have variables that you do not want to forward, you
   could instead set a ``variables`` key that specifically lists out the Review
   Board specific variables.

2. It's also **highly recommended** to set ``strategy: depend`` on the trigger.
   This will make it so the parent pipeline will wait until all child pipelines
   are complete before reporting status. If this is not included, the parent
   pipeline can complete with a success result, even if child pipelines are
   still running or complete with failures.

.. code-block:: yaml

    stages:
      - triggers

    trigger_job:
      stage: triggers
      trigger:
        include:
          - local: child-pipeline.yml
        forward:
          pipeline_variables: true
        strategy: depend
