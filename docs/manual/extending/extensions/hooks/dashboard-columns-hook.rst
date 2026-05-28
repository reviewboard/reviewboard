.. _dashboard-columns-hook:

====================
DashboardColumnsHook
====================

:py:class:`reviewboard.extensions.hooks.DashboardColumnsHook` registers new
columns for the dashboard. Users can then choose to show them, reorder them,
and sort by them, just like the built-in columns.

For a complete guide to writing dashboard columns, see
:ref:`extension-dashboard-columns`.

.. seealso::

   If you need to add columns to any other datagrid, such as the
   :guilabel:`Users` page, use :ref:`datagrid-columns-hook` instead.


Example
=======

.. code-block:: python

    from django.utils.html import format_html
    from django.utils.safestring import SafeString, mark_safe
    from djblets.datagrid.grids import Column, StatefulColumn
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import DashboardColumnsHook
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


    class SampleExtension(Extension):
        def initialize(self) -> None:
            DashboardColumnsHook(self, [
                MilestoneColumn(id='myvendor_milestone'),
            ])
