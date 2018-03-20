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

To configure integration with Travis CI, click :guilabel:`Add a new
configuration` on the :guilabel:`Integrations` page in the :ref:`Administration
UI <administration-ui>`. You can create multiple configurations of the
integration to do builds for each repository which supports Travis CI builds.

The :guilabel:`Name` field can be used to set a name for this particular
configuration. This allows you to keep track of which is which in the case
where you have multiple Travis CI configurations.

If at any point you want to stop triggering builds but do not want to delete
the configuration, you can uncheck :guilabel:`Enable this integration`.

:guilabel:`Conditions` allows you to set conditions for when Review Board will
trigger a build. At a minimum, you should set a condition to match a specific
repository. Even if you only have one repository configured now, you'll want to
set this up so things don't break if you connect a second one. If needed, you
can create complex rules for which review requests get matched with this config
(for example, if you only want to run a test suite for certain branches).

.. image:: images/ci-conditions.png

The :guilabel:`Build Config` allows you to specify a replacement for the
repository's :file:`.travis.yml` file. This should define the build for your
project in isolation, removing any deployment or notification steps. The
required steps for building the patch and reporting results back to Review
Board will be automatically included when the build is triggered.

.. warning:: This configuration should not include any secrets, since code
             submitted through Review Board will have access to the decrypted
             data (and these secrets are not needed when there is no deployment
             or notification).

.. code-block:: yaml

    language: python
    python: 2.7
    install:
        - python setup.py develop
        - pip install -r dev-requirements.txt

    script:
        - python ./tests/runtests.py

There's one additional optional field, :guilabel:`Build Branch`. By default,
the Travis CI user interface will show all builds as occurring on ``master``.
This field allows you to override the branch name to be something else, as to
separate review request builds from regular builds.

.. note:: We recommend creating and pushing a dummy branch named
          "review-requests" to your repository, and then filling in that name
          here. The actual contents of that branch are unimportant, and it
          never needs to be updated, since the source will be completely
          replaced during the build process.


.. _Travis CI: https://travis-ci.org/
