.. _datagrid-columns-hook:

===================
DataGridColumnsHook
===================

:py:class:`reviewboard.extensions.hooks.DataGridColumnsHook` registers new
columns for any datagrid, such as the :guilabel:`All Review Requests`,
:guilabel:`Users`, or :guilabel:`Groups` pages.

For a complete guide to writing columns, see
:ref:`extension-dashboard-columns`.

.. seealso::

   If you need to add columns to the Dashboard, use
   :ref:`dashboard-columns-hook` instead.


Example
=======

.. code-block:: python

    from django.contrib.auth.models import User
    from django.utils.html import escape
    from django.utils.safestring import SafeString, mark_safe
    from djblets.datagrid.grids import Column, StatefulColumn
    from reviewboard.datagrids.grids import UsersDataGrid
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import DataGridColumnsHook


    class TeamColumn(Column):
        label = 'Team'
        shrink = True

        def render_data(
            self,
            state: StatefulColumn,
            obj: User,
        ) -> SafeString:
            profile = obj.get_profile()

            if 'myvendor_team' in profile.extra_data:
                return escape(profile.extra_data['myvendor_team'])

            return mark_safe('')


    class SampleExtension(Extension):
        def initialize(self) -> None:
            DataGridColumnsHook(self, UsersDataGrid, [
                TeamColumn(id='myvendor_team'),
            ])
