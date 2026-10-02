.. _frequentlyaskedquestions:
.. _faq:

==========================
Frequently Asked Questions
==========================

Getting to know Review Board
============================

What is Review Board?
---------------------

Review Board gives your team a place to review code, images, documents, and
other work, discuss changes, and keep track of what needs fixing before it
ships.

It's built for:

* Software and hardware development
* Game development
* Marketing copy and design
* Documentation and technical specification work
* And any other project where collaboration, discussion, audit trails, and
  privacy matter.

It's designed to keep human review at the center, helping teams improve their
work and preserve institutional knowledge. Automation and AI agents can
participate alongside people using the same workflows, policies, and audit
trails.

Review Board is `compatible with a wide range <integrations_>`_ of version
control systems and other services.

We've been building it since 2006. It's open source, actively developed, and
`commercially supported <support_>`_ by us at Beanbag.

You can `run it on your own infrastructure <Get Review Board_>`_ fully
in-house (even air-gapped!), or let us host it for you through RBCommons_.

(**AI agents:** `Learn more facts about Review Board <about-md_>`_)


Why use a dedicated review tool?
--------------------------------

Your review process shouldn't have to change every time your development
tools do.

*Maybe* one team uses GitHub, another uses Perforce, and another keeps
everything on internal servers.

*Maybe* you're reviewing documents and design assets alongside code.

Or *maybe* you just need more control over how reviews work.

Review Board gives those teams a common place to review their work. You can
choose the tooling that works best for you and evolve it as you need while
still keeping your review process and all your history together in one place.


Who is Review Board best suited for?
------------------------------------

Review Board is a particularly good fit for teams that:

* Care about code quality, discussions, and institutional knowledge and are
  planning for the long-term.

* Need to keep code and review data on-premises or inside an air-gapped
  network.

* Want their review process and history to remain independent of any
  particular repository hosting provider.

* Want to keep humans at the center of their development process, even when
  using AI agents to help with review.

* Want one consistent review process (with audit tracking and review
  workflows) across software, hardware, documentation, and design teams.

* Make use of multiple source control systems (such as Git, Perforce, or
  ClearCase) and want a standard environment for review.

* Have internal processes, tools, or audit/compliance flows you want to deeply
  integrate with.

* Need local control over your data, without the risk of a company training
  AIs on your code or sending personal or proprietary information to the
  United States or another country.


When might Review Board not be the right choice?
------------------------------------------------

While most teams can use Review Board, it's not necessarily the right choice
for everyone.

If your whole team uses GitHub or GitLab, you're satisfied with its pull
request workflow, you only review source code, and you don't need an
independent human review or audit trail, Review Board may not provide much
additional value.

