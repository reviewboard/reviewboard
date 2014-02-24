=========
Dashboard
=========

Overview
========

The dashboard is your primary method of accessing review requests. It
displays detailed information on review requests at a glance, and allows
filtering review requests.

After logging in to Review Board, you'll be taken to your dashboard. You can
always get back to it by clicking :guilabel:`Dashboard` on the navigation
banner near the top of the page.


Navigation Sidebar
==================

The dashboard provides a navigation sidebar with the following items:

* :guilabel:`Outgoing`

  * :guilabel:`All`
  * :guilabel:`Open`

* :guilabel:`Incoming`

  * :guilabel:`Open`
  * :guilabel:`To Me`
  * :guilabel:`Starred`

It also lists each group you belong to, and each group you're watching.
Each item also lists the number of review requests in that view.
You can click on an item to be taken to that view of the dashboard.


Outgoing: All
-------------

This view shows every review request you have created, including those that
are discarded or submitted. It works like the :ref:`outgoing-open` but with
your complete history.


.. _outgoing-open:

Outgoing: Open
--------------

This view shows all review requests that you have filed that are open or are
still drafts.


Incoming: Open
--------------

This is the default view. This view shows all review requests that have been
either directly assigned to you or indirectly through a group you belong to.

This can be filtered down by selecting :guilabel:`To Me` or one of the
group names under :guilabel:`Incoming Reviews`.


Incoming: To Me
---------------

This view shows all review requests that have been directly assigned to you.


Incoming: Starred
-----------------

This view shows every review request that you have starred. This is useful for
keeping track of review requests you are interested in that were not directly
assigned to you.


Review Requests List
====================

The main area of the dashboard lists the review requests belonging to that
particular view. This is a detailed, sortable, customizable list.

Clicking on any review request in the list will take you to that particular
review request, while clicking on a submitter's name will take you to the
list of review requests submitted by that user.


Sorting
=======

The review request list can be sorted by clicking on a column header. Clicking
once will sort the column in ascending order, and clicking a second time will
sort that column in descending order. The column will have a little up or
down arrow indicating the sorting order. You can click the :guilabel:`X` next
to clear sorting for that column.

The dashboard provides two-level sorting. You can primarilty sort by one
column but in the case of multiple entries for a particular submitter,
timestamp, etc., you can have secondary sorting on another column. This is set
by simply clicking one column (which will be the secondary column) and then
clicking another column (which will be the primary).

The primary column is indicated by a black up/down arrow, and the secondary
column is indicated by a lighter grey up/down arrow.

Sorting options are saved across sessions.


Reordering Columns
==================

Columns in the dashboard can be reordered by clicking and dragging the column.
The columns will reorder as you're dragging to show you the new layout, and
when you release the mouse cursor the order will be saved.


Customizable Columns
====================

.. image:: dashboard-columns.png

Different users have different things they want to see in the dashboard. You
can change which columns are shown and which aren't by clicking the
pencil icon to the right of the columns. A pop-up menu will appear
showing which columns are shown and which aren't.

The following are available columns you can choose from:


Branch
------

Shows the branch information listed on the review request.


Bugs
----

Shows the bug IDs listed on the review request.


Diff Size
---------

Shows a count of the removed and added lines of code in the latest revision of
the diff.


Diff Updated
------------

Shows the timestamp of the last diff update. This is color-coded to indicate
the age.


Diff Updated (Relative)
-----------------------

Shows the timestamp of the last diff update, relative to now. This is
color-coded to indicate the age.


Last Updated
------------

Shows the timestamp of the last update to the review request. This is
color-coded to indicate the age.


Last Updated (Relative)
-----------------------

Shows the timestamp of the last update to the review request, relative to now.
This is color-coded to indicate the age.


My Comments
-----------

Shows a green comment flag if you have any unpublished comments on the review
request, or a blue comment flag if you have published comments. This allows
you to quickly see which review requests you've addressed.


New Updates
-----------

Shows a message bubble icon for any review requests that have been updated or
have had discussion since you've last seen it. This does not apply to review
requests you haven't yet looked at.


Number of Reviews
-----------------

Shows how many reviews have been made on the review request.


Posted Time
-----------

Shows the timestamp when the review request was first posted. This is
color-coded to indicate the age.


Posted Time (Relative)
----------------------

Shows the timestamp when the review request was first posted, relative to now.
This is color-coded to indicate the age.


Repository
----------

Shows the repository that the review request is against.


Review Request ID
-----------------

Shows the ID number of the review request.


Select Rows
-----------

Shows a checkbox that allows you to select the row. When one or more review
requests are selected, the sidebar will contain commands to close the selected
review requests.


Ship It!
--------

If there are open issues, this shows a count of the open issues in a yellow
bubble. If there are no open issues, this will show a count of reviews where
someone has marked "Ship It!"


Starred
-------

Shows a star indicator that can be toggled. When toggled on, the review
request is starred, meaning you'll be CC'd on any discussion. Toggling it off
will remove you from the CC list.


Submitter
---------

Shows the username of the submitter.


Summary
-------

Shows the summary text of the review request.


Target Groups
-------------

Shows a list of the assigned groups for each review request.


Target People
-------------

Shows a list of the assigned people for each review request.


To Me
-----

Shows a chevron for review requests which directly list you in the "people"
field.
