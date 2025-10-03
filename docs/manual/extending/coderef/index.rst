.. _reviewboard-coderef:

===========================
Module and Class References
===========================


.. seealso::

   :ref:`Djblets Code Reference <djblets-coderef>`


Top-Level Modules
=================

.. autosummary::
   :toctree: python

   reviewboard
   reviewboard.deprecation
   reviewboard.rb_platform
   reviewboard.signals


User Accounts
=============

.. autosummary::
   :toctree: python

   reviewboard.accounts.backends
   reviewboard.accounts.backends.ad
   reviewboard.accounts.backends.base
   reviewboard.accounts.backends.http_digest
   reviewboard.accounts.backends.ldap
   reviewboard.accounts.backends.nis
   reviewboard.accounts.backends.registry
   reviewboard.accounts.backends.standard
   reviewboard.accounts.backends.x509
   reviewboard.accounts.decorators
   reviewboard.accounts.errors
   reviewboard.accounts.forms.auth
   reviewboard.accounts.forms.pages
   reviewboard.accounts.forms.registration
   reviewboard.accounts.managers
   reviewboard.accounts.middleware
   reviewboard.accounts.mixins
   reviewboard.accounts.models
   reviewboard.accounts.pages
   reviewboard.accounts.privacy
   reviewboard.accounts.templatetags.accounts
   reviewboard.accounts.testing
   reviewboard.accounts.testing.queries
   reviewboard.accounts.trophies
   reviewboard.accounts.user_details


Actions
=======

.. autosummary::
   :toctree: python

   reviewboard.actions
   reviewboard.actions.base
   reviewboard.actions.errors
   reviewboard.actions.registry


Administration and Server
=========================

.. autosummary::
   :toctree: python

   reviewboard.admin
   reviewboard.admin.admin_sites
   reviewboard.admin.cache_stats
   reviewboard.admin.checks
   reviewboard.admin.decorators
   reviewboard.admin.form_widgets
   reviewboard.admin.middleware
   reviewboard.admin.model_admin
   reviewboard.admin.security_checks
   reviewboard.admin.server
   reviewboard.admin.siteconfig
   reviewboard.admin.support
   reviewboard.admin.validation
   reviewboard.admin.widgets


File Attachments
================

.. autosummary::
   :toctree: python

   reviewboard.attachments.errors
   reviewboard.attachments.forms
   reviewboard.attachments.managers
   reviewboard.attachments.mimetypes
   reviewboard.attachments.models


Avatars
=======

.. autosummary::
   :toctree: python

   reviewboard.avatars.registry
   reviewboard.avatars.services
   reviewboard.avatars.settings
   reviewboard.avatars.templatetags.avatars
   reviewboard.avatars.testcase


.. seealso::

   :ref:`djblets.avatars <coderef-djblets-avatars>`


Review Request Change Descriptions
==================================

.. autosummary::
   :toctree: python

   reviewboard.changedescs.models


Datagrids
=========

.. autosummary::
   :toctree: python

   reviewboard.datagrids.columns
   reviewboard.datagrids.grids
   reviewboard.datagrids.sidebar


.. seealso::

   :ref:`djblets.datagrids <coderef-djblets-datagrids>`


Diff Viewer
===========

.. autosummary::
   :toctree: python

   reviewboard.diffviewer.chunk_generator
   reviewboard.diffviewer.differ
   reviewboard.diffviewer.diffutils
   reviewboard.diffviewer.errors
   reviewboard.diffviewer.forms
   reviewboard.diffviewer.managers
   reviewboard.diffviewer.models
   reviewboard.diffviewer.models.diffcommit
   reviewboard.diffviewer.models.diffset
   reviewboard.diffviewer.models.diffset_history
   reviewboard.diffviewer.models.filediff
   reviewboard.diffviewer.models.legacy_file_diff_data
   reviewboard.diffviewer.models.raw_file_diff_data
   reviewboard.diffviewer.myersdiff
   reviewboard.diffviewer.opcode_generator
   reviewboard.diffviewer.parser
   reviewboard.diffviewer.processors
   reviewboard.diffviewer.renderers
   reviewboard.diffviewer.smdiff


SSL/TLS Certificates
====================

.. autosummary::
   :toctree: python

   reviewboard.certs
   reviewboard.certs.cert
   reviewboard.certs.errors


Extensions
==========

.. autosummary::
   :toctree: python

   reviewboard.extensions.base
   reviewboard.extensions.hooks
   reviewboard.extensions.packaging
   reviewboard.extensions.packaging.backend
   reviewboard.extensions.packaging.setuptools_backend
   reviewboard.extensions.packaging.static_media
   reviewboard.extensions.testing
   reviewboard.extensions.testing.testcases


.. seealso::

   :ref:`djblets.extensions <coderef-djblets-extensions>`


Hosting Service Integration
===========================

.. autosummary::
   :toctree: python

   reviewboard.hostingsvcs.base
   reviewboard.hostingsvcs.base.client
   reviewboard.hostingsvcs.base.forms
   reviewboard.hostingsvcs.base.hosting_service
   reviewboard.hostingsvcs.base.http
   reviewboard.hostingsvcs.base.paginator
   reviewboard.hostingsvcs.base.registry
   reviewboard.hostingsvcs.base.repository
   reviewboard.hostingsvcs.errors
   reviewboard.hostingsvcs.forms
   reviewboard.hostingsvcs.hook_utils
   reviewboard.hostingsvcs.models
   reviewboard.hostingsvcs.repository
   reviewboard.hostingsvcs.service
   reviewboard.hostingsvcs.testing
   reviewboard.hostingsvcs.testing.testcases
   reviewboard.hostingsvcs.utils.paginator


