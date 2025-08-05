.. _frequentlyaskedquestions:
.. _faq:

==========================
Frequently Asked Questions
==========================

What is Review Board?
=====================

Review Board is a free, open source, web-based code and document review tool.
We built it to help developers and team members collaboratively review code,
graphics, documents, and more.

With Review Board, you can build better projects together, with one of the
longest-supported review products on the market. It's an ideal fit for teams,
organizations, and companies of any size.


Is Review Board free for commercial use?
========================================

Yes! Review Board is absolutely free for commercial use, and can be used for
any number of users without a license, fee, or activation.

This makes it a very cost-effective solution for your company, with no
surprises or rate hikes.

`Support contracts`_ are available to help support your server and IT
department. This can provide peace of mind, ensuring you're not alone if a bad
upgrade or outage puts a stop to productivity at your company.

We can also help you with performance tuning, migration planning, and custom
development under a contract.


What license is Review Board under?
===================================

Review Board is under the MIT license.


Which version control systems does Review Board support?
========================================================

Review Board supports a variety of common source code management systems:

* :rbintegration:`Git <git>`
* :rbintegration:`Mercurial <mercurial>`
* :rbintegration:`Perforce <perforce>`
* :rbintegration:`Subversion <subversion>`
* :rbintegration:`Bazaar / Breezy <bazaar>`
* :rbintegration:`CVS <cvs>`

And more enterprise/market-focused systems through `Power Pack`_.

* :rbintegration:`Azure DevOps / Team Foundation Server <tfs>`
* :rbintegration:`Cliosoft SOS <cliosoft-sos>`
* :rbintegration:`HCL VersionVault <versionvault>`
* :rbintegration:`IBM ClearCase <clearcase>`

We're able to quickly add support for new systems as they come out, making
Review Board a future-proof solution for your company, organization, or
project.


Can Review Board be integrated with other tools?
================================================

Yes. Review Board natively provides `integrations with many services
<integrations_>`_, including...

Chat services:

* :rbintegration:`Discord <discord>`
* :rbintegration:`Matrix <matrix>`
* :rbintegration:`Mattermost <mattermost>`
* :rbintegration:`Slack <slack>`

Continuous integration services:

* :rbintegration:`CircleCI <circleci>`
* :rbintegration:`Jenkins <jenkins>`
* :rbintegration:`Travis CI <travis-ci>`

Project management services:

* :rbintegration:`Asana <asana>`
* :rbintegration:`I Done This <idonethis>`
* :rbintegration:`Trello <trello>`

Custom integrations for any service you need can be written in Python. See
our documentation on :ref:`writing extensions for Review Board
<writing-extensions>`.


Does Review Board support automatic code review?
================================================

It does, with `Review Bot`_!

Review Bot is an extension to Review Board that adds automated code reviews to
your workflow. It integrates with an assortment of third-party code lint,
compliance, and security checking tools to help catch problems early.

It's free, open source, and extensible, making it a great addition to your
Review Board server.


Does Review Board work with our authentication service?
=======================================================

Review Board works with:

* Active Directory
* LDAP
* Single Sign-On services using SAML, including:

  * :rbintegration:`Auth0 <auth0>`
  * :rbintegration:`Okta <okta>`
  * :rbintegration:`OneLogin <onelogin>`


Can we customize Review Board to fit our needs?
===============================================

Absolutely! We have a lot of options within the product to help customize it
to your needs, to connect to other services and tools you may use, and to help
define your workflows.

Review Board can be further customized by :ref:`writing extensions
<writing-extensions>`. With extensions, you can tailor Review Board in almost
any way you can imagine, helping make it a tool truly built for your
organization.


Can I contribute to Review Board?
=================================

Yes, and we'd love that! As an open-source project, Review Board welcomes
contributions of all kinds from the community.

You can contribute by:

* `Reporting bugs or feature requests`_
* `Submitting patches`_ for bug fixes, features, or documentation
* `Discussing on our discussion group`_
* Advocating for Review Board in your organization


How can I get started or learn more?
====================================

To get started, head over to the `Get Review Board`_ page and follow the steps
to get personalized installation instructions for your system.

You can also read through our documentation on:

* :ref:`Installing Review Board <installing-reviewboard-toc>`
* :ref:`Administering Review Board <administration-guide>`
* :ref:`Using Review Board <rb-users-guide>`
* `Review Bot`_ automated code review for Review Board
* `RBTools`_ command line tools for Review Board
* `Power Pack`_ document review, reports, management, and integrations for
  Review Board


.. _Get Review Board: https://www.reviewboard.org/get/
.. _integrations: https://www.reviewboard.org/integrations/
.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/
.. _Reporting bugs or feature requests:
   https://hellosplat.com/s/beanbag/tickets/
.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/
.. _Submitting patches: https://reviews.reviewboard.org/
.. _support contracts: https://www.reviewboard.org/support/
.. _Discussing on our discussion group:
   https://groups.google.com/g/reviewboard
