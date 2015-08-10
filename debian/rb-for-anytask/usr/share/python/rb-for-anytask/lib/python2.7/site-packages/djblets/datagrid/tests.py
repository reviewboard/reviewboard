#
# tests.py -- Unit tests for classes in djblets.datagrid
#
# Copyright (c) 2007-2008  Christian Hammond
# Copyright (c) 2007-2008  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import FieldError
from django.http import HttpRequest
from django.test.client import RequestFactory
from kgb import SpyAgency

from djblets.datagrid.grids import (Column, DataGrid, DateTimeSinceColumn,
                                    StatefulColumn)
from djblets.testing.testcases import TestCase
from djblets.util.dates import get_tz_aware_utcnow


def populate_groups():
    for i in range(1, 100):
        group = Group(name="Group %02d" % i)
        group.save()


class GroupDataGrid(DataGrid):
    objid = Column("ID", link=True, sortable=True, field_name="id")
    name = Column("Group Name", link=True, sortable=True, expand=True)

    def __init__(self, request):
        DataGrid.__init__(self, request, Group.objects.all(), "All Groups")
        self.default_sort = []
        self.default_columns = ['objid', 'name']


class ColumnsTest(TestCase):
    def testDateTimeSinceColumn(self):
        """Testing DateTimeSinceColumn"""
        class DummyObj:
            time = None

        column = DateTimeSinceColumn("Test", field_name='time')
        state = StatefulColumn(None, column)

        if settings.USE_TZ:
            now = get_tz_aware_utcnow()
        else:
            now = datetime.now()

        obj = DummyObj()
        obj.time = now
        self.assertEqual(column.render_data(state, obj), "0\xa0minutes ago")

        obj.time = now - timedelta(days=5)
        self.assertEqual(column.render_data(state, obj), "5\xa0days ago")

        obj.time = now - timedelta(days=7)
        self.assertEqual(column.render_data(state, obj), "1\xa0week ago")


class DataGridTest(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, "AUTH_PROFILE_MODULE",
                                               None)
        settings.AUTH_PROFILE_MODULE = None
        populate_groups()
        self.user = User(username="testuser")
        self.request = HttpRequest()
        self.request.user = self.user
        self.datagrid = GroupDataGrid(self.request)

    def tearDown(self):
        settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def testRender(self):
        """Testing basic datagrid rendering"""
        self.datagrid.render_listview()

    def testRenderToResponse(self):
        """Testing rendering datagrid to HTTPResponse"""
        self.datagrid.render_listview_to_response()

    def testSortAscending(self):
        """Testing datagrids with ascending sort"""
        self.request.GET['sort'] = "name,objid"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["name", "objid"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 01")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 02")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 03")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()

    def testSortDescending(self):
        """Testing datagrids with descending sort"""
        self.request.GET['sort'] = "-name"
        self.datagrid.load_state()

        self.assertEqual(self.datagrid.sort_list, ["-name"])
        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(self.datagrid.rows[0]['object'].name, "Group 99")
        self.assertEqual(self.datagrid.rows[1]['object'].name, "Group 98")
        self.assertEqual(self.datagrid.rows[2]['object'].name, "Group 97")

        # Exercise the code paths when rendering
        self.datagrid.render_listview()

    def testCustomColumns(self):
        """Testing datagrids with custom column orders"""
        self.request.GET['columns'] = "objid"
        self.datagrid.load_state()

        self.assertEqual(len(self.datagrid.rows), self.datagrid.paginate_by)
        self.assertEqual(len(self.datagrid.rows[0]['cells']), 1)

        # Exercise the code paths when rendering
        self.datagrid.render_listview()


class SandboxColumn(Column):
    def setup_state(self, state):
        raise Exception

    def get_sort_field(self, state):
        raise Exception

    def render_data(self, state, obj):
        raise Exception

    def augment_queryset(self, state, queryset):
        raise Exception


class SandboxTests(SpyAgency, TestCase):
    """Testing extension sandboxing."""
    def setUp(self):
        super(SandboxTests, self).setUp()

        self.column = SandboxColumn(id='test')
        DataGrid.add_column(self.column)

        self.factory = RequestFactory()
        self.request = self.factory.get('test', {'columns': 'objid'})
        self.request.user = User(username='reviewboard', email='',
                                 password='password')
        self.datagrid = DataGrid(request=self.request,
                                 queryset=Group.objects.all())

    def tearDown(self):
        super(SandboxTests, self).tearDown()

        DataGrid.remove_column(self.column)

    def test_setup_state_columns(self):
        """Testing DataGrid column sandboxing for setup_state"""
        self.spy_on(SandboxColumn.setup_state)

        self.datagrid.get_stateful_column(column=self.column)
        self.assertTrue(SandboxColumn.setup_state.called)

    def test_get_sort_field_columns(self):
        """Testing DataGrid column sandboxing for get_sort_field"""
        self.datagrid.sort_list = ['test']
        self.datagrid.default_columns = ['objid', 'test']

        self.spy_on(SandboxColumn.get_sort_field)

        self.assertRaisesMessage(
            FieldError,
            "Invalid order_by arguments: [u'']",
            lambda: self.datagrid.precompute_objects())
        self.assertTrue(SandboxColumn.get_sort_field.called)

    def test_render_data_columns(self):
        """Testing DataGrid column sandboxing for render_data"""
        stateful_column = self.datagrid.get_stateful_column(column=self.column)

        self.spy_on(SandboxColumn.render_data)

        super(SandboxColumn, self.column).render_cell(state=stateful_column,
                                                      obj=None,
                                                      render_context=None)
        self.assertTrue(SandboxColumn.render_data.called)

    def test_augment_queryset_columns(self):
        """Testing DataGrid column sandboxing for augment_queryset"""
        stateful_column = self.datagrid.get_stateful_column(column=self.column)
        self.datagrid.columns.append(stateful_column)

        self.spy_on(SandboxColumn.augment_queryset)

        self.datagrid.post_process_queryset(queryset=[])
        self.assertTrue(SandboxColumn.augment_queryset.called)
