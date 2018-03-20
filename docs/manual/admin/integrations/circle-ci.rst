.. _integrations-circle-ci:

====================
CircleCI Integration
====================

CircleCI_ is a popular service for :term:`continuous integration`, allowing you
to run test suites, perform builds, and even deploy to servers in an automated
fashion.

Review Board can integrate with CircleCI to do test builds of code changes and
report the results back as a :ref:`status update <status-updates>` on the review
request.

Review Board requires the use of CircleCI 2.0. If you're still using CircleCI
1.0, you'll need to update first.


Integration Configuration
=========================

To configure integration with CircleCI, click :guilabel:`Add a new
configuration` on the :guilabel:`Integrations` page in the :ref:`Administration
UI <administration-ui>`. You can have multiple different CircleCI
configurations, in the case where you may need to have review requests on
different repositories use different CircleCI API keys.

In the configuration, there are several required fields.

The :guilabel:`Name` field can be used to set a name for this particular
configuration. This allows you to keep track of which is which in the case
where you have multiple CircleCI configurations.

:guilabel:`Conditions` allows you to set conditions for when Review Board will
trigger a build. If you want to trigger builds for all code changes, this can
be set to :guilabel:`Always match`. However, you can also create complex rules
for which review requests will match. Because CircleCI only works with GitHub
and Bitbucket repositories, only changes on repositories configured with those
hosting services will trigger builds.

.. image:: images/ci-conditions.png

:guilabel:`API Token` should be set to a valid CircleCI API Token. These can be
created by going to CircleCI and selecting :guilabel:`User Settings` from the
menu at the top right. From there, select :guilabel:`Personal API Tokens`.

There's one additional optional field, :guilabel:`Build Branch`. By default,
the CircleCI user interface will show all builds as occurring on ``master``.
This field allows you to override the branch name to be something else, as to
separate review request builds from regular builds.

.. note:: We recommend creating and pushing a dummy branch named
          "review-requests" to your repository, and then filling in that name
          here. The actual contents of that branch are unimportant, and it
          never needs to be updated, since the source will be completely
          replaced during the build process.

If at any point you want to stop triggering builds but do not want to delete
the configuration, you can uncheck :guilabel:`Enable this integration`.


CircleCI config.yml Configuration
=================================

CircleCI has no built-in support for doing test builds of patches, so Review
Board will trigger a build using a special job name and pass in information in
the environment which will allow you to set up the build using
:file:`.circleci/config.yml`.

There are several environment variables which will be passed in to your build:

* :envvar:`REVIEWBOARD_SERVER` - The Review Board server name.
* :envvar:`REVIEWBOARD_REVIEW_REQUEST` - The ID of the review request.
* :envvar:`REVIEWBOARD_DIFF_REVISION` - The revision of the diff to build.
* :envvar:`REVIEWBOARD_API_TOKEN` - An API token to use when communicating with
  Review Board.
* :envvar:`REVIEWBOARD_STATUS_UPDATE_ID` - An internal identifier used when
  reporting status back to the Review Board server.

In order for builds with Review Board to work, the :file:`.circleci/config.yml`
file must define a job named ``reviewboard``, and a webhook notification. The
job should look substantially similar to your normal ``build`` job, but with
the addition of a step at the beginning to apply the patch from Review Board.
This should also not include anything that you don't want to run on uncommitted
changes, such as deployments.

This is an example :file:`.circleci/config.yml` file which sets up a Python 2.7
environment, installs dependencies, and runs a unit test script. As you can
see, the steps for the ``reviewboard`` job are virtually identical to the
``build`` job, except there's an extra one at the start which applies the patch
using :ref:`rbt patch <rbtools:rbt-patch>`.

.. code-block:: yaml

    jobs:
      build:
        docker:
          - image: circleci/python:2.7
        steps:
          - checkout
          - run:
            name: Install dependencies
            command: sudo python setup.py develop
          - run:
            name: Run tests
            command: python ./tests/runtests.py
      reviewboard:
        docker:
          - image: circleci/python:2.7
        steps:
          - checkout
          - run:
            name: Apply patch
            command: |
              sudo pip install rbtools
              rbt patch --api-token "$REVIEWBOARD_API_TOKEN" --server "$REVIEWBOARD_SERVER" --diff-revision "$REVIEWBOARD_DIFF_REVISION" "$REVIEWBOARD_REVIEW_REQUEST"
          - run:
            name: Install dependencies
            command: sudo python setup.py develop
          - run:
            name: Run tests
            command: python ./tests/runtests.py
    notify:
      webhooks:
        - url: https://reviewboard.example.com/rbintegrations/circle-ci/webhook/


.. _CircleCI: https://circleci.com/