Integrations
============

.. autosummary::
   :toctree: python

   reviewboard.integrations
   reviewboard.integrations.base
   reviewboard.integrations.forms
   reviewboard.integrations.models
   reviewboard.integrations.urls
   reviewboard.integrations.views


.. seealso::

   :ref:`djblets.integrations <coderef-djblets-integrations>`


Licensing
=========

.. autosummary::
   :toctree: python

   reviewboard.licensing
   reviewboard.licensing.actions
   reviewboard.licensing.errors
   reviewboard.licensing.features
   reviewboard.licensing.license
   reviewboard.licensing.license_checks
   reviewboard.licensing.provider
   reviewboard.licensing.registry
   reviewboard.licensing.views


E-mail and WebHooks
===================

.. autosummary::
   :toctree: python

   reviewboard.notifications
   reviewboard.notifications.email
   reviewboard.notifications.email.backend
   reviewboard.notifications.email.decorators
   reviewboard.notifications.email.hooks
   reviewboard.notifications.email.message
   reviewboard.notifications.email.utils
   reviewboard.notifications.email.views
   reviewboard.notifications.forms
   reviewboard.notifications.managers
   reviewboard.notifications.models
   reviewboard.notifications.webhooks


Review Requests and Reviews
===========================

.. autosummary::
   :toctree: python

   reviewboard.reviews.actions
   reviewboard.reviews.builtin_fields
   reviewboard.reviews.chunk_generators
   reviewboard.reviews.conditions
   reviewboard.reviews.context
   reviewboard.reviews.default_actions
   reviewboard.reviews.detail
   reviewboard.reviews.errors
   reviewboard.reviews.features
   reviewboard.reviews.fields
   reviewboard.reviews.forms
   reviewboard.reviews.managers
   reviewboard.reviews.markdown_utils
   reviewboard.reviews.models
   reviewboard.reviews.signals
   reviewboard.reviews.templatetags.reviewtags
   reviewboard.reviews.testing
   reviewboard.reviews.testing.queries
   reviewboard.reviews.testing.queries.review_groups
   reviewboard.reviews.testing.queries.review_requests
   reviewboard.reviews.testing.queries.reviews
   reviewboard.reviews.ui.base
   reviewboard.reviews.ui.image
   reviewboard.reviews.ui.markdownui
   reviewboard.reviews.ui.text
   reviewboard.reviews.views.attachments
   reviewboard.reviews.views.bug_trackers
   reviewboard.reviews.views.diff_fragments
   reviewboard.reviews.views.diffviewer
   reviewboard.reviews.views.download_diff
   reviewboard.reviews.views.email
   reviewboard.reviews.views.mixins
   reviewboard.reviews.views.new_review_request
   reviewboard.reviews.views.review_request_detail
   reviewboard.reviews.views.review_request_infobox
   reviewboard.reviews.views.review_request_updates
   reviewboard.reviews.views.root


Repository Communication
========================

.. autosummary::
   :toctree: python

   reviewboard.scmtools.certs
   reviewboard.scmtools.conditions
   reviewboard.scmtools.core
   reviewboard.scmtools.crypto_utils
   reviewboard.scmtools.errors
   reviewboard.scmtools.forms
   reviewboard.scmtools.managers
   reviewboard.scmtools.models
   reviewboard.scmtools.signals
   reviewboard.scmtools.testing
   reviewboard.scmtools.testing.queries
   reviewboard.scmtools.tests.testcases


Search
======

.. autosummary::
   :toctree: python

   reviewboard.search.fields
   reviewboard.search.forms
   reviewboard.search.indexes
   reviewboard.search.search_backends.base
   reviewboard.search.search_backends.elasticsearch
   reviewboard.search.search_backends.registry
   reviewboard.search.search_backends.whoosh
   reviewboard.search.signal_processor
   reviewboard.search.testing


Local Sites
===========

.. autosummary::
   :toctree: python

   reviewboard.site.conditions
   reviewboard.site.context_processors
   reviewboard.site.decorators
   reviewboard.site.middleware
   reviewboard.site.mixins
   reviewboard.site.models
   reviewboard.site.signals
   reviewboard.site.templatetags.localsite
   reviewboard.site.testing
   reviewboard.site.testing.queries
   reviewboard.site.urlresolvers
   reviewboard.site.validation


SSH
===

.. autosummary::
   :toctree: python

   reviewboard.ssh.client
   reviewboard.ssh.errors
   reviewboard.ssh.policy
   reviewboard.ssh.storage
   reviewboard.ssh.utils


Unit Test Helpers
=================

.. autosummary::
   :toctree: python

   reviewboard.testing.hosting_services
   reviewboard.testing.queries
   reviewboard.testing.queries.base
   reviewboard.testing.queries.http
   reviewboard.testing.scmtool
   reviewboard.testing.testcase


Themes
======

.. autosummary::
   :toctree: python

   reviewboard.themes
   reviewboard.themes.context_processors
   reviewboard.themes.ui
   reviewboard.themes.ui.base
   reviewboard.themes.ui.default
   reviewboard.themes.ui.registry


Web API
=======

.. autosummary::
   :toctree: python

   reviewboard.webapi.auth_backends
   reviewboard.webapi.base
   reviewboard.webapi.decorators
   reviewboard.webapi.errors
   reviewboard.webapi.mixins
   reviewboard.webapi.models
   reviewboard.webapi.server_info
   reviewboard.webapi.testing
   reviewboard.webapi.testing.queries
   reviewboard.webapi.tests.base


.. seealso::

   :ref:`djblets.webapi <coderef-djblets-webapi>`
