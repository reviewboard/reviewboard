Review Board
============

[Review Board](https://www.reviewboard.org/) is an open source, web-based code
and document review tool built to help companies, open source projects, and
other organizations keep their quality high and their bug count low.

We began writing Review Board in 2006 to fill a hole in the code review market.
We wanted something open source that could be flexible enough to work with a
variety of workflows, and could take the pain out of the code review process.

Today, it's a vital part of the development process at thousands of projects
and companies, ranging from small startups of two people to enterprises of
thousands.


What does Review Board do?
--------------------------

Review Board tracks changes to your pending code, graphics, documents, and all
discussions around all the decisions made about your product. Our diff viewer
does more than just display diffs: It shows you exactly how your code was
changed, with syntax highlighting, interdiffs, moved line detection,
indentation change indicators, and more.

You can integrate with Review Board using its rich API and extension
frameworks, allowing custom features, review UIs, data analysis, and more to be
built without ever having to fork Review Board.

There's support for Bazaar, ClearCase, CVS, Git, Mercurial, Perforce, Plastic,
and Team Foundation Server, hosted on your own server or on Beanstalk,
Bitbucket, Codebase, GitHub, GitLab, Gitorious, Kiln, or Unfuddle.

To learn more, visit the [Review Board website](https://www.reviewboard.org/).


Setting up Review Board
-----------------------

First, [get Review Board](https://www.reviewboard.org/get/). Our helpful
interactive guide will walk you through what you need to download and install
Review Board.

We can also host Review Board for you at [RBCommons](https://rbcommons.com/).
Management is simple, and we'll take care of all the administrative work.

If you want to get a feel for Review Board, check out the
[demo](http://demo.reviewboard.org/).

For additional information, see our documentation:

* [Review Board User Manual](https://www.reviewboard.org/docs/manual/latest/users/)
* [Review Board Administration Manual](https://www.reviewboard.org/docs/manual/latest/admin/)
* [FAQ](https://www.reviewboard.org/docs/manual/latest/faq/)


Installing Power Pack
---------------------

[Power Pack](https://www.reviewboard.org/powerpack/) extends Review Board,
adding such helpful features as:

* [Report generation](https://www.reviewboard.org/docs/powerpack/latest/powerpack/manual/reports/)
* [PDF document review](https://www.reviewboard.org/docs/powerpack/latest/powerpack/manual/pdf/)
* Better multi-server scalability
* Integration with [Microsoft Team Foundation Server](https://www.visualstudio.com/en-us/products/tfs-overview-vs.aspx)
* Integration with [GitHub Enterprise](https://enterprise.github.com/)
* LDAP/Active Directory user sync (coming soon)

To get started,
[download a trial license](https://www.reviewboard.org/powerpack/trial/), or
read the
[Power Pack documentation](https://www.reviewboard.org/docs/powerpack/latest/)
for more information.


Installing RBTools
------------------

If you're an end-user already using Review Board, you'll want to install
RBTools, our command line suite for working with Review Board.

RBTools makes it easy to post changes for review, land reviewed changes,
patch your local tree with someone else's changes, check your workload, and
much more.

RBTools can be [installed](https://www.reviewboard.org/downloads/rbtools/) on
Windows, Linux, Mac, and other platforms. See the
[RBTools documentation](https://www.reviewboard.org/docs/rbtools/latest/) for
everything it can do.


Getting Support
---------------

We can help you get going with Review Board, and diagnose any issues that may
come up. There are two levels of support: Public community support, and private
premium support.

The public community support is available on our main
[discussion list](http://groups.google.com/group/reviewboard/). We generally
respond to requests within a couple of days. This support works well for
general, non-urgent questions that don't need to expose confidential
information.

We can also provide more
[dedicated, private support](https://www.beanbaginc.com/support/contracts/) for
your organization through a support contract. We offer same-day responses
(generally within a few hours, if not sooner), confidential communications,
installation/upgrade assistance, emergency database repair, phone/chat (by
appointment), priority fixes for urgent bugs, and backports of urgent fixes to
older releases (when possible).


Our Happy Users
---------------

There are thousands of companies and organizations using Review Board today.
We respect the privacy of our users, but some of them have asked to feature them
on the [Happy Users page](https://www.reviewboard.org/users/).

If you're using Review Board, and you're a happy user,
[let us know!](https://groups.google.com/group/reviewboard/)


Reporting Bugs
--------------

Hit a bug? Let us know by
[filing a bug report](https://www.reviewboard.org/bugs/new/).

You can also look through the
[existing bug reports](https://www.reviewboard.org/bugs/) to see if anyone else
has already filed the bug.


Contributing
------------

Are you a developer? Do you want to integrate with Review Board, or work on
Review Board itself? Great! Let's help you get started.

First off, we have a few handy guides:

* [Web API Guide](https://www.reviewboard.org/docs/manual/latest/webapi/)
* [Extending Review Board](https://www.reviewboard.org/docs/manual/latest/webapi/)
* [Contributor Guide](https://www.reviewboard.org/docs/codebase/dev/)

We accept patches to Review Board, RBTools, and other related projects on
[reviews.reviewboard.org](https://reviews.reviewboard.org/). (Please note that
we do not accept pull requests.)

Got any questions about anything related to Review Board and development? Head
on over to our
[development discussion list](https://groups.google.com/group/reviewboard-dev/).


Related Projects
----------------

* [Djblets](https://github.com/djblets/djblets/) -
  Our pack of Django utilities for datagrids, API, extensions, and more. Used
  by Review Board.
* [RBTools](https://github.com/reviewboard/rbtools/) -
  The RBTools command line suite.
* [ReviewBot](https://github.com/reviewboard/ReviewBot/) -
  Pluggable, automated code review for Review Board.
* [rb-gateway](https://github.com/reviewboard/rb-gateway/) -
  Manages Git repositories, providing a full API enabling all of Review Board's
  feaures.
