.. _extension-dashboard-columns:

=================================
Customizing the Dashboard Columns
=================================

The Review Board :ref:`dashboard <dashboard>` displays review requests that
you have out for review or that need your attention. It's customizable,
allowing users to choose the columns they want to see in the order they want
to see them.

Extensions can add their own columns to the dashboard. Users can then choose
to include them, reorder them, and sort by them, just like the built-in
columns.

There are three key things to know:

1. **Columns are defined** by subclassing
   :py:class:`~djblets.datagrid.grids.Column` and setting attributes that
   control what is shown and how.

2. **Columns render data** by overriding
   :py:meth:`~djblets.datagrid.grids.Column.render_data`, which returns HTML
   to show for the cell.

3. **Columns are registered** by passing instances to
   :py:class:`~reviewboard.extensions.hooks.DashboardColumnsHook`.


Creating a Column
=================

To create a column, subclass :py:class:`~djblets.datagrid.grids.Column` and
set the attributes that describe it:

.. code-block:: python

   from django.utils.html import format_html
   from django.utils.safestring import SafeString, mark_safe
   from djblets.datagrid.grids import Column, StatefulColumn
   from reviewboard.reviews.models import ReviewRequest


   class MilestoneColumn(Column):
       label = 'Milestone'
       detailed_label = 'Project milestone'
       shrink = True

       def render_data(
           self,
           state: StatefulColumn,
           obj: ReviewRequest,
       ) -> SafeString:
           milestone = obj.extra_data.get('myvendor_milestone', '')

           if milestone:
               return format_html(
                   '<span class="myvendor-milestone">{}</span>',
                   milestone)

           return mark_safe('')

This defines a column that shows in the column-picker as
:guilabel:`Milestone`, and then renders some content set by either the
extension or an API request.

There are several attributes you can set on the column that control how
the column is displayed or how data is fetched:

*
    :py:attr:`~djblets.datagrid.grids.Column.label`:
    The short label shown in the column header.

*
    :py:attr:`~djblets.datagrid.grids.Column.detailed_label`:
    A longer label shown in the columns menu, where users can add or remove
    columns.

    This defaults to :py:attr:`~djblets.datagrid.grids.Column.label` if not
    set.

*
    :py:attr:`~djblets.datagrid.grids.Column.field_name`:
    The name of the attribute on the object being displayed in the row.

    You'll only need to set this if you're operating off of a built-in field
    on the :py:class:`~reviewboard.reviews.models.ReviewRequest` model and
    want to use the built-in rendering of the field.

*
    :py:attr:`~djblets.datagrid.grids.Column.sortable`:
    Whether users can sort the table by this column.

    This defaults to ``False``. In most cases, your column may be operating
    off of dynamic data or data set by your extension in
    :py:attr:`ReviewRequest.extra_data
    <reviewboard.reviews.models.ReviewRequest.extra_data>`, which can't be
    sorted.

*
    :py:attr:`~djblets.datagrid.grids.Column.db_field`:
    The database field used for sorting, if you want your column to sort.

    This supports relations using ``__``, such as ``repository__name``.

    You must provide this if setting
    :py:attr:`~djblets.datagrid.grids.Column.sortable` to ``True``.

*
    :py:attr:`~djblets.datagrid.grids.Column.shrink`:
    If ``True``, the column takes only the minimum width needed for its
    content.

    This defaults to ``False``, allowing it to more equally share space
    with other columns.

*
    :py:attr:`~djblets.datagrid.grids.Column.expand`:
    If ``True``, the column expands to fill any remaining horizontal space.

    This defaults to ``False``, allowing it to more equally share space
    with other columns.

*
    :py:attr:`~djblets.datagrid.grids.Column.css_class`:
    A CSS class (or a callable returning one) for adding custom styling to
    the table cell.

    Normally, you'll just want to apply styling within your rendered HTML,
    but this can be used if you want to style the full cells (background and
    border) like the :guilabel:`Last Updated` column does.


Rendering Column Data
---------------------

