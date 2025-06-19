.. _integrations-travis-ci:

=====================
Travis CI Integration
=====================

`Travis CI`_ is a popular service for :term:`continuous integration`, allowing
you to run test suites, perform builds, and even deploy to servers in an
automated fashion.

Review Board can integrate with Travis CI to do test builds of code changes and
report the results back as a :ref:`status update <status-updates>` on the
review request.


Integration Configuration
=========================

To configure an integration with Travis CI:

1. Click :guilabel:`Add Integration` on the :guilabel:`Integrations` page
   in the :ref:`Administration UI <administration-ui>` and select
   :guilabel:`Travis CI` from the list.

   .. image:: images/add-integration.png

2. Fill out the general fields:

   :guilabel:`Name`:
       A name for this particular configuration.

       Each integration must have its own name. You can provide any name
       you choose. This will be shown whenever a build is in progress.

   :guilabel:`Enable this integration`:
       This will be on by default. You can turn this off to temporarily or
       permanently disable this Travis CI configuration without having to
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

   Because Travis CI only works with GitHub repositories, only changes on
   repositories configured with those hosting services will trigger builds.

4. Fill out the endpoint and authentication credentials for the Travis CI
   server handling your project:

   :guilabel:`Travis CI`:
       The Travis CI endpoint for your project.

   :guilabel:`API Token`:
       The API token used for authentication. To get an API token, follow
       the instructions in their documentation_.

5. Fill out the information for the build processes in Travis CI.

   This configuration will be used instead of anything that is set in the
   repository's :file:`.travis.yml` file.

   :guilabel:`Build Config`:
       The configuration needed to do a test build, without any notification
       or deploy stages.

       The required steps for building the patch and reporting results back
       to Review Board will be automatically included when the build is
       triggered.

   .. warning:: This configuration should not include any secrets, since code
                submitted through Review Board will have access to the
                decrypted data (and these secrets are not needed when there
                is no deployment or notification).

   .. code-block:: yaml

       language: python
       python: 3.12
       install:
           - pip install -e .
           - pip install -r dev-requirements.txt

       script:
           - python -m pytest ./project/

   :guilabel:`Build Branch`:
       An optional branch name to use for review request builds within the
       Travis CI user interface.

       By default, the Travis CI user interface will show all builds as
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
       Enable this if you want Travis CI builds to only run when manually
       started.

       When enabled, this will add a :guilabel:`Run` button to the build
       entry.

   :guilabel:`Build timeout`:
       The amount of time until the build is considered to have timed out.

       If the build takes longer than this, it will be marked as timed out
       and can be re-run.

You can create multiple configurations of the integration to do builds for
each repository which supports Travis CI builds.


.. _Travis CI: https://travis-ci.org/
.. _documentation: https://developer.travis-ci.com/authentication
