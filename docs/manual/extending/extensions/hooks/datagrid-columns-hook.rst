.. _datagrid-columns-hook:

===================
DataGridColumnsHook
===================

:py:class:`reviewboard.extensions.hooks.DataGridColumnsHook` allows
extensions to register new columns for any datagrid, such as the ones
used on the All Review Request or Groups pages. Users can add these columns
to their dashboard, move them around, and sort them. They behave just like the
default columns.

Columns can simply reflect information from the database, or provide any sort
of custom rendering needed.

A caller simply instantiates :py:class:`DataGridColumnsHook`, passing the
:py:class:`djblets.datagrid.grids.DataGrid` subclass, plus a list of
:py:class:`djblets.datagrid.grids.Column` instances. Each instance must have
an :py:attr:`id` attribute set to a value that's unique to that datagrid.

Custom columns can also be created by subclassing
:py:class:`djblets.datagrid.grids.Column`.

If you want to add to the dashboard specifically, you can use
:ref:`dashboard-columns-hook`. Columns added using that hook will appear
only on the dashboard's datagrid.


Example
=======

.. code-block:: python

    from django.utils.html import escape
    from djblets.datagrid.grids import Column
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import DataGridColumnsHook
    from reviewboard.datagrids.grids import UsersDataGrid


    class TeamColumn(Column):
        def render_data(self, user):
            profile = user.get_profile()

            if 'myvendor_team' in profile.extra_data:
                return escape(profile.extra_data['myvendor_team'])

            return ''


    class SampleExtension(Extension):
        def initialize(self):
            DataGridColumnsHook(self, UsersDataGrid, [
                TeamColumn(id='myvendor_teams',
                           label='Team'),
            ])
