.. _rb-users-guide:
.. _usersguide:

===========
Users Guide
===========

Review Board is an extensible, feature-rich, open source code review product
commonly used used to help with the peer code review and document review
processes. It's ideal for source code, documentation, images, and more.

It's built to work with a wide variety of environments, `team collaboration
and CI services`_, and source code management systems, such as:

* :rbintegration:`Git <git>`
* :rbintegration:`Mercurial <mercurial>`
* :rbintegration:`Perforce <perforce>`
* :rbintegration:`Cliosoft SOS <cliosoft-sos>`
* :rbintegration:`IBM ClearCase <clearcase>`
* :rbintegration:`HCL VersionVault <versionvault>`
* :rbintegration:`Microsoft Azure DevOps / TFS / Team Foundation Services
  <tfs>`

Plus `many more <https://www.reviewboard.org/integrations/>`_.

Review Board can be :ref:`extended in-house <extensions-overview>`, allowing
companies to build new first-class features, tweak policies, and better
integrate with their existing systems. This provides opportunities not
available with other code review products.


.. _team collaboration and CI services:
   https://www.reviewboard.org/integrations/


Getting Started with Code Review
================================

New to code review? Start here to learn some of the basics before you get going
with Review Board.

* :doc:`What is code review? <getting-started/what-is-code-review>`
* :doc:`Review Board workflows <getting-started/workflow>`


The Dashboard: Your Code Review Inbox
=====================================

The first thing you'll generally see when you log in is the Dashboard. This
tracks all the review requests you've posted and all the ones sent your way
for review. It's customizable, letting you show and filter things just the way
you want.

* :doc:`Learn about the Dashboard <dashboard/index>`


Managing Your Account
=====================

Once you get going with Review Board, you'll want to take a look at your
account settings. Here you'll be able to update your profile information (such
as your name and e-mail address), join :term:`review groups`, customize your
settings, manage API tokens, and more.

* :doc:`Manage your account settings <settings>`


Creating and Managing Review Requests
=====================================

A review request is a proposed change, a collection of code, documents, or
other content, which is published for review. They can be modified in a draft
state and then published for others to see.

Review requests are central to Review Board, and you'll want to learn how to
work with them. We recommend starting with the overview.


Getting started
---------------

* :doc:`Overview of review requests <review-requests/overview>`
* :doc:`Creating review requests <review-requests/creating>`


Making changes
--------------

* :doc:`Editing review request fields <review-requests/fields>`
* :doc:`Uploading new diff revisions <review-requests/uploading-diffs>`
* :doc:`Uploading file attachments <review-requests/uploading-files>`


Finishing up your changes
-------------------------

* :doc:`Publishing drafts <review-requests/publishing>`
* :doc:`Closing or discarding review requests <review-requests/closing>`


Reviewing Code and Documents
============================

Review requests can store all kinds of content, from code to documents to
images to arbitrary files. In this section, we'll tell you how to review that
content.


Basic concepts
--------------

* :doc:`Reviews and comments <reviews/reviews>`
* :doc:`The review banner <reviews/banner>`
* :doc:`Tracking issues <reviews/issue-tracking>`
* :doc:`Managing and publishing drafts <reviews/drafts>`


Reviewing content
-----------------

* :doc:`Reviewing code (diffs) <reviews/reviewing-diffs>`
* :doc:`Reviewing file attachments (overview) <reviews/reviewing-files>`
* :doc:`Reviewing image file attachments <reviews/reviewing-images>`
* :doc:`Reviewing Markdown file attachments <reviews/reviewing-markdown>`
* :doc:`Reviewing text file attachments <reviews/reviewing-text-files>`
* :doc:`Automated code review <reviews/automated-review/index>`


Managing reviews
----------------

* :doc:`Creating and editing reviews <reviews/editing-reviews>`
* :doc:`Approving changes (Ship It!) <reviews/approving-changes>`


Discussing reviews
------------------

* :doc:`Replying to comments <reviews/replying>`


Editing in Markdown
===================

When composing review requests, reviews, or replying to comments, you have the
option of using Markdown. Spice up your text with text formatting, code
samples, images, and more.

* :doc:`Complete guide to using Markdown <markdown>`

For your convenience, here's some sections you might be interested in.

* :ref:`Basic syntax for Markdown <markdown-basic-syntax>`
* :ref:`Providing code samples <markdown-code-syntax>`
* :ref:`Using Emoji <emoji>`
* :ref:`Uploading images <markdown-upload-images>`


Searching for Review Requests and Users
=======================================

Depending on your server's :ref:`search settings <search-settings>`, you
may be able to look up review requests and users through a handy search
field at the top of any page.

If full support for search is enabled, you'll be able to take advantage of
full-text search. If not, you'll still be able to use what we call Quick
Search, a more limited but still useful way of quickly locating and jumping to
a review request or user.

* :doc:`Using Quick Search <searching/quick-search>`
* :doc:`Using full-text search <searching/full-text-search>`


.. toctree::
   :hidden:

   getting-started/index
   settings
   dashboard/index
   review-requests/index
   reviews/index
   searching/index
   markdown
