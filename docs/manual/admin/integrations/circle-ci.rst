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

To configure an integration with CircleCI:

1. Navigate to the :ref:`Administration UI <administration-ui>` ->
   :guilabel:`Integrations`.

2. Click :guilabel:`Add Integration` and select :guilabel:`CircleCI`.

3. Fill out the general fields:

   :guilabel:`Name`:
       A name for this particular configuration.

       Each integration must have its own name. You can provide any name
       you choose. This will be shown whenever a build is in progress.

   :guilabel:`Enable this integration`
       This will be on by default. You can turn this off to temporarily or
       permanently disable this CircleCI configuration without having to
       delete it.

   :guilabel:`Local Site`
       If you're using the advanced :term:`Local Site` (multi-server
       partition) support, you can specify which site contains this
       configuration.

       Most users can leave this blank.

4. Set the :guilabel:`Conditions` for when Review Board will trigger a build.

   At a minimum, you should set a condition to match a specific repository.
   Even if you only have one repository configured now, you'll want to set
   this up so things don't break if you connect a second one. If needed, you
   can create complex rules for which review requests get matched with this
   config (for example, if you only want to run a test suite for certain
   branches).

   .. image:: images/ci-conditions.png

   Because CircleCI only works with GitHub and Bitbucket repositories, only
   changes on repositories configured with those hosting services will
   trigger builds.

5. Fill out the information for the build processes in CircleCI.

   :guilabel:`API Token`:
       The API token used for authentication. You can use a personal or
       project API token. To create an API token, follow the instructions
       in their documentation_.

   :guilabel:`Build Branch`:
       An optional branch name to use for review request builds within the
       CircleCI user interface.

       By default, the CircleCI user interface will show all builds as
       occurring on ``master``. This field allows you to override the
       branch name to be something else, as to separate review request builds
       from regular builds.

   .. note:: We recommend creating and pushing a dummy branch named
             "review-requests" to your repository, and then filling in that
             name here. The actual contents of that branch are unimportant,
             and it never needs to be updated, since the source will be
             completely replaced during the build process.

6. Set the information for when to run builds.

   :guilabel:`Run builds manually`:
       Enable this if you want CircleCI builds to only run when manually
       started.

       When enabled, this will add a :guilabel:`Run` button to the build
       entry.

   :guilabel:`Build timeout`
       The amount of time until the build is considered to have timed out.

       If the build takes longer than this, it will be marked as timed out
       and can be re-run.

You can create multiple configurations of the integration to do builds for
each repository which supports CircleCI builds.


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
            command: sudo pip install -e .
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
            command: sudo pip install -e .
          - run:
            name: Run tests
            command: python ./tests/runtests.py
    notify:
      webhooks:
        - url: https://reviewboard.example.com/rbintegrations/circle-ci/webhook/


.. _CircleCI: https://circleci.com/
.. _documentation: https://circleci.com/docs/managing-api-tokens/