By default, a column renders the raw value of
:py:attr:`~djblets.datagrid.grids.Column.field_name` as plain text. In most
cases, though, you'll be working off of :py:attr:`ReviewRequest.extra_data
<reviewboard.reviews.models.ReviewRequest.extra_data>` or some function
defined by your extension, and will need to render the data yourself.

To render data yourself, override
:py:meth:`~djblets.datagrid.grids.Column.render_data`.

We saw an example above, but let's look at it again:

.. code-block:: python

   from django.utils.html import format_html
   from django.utils.safestring import SafeString, mark_safe
   from djblets.datagrid.grids import Column, StatefulColumn
   from reviewboard.reviews.models import ReviewRequest


   class MilestoneColumn(Column):
       label = 'Milestone'
       shrink = True

       def render_data(
           self,
           state: StatefulColumn,
           obj: ReviewRequest,
       ) -> SafeString:
           milestone = obj.extra_data.get('myvendor_milestone', '')

           if milestone:
               return format_html(
                   '<span class="myvendor-milestone">{}</span>',
                   milestone)

           return mark_safe('')

Here, ``obj`` is the review request being rendered in the current row.
``state`` carries a per-column rendering context, which can be used to get
the parent datagrid (via ``state.datagrid``) or the HTTP request (via
``state.datagrid.request``).

This function must *always* return safe HTML (HTML that has already been
formatted to carefully consider user input).

Always use :py:func:`~django.utils.html.format_html` to build HTML with
user-provided values, :py:func:`~django.utils.html.escape` to convert plain
text to HTML, or render using a :ref:`Django template <django:templates>`.
If the content is already from a trusted source, you can mark it safe using
:py:func:`~django.utils.safestring.mark_safe`.


Augmenting the Queryset
-----------------------

If your column needs data from a related model (such as one provided by
your extension), you can augment the queryset to include it as part of the
dashboard's query.

To augment the queryset, override
:py:meth:`~djblets.datagrid.grids.Column.augment_queryset_for_data`.

This runs once when the datagrid fetches its rows in preparation for display.
By making your query part of the initial query, you avoid accidentally
triggering a database query per-row (which will slow down your server).

For example:

.. code-block:: python

   from django.db.models import QuerySet
   from django.http import HttpRequest
   from django.utils.html import escape
   from django.utils.safestring import SafeString, mark_safe
   from djblets.datagrid.grids import Column, StatefulColumn
   from reviewboard.reviews.models import ReviewRequest


   class RepositoryColumn(Column):
       label = 'Repository'
       shrink = True

       def augment_queryset_for_data(
           self,
           state: StatefulColumn,
           queryset: QuerySet,
           *,
           request: HttpRequest,
           **kwargs,
       ) -> QuerySet:
           return queryset.select_related('repository')

       def render_data(
           self,
           state: StatefulColumn,
           obj: ReviewRequest,
       ) -> SafeString:
           if obj.repository_id is None:
               return mark_safe('')

           return escape(obj.repository.name)

You can use methods like
:py:meth:`~django.db.models.query.QuerySet.annotate()`,
:py:meth:`~django.db.models.query.QuerySet.prefetch_related()`, or
:py:meth:`~django.db.models.query.QuerySet.select_related()` to build
augmented querysets.


Making Columns Sortable
-----------------------

If your column is based on a field in the database (rather than dynamic
data or something stored in :py:attr:`ReviewRequest.extra_data
<reviewboard.reviews.models.ReviewRequest.extra_data>`), you can make it
sortable.

To do this:

1. Set :py:attr:`~djblets.datagrid.grids.Column.sortable` to ``True``.
2. Set :py:attr:`~djblets.datagrid.grids.Column.db_field` to the field (or
   a ``__``-delimited relation) to sort by:

.. code-block:: python

   class RepositoryColumn(Column):
       label = 'Repository'
       db_field = 'repository__name'
       sortable = True
       shrink = True

Users can then click the column header to sort the dashboard by that field
in either ascending or descending order.


Linking to a Page
-----------------

Your column can easily link its data to another page, helping take users to
another page inside or outside of Review Board.

To make the column's content a link:

1. Set :py:attr:`~djblets.datagrid.grids.Column.link` to ``True``.

2. Define a :py:attr:`djblets.datagrid.grids.Column.link_func` on your
   object (this must be a :py:func:`@staticmethod <staticmethod>`).

For example:

.. code-block:: python

   from django.utils.safestring import SafeString
   from djblets.datagrid.grids import Column, StatefulColumn
   from reviewboard.reviews.models import ReviewRequest


   class RepositoryColumn(Column):
       label = 'Repository'
       db_field = 'repository__name'
       link = True
       sortable = True
       shrink = True

       @staticmethod
       def link_func(
           state: StatefulColumn,
           obj: ReviewRequest,
           rendered_data: SafeString,
       ) -> str:
           if obj.repository_id is not None:
               return obj.repository.get_absolute_url()

           return ''

       # NOTE: Include augment_queryset_for_data() and render_data() from
       #       above.
       #
       #       Without augment_queryset_for_data(), our link_func() will
       #       fetch a repository per-row, which would be expensive.

This largely takes the same values used when rendering, with the addition
of the HTML that's going to be rendered into the cell.


Registering a Column
====================

In order for your column to be available for users to add to their dashboard,
you will need to register it. This is done by passing one or more column
instances to a :ref:`dashboard-columns-hook`:

.. code-block:: python

   from reviewboard.extensions.hooks import DashboardColumnsHook


   class MyExtension(Extension):
       def initialize(self) -> None:
           DashboardColumnsHook(self, [
               MilestoneColumn(id='myvendor_milestone'),
           ])

You must include the unique ``id`` you want assigned for the column. This
will identify your column and allow it to be chosen and saved in the users'
settings.

.. tip::

   Use a vendor prefix (such as your extension's package name) to avoid
   conflicts with Review Board's built-in columns or other extensions.


Working with Other Datagrids
============================

This guide covered the Dashboard, which is what most users will use every
day.

You can also register columns into other datagrids:

* All Review Requests
* Users
* Groups

You'll define your columns in much the same way, but you may be working with
other types of objects (:py:class:`~django.contrib.auth.models.User` for the
Users datagrid, or :py:class:`~reviewboard.reviews.models.Group` for the
Groups datagrid).

To register columns into these other datagrids, you'll use
:ref:`DataGridColumnsHook <datagrid-columns-hook>`, passing in the right
datagrid class for the right page. For example:

.. code-block:: python

   from reviewboard.extensions.hooks import DataGridColumnsHook
   from reviewboard.datagrids.grids import (ReviewRequestDataGrid,
                                            GroupDataGrid,
                                            UsersDataGrid)


   class MyExtension(Extension):
       def initialize(self) -> None:
           # For the All Review Requests page:
           DataGridColumnsHook(self, ReviewRequestDataGrid, [
               MilestoneColumn(id='myvendor_milestone'),
           ])

           # For the Users page:
           DataGridColumnsHook(self, UsersDataGrid, [
               TeamColumn(id='myvendor_team'),
           ])

           # For the Groups page:
           DataGridColumnsHook(self, GroupDataGrid, [
               DepartmentColumn(id='myvendor_department'),
           ])
