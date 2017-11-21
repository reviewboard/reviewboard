.. _reviewboard-coderef:

===========================
Module and Class References
===========================


Top-Level Modules
=================

.. autosummary::
   :toctree: python

   reviewboard
   reviewboard.rb_platform
   reviewboard.signals


User Accounts
=============

.. autosummary::
   :toctree: python

   reviewboard.accounts.backends
   reviewboard.accounts.decorators
   reviewboard.accounts.errors
   reviewboard.accounts.managers
   reviewboard.accounts.mixins
   reviewboard.accounts.models
   reviewboard.accounts.pages
   reviewboard.accounts.trophies
   reviewboard.accounts.forms.auth
   reviewboard.accounts.forms.pages
   reviewboard.accounts.forms.registration


File Attachments
================

.. autosummary::
   :toctree: python

   reviewboard.attachments.forms
   reviewboard.attachments.managers
   reviewboard.attachments.mimetypes
   reviewboard.attachments.models


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
   reviewboard.diffviewer.myersdiff
   reviewboard.diffviewer.opcode_generator
   reviewboard.diffviewer.parser
   reviewboard.diffviewer.processors
   reviewboard.diffviewer.renderers
   reviewboard.diffviewer.smdiff


Extensions
==========

.. autosummary::
   :toctree: python

   reviewboard.extensions.base
   reviewboard.extensions.hooks
   reviewboard.extensions.packaging
   reviewboard.extensions.testing
   reviewboard.extensions.testing.testcases


Hosting Service Integration
===========================

.. autosummary::
   :toctree: python

   reviewboard.hostingsvcs.errors
   reviewboard.hostingsvcs.forms
   reviewboard.hostingsvcs.hook_utils
   reviewboard.hostingsvcs.repository
   reviewboard.hostingsvcs.service


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


E-mail and WebHooks
===================

.. autosummary::
   :toctree: python

   reviewboard.notifications
   reviewboard.notifications.email
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
   reviewboard.reviews.chunk_generators
   reviewboard.reviews.context
   reviewboard.reviews.default_actions
   reviewboard.reviews.detail
   reviewboard.reviews.errors
   reviewboard.reviews.fields
   reviewboard.reviews.forms
   reviewboard.reviews.managers
   reviewboard.reviews.markdown_utils
   reviewboard.reviews.models
   reviewboard.reviews.signals
   reviewboard.reviews.ui.base
   reviewboard.reviews.ui.image
   reviewboard.reviews.ui.text


Repository Communication
========================

.. autosummary::
   :toctree: python

   reviewboard.scmtools.certs
   reviewboard.scmtools.core
   reviewboard.scmtools.crypto_utils
   reviewboard.scmtools.errors
   reviewboard.scmtools.forms
   reviewboard.scmtools.managers
   reviewboard.scmtools.models
   reviewboard.scmtools.signals


Search
======

.. autosummary::
   :toctree: python

   reviewboard.search.indexes


Local Sites
===========

.. autosummary::
   :toctree: python

   reviewboard.site.decorators
   reviewboard.site.mixins
   reviewboard.site.models
   reviewboard.site.signals
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

   reviewboard.testing.testcase


Web API
=======

.. autosummary::
   :toctree: python

   reviewboard.webapi.base
   reviewboard.webapi.decorators
   reviewboard.webapi.errors
   reviewboard.webapi.mixins
   reviewboard.webapi.models
   reviewboard.webapi.server_info
