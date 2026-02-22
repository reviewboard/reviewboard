.. _dashboard-columns-hook:

====================
DashboardColumnsHook
====================

:py:class:`reviewboard.extensions.hooks.DashboardColumnsHook` allows
extensions to register new columns for the dashboard. Users can add these
columns to their dashboard, move them around, and sort them. They behave just
like the default columns.

Dashboard columns can simply reflect information from the database, or
provide any sort of custom rendering needed.

A caller simply instantiates :py:class:`DashboardColumnsHook`, passing a list
of :py:class:`djblets.datagrid.grids.Column` instances. Each instance must
have an :py:attr:`id` attribute set to a value that's unique.

Custom columns can also be created by subclassing
:py:class:`djblets.datagrid.grids.Column`.

Note that this is a specialization of
:py:class:`reviewboard.extensions.hooks.DataGridColumnsHook`. If you need to
add to any other datagrid, such as the one on the All Review Requests page,
then you should use :ref:`datagrid-columns-hook` instead.


Example
=======

.. code-block:: python

    from django.utils.html import escape
    from djblets.datagrid.grids import Column
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import DashboardColumnsHook


    class MilestoneColumn(Column):
        def render_data(self, review_request):
            if 'myvendor_milestone' in review_request.extra_data:
                return (
                    '<span class="myvendor-milestone">%s</span>'
                    % escape(review_request.extra_data['myvendor_milestone'])
                )

            return ''


    class SampleExtension(Extension):
        def initialize(self):
            DashboardColumnsHook(self, [
                MilestoneColumn(id='myvendor_milestone',
                                label='Milestone'),
            ])
