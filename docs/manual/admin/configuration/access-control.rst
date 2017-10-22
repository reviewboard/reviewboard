.. _access-control:

==============
Access Control
==============

Review Board can limit who can view certain review requests, access
repositories, and join groups. This can be useful in large organizations
or companies where not everyone has access to every project.


.. _invite-only-review-groups:

Invite-only Review Groups
=========================

:ref:`review-groups` can be made to be invite-only. An invite-only group
cannot be joined directly. It requires a Review Board administrator to
add users.

If a review request lists an invite-only group as a reviewer, and doesn't
list any public groups, then it'll be inaccessible to anyone not on the
invite-only groups, unless they're listed explicitly on the reviewer lists.

To set a group to be invite-only, toggle the
:ref:`Invite only <review-group-invite-only>` setting and then add the
users who need access to the group.


.. _hidden-review-groups:

Hidden Review Groups
====================

Groups can be marked invisible. This can work in conjunction with
invite-only groups, and can also be used for groups that are no longer
in operation.

Marking a group as invisible doesn't change who can use it or how it affects
access, but it does hide it from all lists of groups.


.. _private-repositories:

Private Repositories
====================

Repositories can be made to be accessible only to certain users or review
groups, keeping everyone else out. Inaccessible repositories completely
prevent access not only to the files contained within the repository, but
to all review requests on that repository.

A review request on a private repository can only be viewed by users who
are specifically on the reviewer list, who are on the repository's user access
list, or who are on a group that's on the repository's group access list.

To make a repository private, toggle the
:ref:`Publicly accessible <repository-publicly-accessible>` checkbox off.
You will need to add one or more users or invite-only groups to the access
control lists in order for anyone to have access.


Review Request Access Summary
=============================

To summarize, a user has access to a review request only if all the following
conditions are met:

* The review request is public, or the user can modify it (either by being
  the submitter or having special administrative permissions).

* The repository is public or the user has access to to it (either by
  being explicitly on the user access list, or by being a member of a group
  on that list).

* The user is listed as a requested reviewer on the review request, or the
  user has access to one or more groups listed as requested reviewers
  (either by being a member of an invite-only group, or by the group being
  public).