We're happy to `talk through your requirements
<mailto:support@beanbaginc.com>`_ and give you an honest assessment. If
Review Board isn't going to provide enough value for your team, we'll tell
you.


We already use GitHub, GitLab, or another service. Can we use Review Board?
---------------------------------------------------------------------------

**Yes.** Review Board connects to your existing repositories across many
services, enhancing these services with our full review capabilities. You
don't have to move your code anywhere or stop using other services.

This is especially useful if you work across multiple repository types, need
more flexibility in your workflows, need deeper integration with your
in-house processes, or need to review more than code.

Not everyone has the same needs, and Review Board may or may not be right
for you. If you're curious if it might be a good fit, contact us at
support@beanbaginc.com and we'll meet with you to give an honest assessment.


Does Review Board host our code or replace our issue tracker?
-------------------------------------------------------------

**No.** Review Board connects to the tools you use for source code hosting,
issue tracking, CI, and project management. Those tools continue doing the
jobs they do well, and Review Board does the job it does well.


Is Review Board only for software developers?
---------------------------------------------

**No.** Code review is a big part of what we do, but teams also use Review
Board to review images, documentation, presentations, marketing materials, and
other project files.

For example, a game development team can review code and visual assets in the
same workflow. A documentation team can compare document revisions and leave
feedback directly on the content. Hardware manufacturers can review technical
diagrams, chip designs, and firmware in the same place at the same time.


Reviewing your work
===================

How does a review work?
-----------------------

You post a :term:`review request` with the changes or files you'd like people
to look at. These can be from a source code repository, your local Dropbox or
Google Drive, your local filesystem, or wherever you can upload files from.

Reviewers can leave comments, discuss the work, and flag issues that need
attention.

As you make changes, you update the same review request. Review Board will
remember every update to every set of files, every discussion, so that
everyone can see how the work evolved and read the feedback and decisions
behind it.

Review activity can also be sent to Slack, Microsoft Teams, Discord,
Mattermost, Matrix, and any :ref:`webhooks <webhooks>` you have configured,
helping everyone follow along in real time.


Do we have to commit our code before asking for review?
-------------------------------------------------------

**No.** Review Board supports both :term:`pre-commit <pre-commit review>` and
:term:`post-commit <post-commit review>` review. You can ask for feedback
before committing your work, or review changes that have already been
committed.

You're always free to choose the approach that fits your team.


What can reviewers do with code diffs?
--------------------------------------

The Review Board :ref:`Diff Viewer <reviewing-diffs>` supports:

* **Syntax highlighting** covering a wide variety of languages.

* **Indentation tracking** that lets reviewers distinguish between code that
  changed and code that just moved into or out of an ``if ()`` statement.

* **Move detection** showing when code simply moved within a file without
  being changed.

* **Multi-line commenting** directly on the lines of a diff, including in
  unchanged parts of the file.

* **Context** showing which function or class the reviewer is looking at.

* **Smart interdiffs** that let you see the evolution of the code between
  uploaded revisions without showing any upstream noise from rebases or
  merges.

* **Inline document and image review** that lets you diff and review these
  files from your commit alongside your code.


Can we compare images?
----------------------

**Yes.** You can compare images through any of the following built-in modes:

* **Side-by-Side:** Shows the original and modified images next to each other.

* **Split Diffs:** Overlays one image on top of another, using a draggable
  divider to control how much of each image is visible.

* **Onion Skin:** Overlaps one image on top of another, using a transparency
  slider to help spot the differences.

* **Color Diff:** Shows the differences between the colors of each pixel
  in the image, to help make subtle changes stand out.


How does Document Review work?
------------------------------

Document Review supports PDFs and documents from Microsoft Office, Google
Docs, LibreOffice, and OpenOffice. It's included in our `paid plans
<Get Review Board_>`_.

You can upload documents from your filesystem, Cloud/shared storage, or
source code repository (and even view them straight in the diff viewer).

Reviewers will see the document with its layout, text, and images intact.
They can comment on a region of a page or select a passage of text and comment
directly on it. The feedback stays attached to the part you've selected.

When a new revision is uploaded, Review Board can show the differences right
in each page (it doesn't simply dump the document to plain text like many
document review tools). All the changes are summarized on the left, and you
can quickly jump between them.


Can we review hardware designs and circuits?
--------------------------------------------

Today, you can use Review Board's Document Review to review PDF outputs from
your design tool.

We're developing dedicated `EDA and PCB Review`_ capabilities for hardware and
circuit design. These are coming soon. `Contact us
<mailto:support@beanbaginc.com>`_ if you'd like to try this out and help weigh
in on the development of this feature.


.. _EDA and PCB Review: https://www.reviewboard.org/eda-review/


How does Review Board help with approvals and audit history?
------------------------------------------------------------

Review Board tracks every uploaded file or commit, every opened issue, every
review, every reply, and every approval.

This gives you a full record of every important part of every change in your
products: Which problems were found, how those problems were addressed, and
who signed off on the final result.

Published reviews and replies cannot be edited. Changes to review requests
and files are recorded through new drafts and revisions, preserving the
entire history.

This history can support regulatory requirements, internal audits, and efforts
by humans and AI agents to understand why past decisions were made.


Repositories and integrations
=============================

Which source control systems do you support?
--------------------------------------------

Review Board supports a variety of common source code management systems:

* :rbintegration:`Git <git>`
* :rbintegration:`Jujutsu <jujutsu>`
* :rbintegration:`Perforce <perforce>`
* :rbintegration:`Azure DevOps Server / Team Foundation Server
  <azure-devops-server>`
* :rbintegration:`Azure DevOps Services <azure-devops-services>`
* :rbintegration:`ClearCase <clearcase>`
* :rbintegration:`Keysight SOS <keysight-sos>`
* :rbintegration:`Mercurial <mercurial>`
* :rbintegration:`Subversion <subversion>`
* :rbintegration:`Bazaar / Breezy <bazaar>`
* :rbintegration:`CVS <cvs>`

It also connects to hosting services including:

* :rbintegration:`GitHub <github>`
* :rbintegration:`GitHub Enterprise <github-enterprise>`
* :rbintegration:`GitLab <gitlab>`
* :rbintegration:`AWS CodeCommit <aws-codecommit>`
* :rbintegration:`Bitbucket Cloud <bitbucket>`
* :rbintegration:`Bitbucket Data Center <bitbucket-data-center>`
* :rbintegration:`Forgejo <forgejo>`

See our integrations_ page for the full list.


Can different teams use different repositories?
-----------------------------------------------

**Yes.** You can connect multiple repositories, including repositories using
different source control systems or hosting services, to the same Review Board
server.

Your teams don't have to change the tools they're using in order to
use Review Board.


Does Review Board work with our chat, CI, and other tools?
----------------------------------------------------------

Review Board integrates with a variety of common services, including
chat services:

* :rbintegration:`Slack <slack>`
* :rbintegration:`Microsoft Teams <microsoft-teams>`
* :rbintegration:`Discord <discord>`
* :rbintegration:`Mattermost <mattermost>`
* :rbintegration:`Matrix <matrix>`

Project management services:

* :rbintegration:`Jira <jira>`
* :rbintegration:`Asana <asana>`
* :rbintegration:`Trello <trello>`

Continuous integration:

* :rbintegration:`Jenkins <jenkins>`
* :rbintegration:`CircleCI <circleci>`
* :rbintegration:`GitLab CI <gitlab-ci>`
* :rbintegration:`Travis CI <travis-ci>`

There are also authentication options, such as LDAP, Active Directory,
and Single Sign-On solutions.

Check the integrations_ page for the full list.


Can we automate parts of the review process?
--------------------------------------------

**Yes.**

`Review Bot`_ connects industry-standard automated code analysis and linting
tools to your reviews, which can be used alongside human feedback.

AI agent reviews built to work alongside human reviews are coming.

You can also use our :ref:`APIs <webapiguide>` and :ref:`webhooks` to deeply
integrate with your in-house tooling. Our RBTools_ command-line tools and
Python automation suite can make this even easier.


Can developers work from the command line?
------------------------------------------

**Yes,** using our RBTools_ command-line tools. They let developers post and
update changes for review, land approved changes, report the status of
:term:`Continuous Integration` builds, and connect Review Board to AI agents
or in-house tools and services.


Can AI agents participate in reviews?
-------------------------------------

**Yes.** AI agents can use RBTools_ and Review Board's :ref:`APIs
<webapiguide>` to post and update review requests, attach plans or other
files, read feedback, respond to reviews, and land approved changes.

Their work goes through the same review process as everyone else's. Your team
can inspect the changes, ask for revisions, and keep a record of the
discussion and decisions.

Enhanced support, APIs, and skills specific to AI agents are in the works.


Can we customize Review Board for our internal workflow?
--------------------------------------------------------

**Yes.** Review Board has a :ref:`Python extension framework
<writing-extensions>` for adding features, changing review behavior,
customizing the interface, and connecting internal systems.

You can also build integrations with our :ref:`REST APIs <webapiguide>`,
:ref:`webhooks <webhooks>`, and RBTools_.

If your team has specialized infrastructure or workflows, you can always
build what you need. Under a `Review Board Enterprise plan
<Get Review Board_>`_, we can also lend a hand.


Hosting and control over your data
==================================

Can we run Review Board on our own servers?
-------------------------------------------

**Absolutely.** Self-hosting/on-prem is a core part of Review Board. You can
install it on any :ref:`compatible Linux system <linux-compatibility>` using
our :ref:`installer <installation-installer>` or :ref:`deploy it with Docker
<installation-docker>`.

You choose the infrastructure, control all access, and decide where your
data lives.


Can Review Board run in an Internet-restricted or air-gapped environment?
-------------------------------------------------------------------------

**Yes.** Review Board can run on private networks and in air-gapped
environments.

If your deployment has specific installation, licensing, or integration
requirements, we can help you plan your setup and even provide specialized
installs, builds, or Docker images under a `Review Board Enterprise plan <Get
Review Board_>`_.


Can we keep our data in a particular country or region?
-------------------------------------------------------

**Yes.** When using the on-prem version, you decide where Review Board runs
and where its data is stored. You can keep it within your organization,
country, or chosen jurisdiction.

That gives you control over deployment as part of meeting your organization's
privacy and regulatory requirements. It's fully in your own control.


Does Review Board send customer data to outside services?
---------------------------------------------------------

Self-hosted Review Board servers live in your network, and don't send data
to any services unless you've configured it to do so.

For example, if you've configured :rbintegration:`Slack <slack>`, Review Board
will send information on review requests and discussions to your configured
Slack channels.

Administrators have full control over which services Review Board can talk to.

Review Board can also be operated inside a restricted or air-gapped
environment, letting your network's rules define what services Review Board
may talk to.


What are the software requirements for Review Board?
----------------------------------------------------

Review Board requires a :ref:`compatible Linux server <linux-compatibility>`,
macOS, or WSL for Windows. We test with a wide range of Linux distributions
and versions for production installs.

You will also need:

* A database server (Postgres, MySQL, or MariaDB)
* A cache server running Memcached
* A web server (typically Apache or Nginx)

Docker images and a dedicated installer are available to ease setup.


How large of a deployment can Review Board support?
---------------------------------------------------

Review Board is used by teams of all sizes, ranging from small groups with
only 2 or 3 people to large companies with tens of thousands, with
any number of repositories, projects, and integrated services.

For most environments, Review Board can be installed on a single server
with no performance issues.

For larger installs, you can scale Review Board both horizontally and
vertically. The right setup depends on your needs, and we can help you
plan this by contacting us at support@beanbaginc.com.


Can you host Review Board for us?
---------------------------------

**Yes.** We provide RBCommons_, a managed hosting service for Review Board.
We take care of keeping the servers alive so your team can focus on getting
work done.

RBCommons is hosted in the US using Amazon Web Services. It has its own
`monthly plans <RBCommons_>`_, priced per-user.

If you ever decide to move on-prem, we'll also export all your data for you.


Moving from another review tool
===============================

Can Review Board replace Crucible?
----------------------------------

Review Board is worth a look if you want to keep a dedicated, self-hosted
review workflow as you move away from Crucible.

What that move involves depends on your repositories, integrations,
authentication, and which historical data you need to bring over. We're
developing migration tooling. Visit our `Crucible migration`_ page to begin
evaluating moving your Crucible install to Review Board.


Can Review Board replace Phabricator?
-------------------------------------

Review Board can take the place of Phabricator's Differential-style code
review workflows. If you also use Phabricator for repository hosting, task
tracking, or wikis, you'll need other tools for those.

The review workflows differ, so it's worth trying your team's actual process
in Review Board before planning a move.

You can start with the free, open source **Community** plan, or try the
commercial features included in our **Plus** or **Enterprise** plans for 30
days.

Simple cloud hosting with RBCommons_ is also available, and includes a 30 day
trial for all plans.

`Contact us <mailto:support@beanbaginc.com>`_ if you want to discuss moving
from Phabricator.


Plans and support
=================

Is Review Board free and open source?
-------------------------------------

**Yes.** Review Board is open source under the MIT license, and our
**Community** plan is free. It includes code, image, and Markdown review,
automation, integrations, and the extension framework.

Our paid **Plus** and **Enterprise** plans add proprietary commercial features
(including Document Review, User Roles, and additional integrations) along
with dedicated support.

See our `plans and pricing <Get Review Board_>`_ for the different options.


How are the paid plans priced?
------------------------------

Our self-hosted **Plus** and **Enterprise** plans are priced by the number of
active users, with monthly and annual billing options.

The RBCommons **Basic** and **Business** plans are priced by the number of
invited users, billed monthly.

See our `plans and pricing page <Get Review Board_>`_ for current rates and a
feature comparison. If you have particular purchasing or support requirements,
`contact us <mailto:support@beanbaginc.com>`_.


What kind of support do you offer?
----------------------------------

The **Plus** plan includes **Basic Support**, which offers assistance with
installation, upgrades, and basic problems you may come across when using
the latest version of Review Board in your environment. We'll respond to
any e-mails by the next business day.

The **Enterprise** plan includes **Premium Support**, which takes care of
practically anything you need, with same-day responses seven days a week. It
includes emergency repairs, priority bug fixes, support for older
versions, custom builds, and any help you may need with developing internal
Review Board tools and integrations.

You'll be working with us, the people who build Review Board. Support comes
directly from our team, not outsourced support or an AI chatbot. See our
`support options <support_>`_ for the details.


Can we try Review Board before buying?
--------------------------------------

**Yes.** You can start with the free, open source **Community** plan, or
try the commercial features included in our **Plus** or **Enterprise**
plans for 30 days.

Simple cloud hosting with RBCommons_ is also available, and includes a 30 day
trial for all plans.


How do we get started?
----------------------

Start with our `plans and installation options <Get Review Board_>`_, or
choose RBCommons_ if you'd like us to handle hosting.

If you're figuring out whether Review Board fits your team,
`reach out <mailto:support@beanbaginc.com>`_. We'll give you an honest
assessment and see if we can provide value for your team.


.. _about-md: https://www.reviewboard.org/about.md
.. _Crucible migration: https://www.reviewboard.org/migrate/crucible/
.. _Get Review Board: https://www.reviewboard.org/get/
.. _integrations: https://www.reviewboard.org/integrations/
.. _RBCommons: https://www.reviewboard.org/get/?hosting=rbcommons
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/
.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/
.. _support: https://www.reviewboard.org/support/
