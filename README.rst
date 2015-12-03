Review Board
============

`Review Board`_ is an open source, web-based code and document review tool
built to help companies, open source projects, and other organizations keep
their quality high and their bug count low.

We began writing Review Board in 2006 to fill a hole in the code review market.
We wanted something open source that could be flexible enough to work with a
variety of workflows, and could take the pain out of the code review process.

Today, it's a vital part of the development process at thousands of projects
and companies, ranging from small startups of two people to enterprises of
thousands.

.. _`Review Board`: https://www.reviewboard.org/


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
and Team Foundation Server, hosted on your own server or on Assembla,
Beanstalk, Bitbucket, Codebase, GitHub, GitLab, Gitorious, Kiln, or Unfuddle.

To learn more, visit the `Review Board website`_.

.. _`Review Board website`: https://www.reviewboard.org/


Setting up Review Board
-----------------------

First, `get Review Board <https://www.reviewboard.org/get/>`_. Our helpful
interactive guide will walk you through what you need to download and install
Review Board.

We can also host Review Board for you at RBCommons_. Management is simple,
and we'll take care of all the administrative work.

If you want to get a feel for Review Board, check out the demo_.

For additional information, see our documentation:

* `Review Board User Manual`_
* `Review Board Administration Manual`_
* FAQ_

.. _RBCommons: https://rbcommons.com/
.. _demo: http://demo.reviewboard.org/
.. _`Review Board User Manual`:
   https://www.reviewboard.org/docs/manual/latest/users/
.. _`Review Board Administration Manual`:
   https://www.reviewboard.org/docs/manual/latest/admin/
.. _FAQ: https://www.reviewboard.org/docs/manual/latest/faq/


Installing Power Pack
---------------------

`Power Pack`_ extends Review Board, adding such helpful features as:

* `Report generation`_
* `PDF document review`_
* Better multi-server scalability
* Integration with `Microsoft Team Foundation Server`_
* Integration with `GitHub Enterprise`_
* LDAP/Active Directory user sync (coming soon)

To get started, `download a trial license`_, or read the
`Power Pack documentation`_ for more information.

.. _`Power Pack`: https://www.reviewboard.org/powerpack/
.. _`Report generation`:
   https://www.reviewboard.org/docs/powerpack/latest/powerpack/manual/reports/
.. _`PDF document review`:
   https://www.reviewboard.org/docs/powerpack/latest/powerpack/manual/pdf/
.. _`Microsoft Team Foundation Server`:
   https://www.visualstudio.com/en-us/products/tfs-overview-vs.aspx
.. _`GitHub Enterprise`: https://enterprise.github.com/
.. _`download a trial license`: https://www.reviewboard.org/powerpack/trial/
.. _`Power Pack documentation`:
   https://www.reviewboard.org/docs/powerpack/latest/


Installing RBTools
------------------

If you're an end-user already using Review Board, you'll want to install
RBTools, our command line suite for working with Review Board.

RBTools makes it easy to post changes for review, land reviewed changes,
patch your local tree with someone else's changes, check your workload, and
much more.

RBTools can be `installed <https://www.reviewboard.org/downloads/rbtools/>`_
on Windows, Linux, Mac, and other platforms. See the `RBTools documentation`_
for everything it can do.

.. _`RBTools documentation`: https://www.reviewboard.org/docs/rbtools/latest/


Getting Support
---------------

We can help you get going with Review Board, and diagnose any issues that may
come up. There are two levels of support: Public community support, and private
premium support.

The public community support is available on our main `discussion list`_. We
generally respond to requests within a couple of days. This support works well
for general, non-urgent questions that don't need to expose confidential
information.

We can also provide more
`dedicated, private support <https://www.beanbaginc.com/support/contracts/>`_
for your organization through a support contract. We offer same-day responses
(generally within a few hours, if not sooner), confidential communications,
installation/upgrade assistance, emergency database repair, phone/chat (by
appointment), priority fixes for urgent bugs, and backports of urgent fixes to
older releases (when possible).

.. _`discussion list`: https://groups.google.com/group/reviewboard/


Our Happy Users
---------------

There are thousands of companies and organizations using Review Board today.
We respect the privacy of our users, but some of them have asked to feature them
on the `Happy Users page`_.

If you're using Review Board, and you're a happy user,
`let us know! <https://groups.google.com/group/reviewboard/>`_.


.. _`Happy Users page`: https://www.reviewboard.org/users/


Reporting Bugs
--------------

Hit a bug? Let us know by
`filing a bug report <https://www.reviewboard.org/bugs/new/>`_.

You can also look through the
`existing bug reports <https://www.reviewboard.org/bugs/>`_ to see if anyone
else has already filed the bug.


Contributing
------------

Are you a developer? Do you want to integrate with Review Board, or work on
Review Board itself? Great! Let's help you get started.

First off, we have a few handy guides:

* `Web API Guide`_
* `Extending Review Board`_
* `Contributor Guide`_

We accept patches to Review Board, RBTools, and other related projects on
`reviews.reviewboard.org <https://reviews.reviewboard.org/>`_. (Please note
that we do not accept pull requests.)

Got any questions about anything related to Review Board and development? Head
on over to our `development discussion list`_.

.. _`Web API Guide`: https://www.reviewboard.org/docs/manual/latest/webapi/
.. _`Extending Review Board`:
   https://www.reviewboard.org/docs/manual/latest/webapi
.. _`Contributor Guide`: https://www.reviewboard.org/docs/codebase/dev/
.. _`development discussion list`:
   https://groups.google.com/group/reviewboard-dev/


Related Projects
----------------

* Djblets_ -
  Our pack of Django utilities for datagrids, API, extensions, and more. Used
  by Review Board.
* RBTools_ -
  The RBTools command line suite.
* ReviewBot_ -
  Pluggable, automated code review for Review Board.
* rb-gateway_ -
  Manages Git repositories, providing a full API enabling all of Review Board's
  feaures.

.. _Djblets: https://github.com/djblets/djblets/
.. _RBTools: https://github.com/reviewboard/rbtools/
.. _ReviewBot: https://github.com/reviewboard/ReviewBot/
.. _rb-gateway: https://github.com/reviewboard/rb-gateway/
