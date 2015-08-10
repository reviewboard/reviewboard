#
# grids.py -- Basic definitions for datagrids
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
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
#

from __future__ import unicode_literals

import logging
import re
import string
import traceback

import pytz
from django.conf import settings
from django.contrib.auth.models import SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import InvalidPage, QuerySetPaginator
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext, Context
from django.template.defaultfilters import date, timesince
from django.template.loader import render_to_string, get_template
from django.utils import six
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.util.http import get_url_params_except


# Registration of all datagrid classes to columns.
_column_registry = {}


class Column(object):
    """A column in a data grid.

    The column is the primary component of the data grid. It is used to
    display not only the column header but the HTML for the cell as well.

    Columns can be tied to database fields and can be used for sorting.
    Not all columns have to allow for this, though.

    Columns can have an image, text, or both in the column header. The
    contents of the cells can be instructed to link to the object on the
    row or the data in the cell.

    If a Column defines an image_class, then it will be assumed that the
    class represents an icon, perhaps as part of a spritesheet, and will
    display it in a <div>. An image_url cannot also be defined.
    """
    SORT_DESCENDING = 0
    SORT_ASCENDING = 1

    def __init__(self, label=None, id=None, detailed_label=None,
                 detailed_label_html=None, field_name=None, db_field=None,
                 image_url=None, image_class=None, image_width=None,
                 image_height=None, image_alt="", shrink=False, expand=False,
                 sortable=False,
                 default_sort_dir=SORT_DESCENDING, link=False,
                 link_func=None, cell_clickable=False, css_class=""):
        assert not (image_class and image_url)

        self.id = id
        self.field_name = field_name
        self.db_field = db_field or field_name
        self.label = label
        self.detailed_label = detailed_label or self.label
        self.detailed_label_html = detailed_label_html or self.detailed_label
        self.image_url = image_url
        self.image_class = image_class
        self.image_width = image_width
        self.image_height = image_height
        self.image_alt = image_alt
        self.shrink = shrink
        self.expand = expand
        self.sortable = sortable
        self.default_sort_dir = default_sort_dir
        self.cell_clickable = False
        self.link = link
        self.link_func = (
            link_func or
            (lambda state, x, y: state.datagrid.link_to_object(state, x, y)))
        self.css_class = css_class

    def setup_state(self, state):
        """Sets up any state that may be needed for the column.

        This is called once per column per datagrid instance.

        By default, no additional state is set up. Subclasses can override
        this to set any variables they may need.
        """
        pass

    def get_sort_field(self, state):
        """Returns the field used for sorting this column.

        By default, this uses the provided db_field.
        """
        return self.db_field

    def get_toggle_url(self, state):
        """
        Returns the URL of the current page with this column's visibility
        toggled.
        """
        columns = [column.id for column in state.datagrid.columns]

        if state.active:
            try:
                columns.remove(self.id)
            except ValueError:
                pass
        else:
            columns.append(self.id)

        url_params = get_url_params_except(state.datagrid.request.GET,
                                           'columns')
        if url_params:
            url_params = url_params + '&'

        return "?%scolumns=%s" % (url_params, ",".join(columns))

    def get_header(self, state):
        """
        Displays a sortable column header.

        The column header will include the current sort indicator, if it
        belongs in the sort list. It will also be made clickable in order
        to modify the sort order appropriately, if sortable.
        """
        datagrid = state.datagrid
        in_sort = False
        sort_direction = self.SORT_DESCENDING
        sort_primary = False
        sort_url = ""
        unsort_url = ""

        if self.sortable:
            sort_list = list(datagrid.sort_list)

            if sort_list:
                rev_column_id = "-%s" % self.id
                new_column_id = self.id
                cur_column_id = ""

                if self.id in sort_list:
                    # This column is currently being sorted in
                    # ascending order.
                    sort_direction = self.SORT_ASCENDING
                    cur_column_id = self.id
                    new_column_id = rev_column_id
                elif rev_column_id in sort_list:
                    # This column is currently being sorted in
                    # descending order.
                    sort_direction = self.SORT_DESCENDING
                    cur_column_id = rev_column_id
                    new_column_id = self.id

                if cur_column_id:
                    in_sort = True
                    sort_primary = (sort_list[0] == cur_column_id)

                    if not sort_primary:
                        # If this is not the primary column, we want to keep
                        # the sort order intact.
                        new_column_id = cur_column_id

                    # Remove this column from the current location in the list
                    # so we can move it to the front of the list.
                    sort_list.remove(cur_column_id)

                # Insert the column name into the beginning of the sort list.
                sort_list.insert(0, new_column_id)
            else:
                # There's no sort list to begin with. Make this column
                # the only entry.
                sort_list = [self.id]

            # We can only support two entries in the sort list, so truncate
            # this.
            del(sort_list[2:])

            url_params = get_url_params_except(
                datagrid.request.GET,
                "sort", "datagrid-id", "gridonly", "columns")
            if url_params:
                url_params = url_params + '&'

            url_prefix = "?%ssort=" % url_params
            unsort_url = url_prefix + ','.join(sort_list[1:])
            sort_url = url_prefix + ','.join(sort_list)

        ctx = Context({
            'column': self,
            'column_state': state,
            'in_sort': in_sort,
            'sort_ascending': sort_direction == self.SORT_ASCENDING,
            'sort_primary': sort_primary,
            'sort_url': sort_url,
            'unsort_url': unsort_url,
        })

        return mark_safe(datagrid.column_header_template_obj.render(ctx))

    def collect_objects(self, state, object_list):
        """Iterates through the objects and builds a cache of data to display.

        This optimizes the fetching of data in the grid by grabbing all the
        IDs of related objects that will be queried for rendering, loading
        them all at once, and populating the cache.
        """
        id_field = '%s_id' % self.field_name
        ids = set()
        model = None

        for obj in object_list:
            if not hasattr(obj, id_field):
                # This isn't the field type you're looking for.
                return

            ids.add(getattr(obj, id_field))

            if not model:
                field = getattr(obj.__class__, self.field_name).field

                try:
                    model = field.rel.to
                except AttributeError:
                    # No idea what this is. Bail.
                    return

        if model:
            for obj in model.objects.filter(pk__in=ids):
                state.data_cache[obj.pk] = obj

    def render_cell(self, state, obj, render_context):
        """Renders the table cell containing column data."""
        datagrid = state.datagrid

        try:
            rendered_data = self.render_data(state, obj)
        except Exception as e:
            logging.error('Error when calling render_data for DataGrid Column'
                          ' %r: %s',
                          self, e, exc_info=1)
            rendered_data = None

        url = ''
        css_class = ''

        if self.link:
            try:
                url = self.link_func(state, obj, rendered_data)
            except AttributeError:
                pass

        if self.css_class:
            if six.callable(self.css_class):
                css_class = self.css_class(obj)
            else:
                css_class = self.css_class

        key = "%s:%s:%s:%s" % (state.last, rendered_data, url, css_class)

        if key not in state.cell_render_cache:
            ctx = Context(render_context)
            ctx.update({
                'column': self,
                'column_state': state,
                'css_class': css_class,
                'url': url,
                'data': mark_safe(rendered_data)
            })

            state.cell_render_cache[key] = \
                mark_safe(datagrid.cell_template_obj.render(ctx))

        return state.cell_render_cache[key]

    def render_data(self, state, obj):
        """Renders the column data to a string. This may contain HTML."""
        id_field = '%s_id' % self.field_name

        # Look for this directly so that we don't end up fetching the
        # data for the object.
        if id_field in obj.__dict__:
            pk = obj.__dict__[id_field]

            if pk in state.data_cache:
                return state.data_cache[pk]
            else:
                value = getattr(obj, self.field_name)
                state.data_cache[pk] = escape(value)
                return value
        else:
            # Follow . separators like in the django template library
            value = obj
            for field_name in self.field_name.split('.'):
                if field_name:
                    value = getattr(value, field_name)

                    if six.callable(value):
                        value = value()

            return escape(value)

    def augment_queryset(self, state, queryset):
        """Augments a queryset with new queries.

        Subclasses can override this to extend the queryset to provide
        additional information, usually using queryset.extra(). This must
        return a queryset based on the original queryset.

        This should not restrict the query in any way, or the datagrid may
        not operate properly. It must only add additional data to the
        queryset.
        """
        return queryset


class StatefulColumn(object):
    """A stateful wrapper for a Column instance.

    Columns must be stateless, as they are shared across all instances of
    a particular DataGrid. However, some state is needed for columns, such
    as their widths or active status.

    StatefulColumn wraps a Column instance and provides state storage,
    and also provides a convenient way to call methods on a Column and pass
    the state.

    Attributes owned by the Column can be accessed directly through the
    StatefulColumn.

    Likewise, any functions owned by the Column can be accessed as well.
    The function will be invoked with this StatefulColumn as the first
    parameter passed.
    """
    def __init__(self, datagrid, column):
        self.datagrid = datagrid
        self.column = column
        self.active = False
        self.last = False
        self.width = 0
        self.data_cache = {}
        self.cell_render_cache = {}

        try:
            column.setup_state(self)
        except Exception as e:
            logging.error('Error when calling setup_state in DataGrid Column '
                          '%r: %s',
                          self.column, e, exc_info=1)

    @property
    def toggle_url(self):
        """Returns the visibility toggle URL of the column.

        This is a convenience used by templates to call Column.get_toggle_url
        with the current state.
        """
        return self.column.get_toggle_url(self)

    @property
    def header(self):
        """Returns the header of the column.

        This is a convenience used by templates to call Column.get_header
        with the current state.
        """
        return self.column.get_header(self)

    def __getattr__(self, name):
        """Returns an attribute from the parent Column.

        This is called when accessing an attribute not found directly on
        StatefulColumn. The attribute will be fetched from the Column
        (if it exists there).

        In the case of accessing a function, a wrapper will be returned
        that will automatically pass this StatefulColumn instance as the
        first parameter.
        """
        result = getattr(self.column, name)

        if callable(result):
            return lambda *args, **kwargs: result(self, *args, **kwargs)

        return result


class CheckboxColumn(Column):
    """A column that renders a checkbox.

    The is_selectable and is_selected functions can be overridden to
    control whether a checkbox is displayed in a row and whether that
    checkbox is initially checked.

    The checkboxes have a data-object-id attribute that contains the ID of
    the object that row represents. This allows the JavaScript code to
    determine which rows have been checked, and operate on that
    accordingly.

    The checkboxes also have a data-checkbox-name attribute that
    contains the value passed in to the checkbox_name parameter of its
    constructor.
    """
    def __init__(self, checkbox_name='select', shrink=True,
                 show_checkbox_header=True,
                 detailed_label=_('Select Rows'),
                 *args, **kwargs):
        super(CheckboxColumn, self).__init__(
            shrink=shrink,
            label=mark_safe(
                '<input class="datagrid-header-checkbox"'
                ' type="checkbox" data-checkbox-name="%s" />'
                % checkbox_name),
            detailed_label=detailed_label,
            detailed_label_html=mark_safe(
                '<input type="checkbox" /> %s'
                % detailed_label),
            *args, **kwargs)

        self.show_checkbox_header = show_checkbox_header
        self.checkbox_name = checkbox_name

    def render_data(self, state, obj):
        if self.is_selectable(state, obj):
            checked = ''

            if self.is_selected(state, obj):
                checked = 'checked="true"'

            return ('<input type="checkbox" data-object-id="%s" '
                    'data-checkbox-name="%s" %s />'
                    % (obj.pk, escape(self.checkbox_name), checked))
        else:
            return ''

    def is_selectable(self, state, obj):
        """Returns whether an object can be selected.

        If this returns False, no checkbox will be rendered for this item.
        """
        return True

    def is_selected(self, state, obj):
        """Returns whether an object has been selected.

        If this returns True, the checkbox will be checked.
        """
        return False


class DateTimeColumn(Column):
    """A column that renders a date or time."""
    def __init__(self, label, format=None, sortable=True,
                 timezone=pytz.utc, *args, **kwargs):
        super(DateTimeColumn, self).__init__(label, sortable=sortable,
                                             *args, **kwargs)
        self.format = format
        self.timezone = timezone

    def render_data(self, state, obj):
        # If the datetime object is tz aware, conver it to local time
        datetime = getattr(obj, self.field_name)
        if settings.USE_TZ:
            datetime = pytz.utc.normalize(datetime).\
                astimezone(self.timezone)

        return date(datetime, self.format)


class DateTimeSinceColumn(Column):
    """A column that renders a date or time relative to now."""
    def __init__(self, label, sortable=True, timezone=pytz.utc,
                 *args, **kwargs):
        super(DateTimeSinceColumn, self).__init__(label, sortable=sortable,
                                                  *args, **kwargs)

    def render_data(self, state, obj):
        return _("%s ago") % timesince(getattr(obj, self.field_name))


class DataGrid(object):
    """
    A representation of a list of objects, sorted and organized by
    columns. The sort order and column lists can be customized. allowing
    users to view this data however they prefer.

    This is meant to be subclassed for specific uses. The subclasses are
    responsible for defining one or more column types. It can also set
    one or more of the following optional variables:

        * 'title':                  The title of the grid.
        * 'profile_sort_field':     The variable name in the user profile
                                    where the sort order can be loaded and
                                    saved.
        * 'profile_columns_field":  The variable name in the user profile
                                    where the columns list can be loaded and
                                    saved.
        * 'paginate_by':            The number of items to show on each page
                                    of the grid. The default is 50.
        * 'paginate_orphans':       If this number of objects or fewer are
                                    on the last page, it will be rolled into
                                    the previous page. The default is 3.
        * 'page':                   The page to display. If this is not
                                    specified, the 'page' variable passed
                                    in the URL will be used, or 1 if that is
                                    not specified.
        * 'listview_template':      The template used to render the list view.
                                    The default is 'datagrid/listview.html'
        * 'column_header_template': The template used to render each column
                                    header. The default is
                                    'datagrid/column_header.html'
        * 'cell_template':          The template used to render a cell of
                                    data. The default is 'datagrid/cell.html'
        * 'optimize_sorts':         Whether or not to optimize queries when
                                    using multiple sorts. This can offer a
                                    speed improvement, but may need to be
                                    turned off for more advanced querysets
                                    (such as when using extra()).
                                    The default is True.
    """
    _columns = None

    @classmethod
    def add_column(cls, column):
        """Adds a new column for this datagrid.

        This can be used to add columns to a DataGrid subclass after
        the subclass has already been defined.

        The column added must have a unique ID already set.
        """
        cls._populate_columns()

        if not column.id:
            raise KeyError(
                'Custom datagrid columns must have a unique id attribute.')

        if column.id in _column_registry[cls]:
            raise KeyError('"%s" is already a registered column for %s'
                           % (column.id, cls.__name__))

        _column_registry[cls][column.id] = column

    @classmethod
    def remove_column(cls, column):
        """Removes a column from this datagrid.

        This can be used to remove columns previously added through
        add_column().
        """
        cls._populate_columns()

        try:
            del _column_registry[cls][column.id]
        except KeyError:
            raise KeyError('"%s" is not a registered column for %s'
                           % (column.id, cls.__name__))

    @classmethod
    def get_column(cls, column_id):
        """Returns the column with the given ID.

        If not found, this will return None.
        """
        cls._populate_columns()

        return _column_registry[cls].get(column_id)

    @classmethod
    def get_columns(cls):
        """Returns the list of registered columns for this datagrid."""
        cls._populate_columns()

        return six.itervalues(_column_registry[cls])

    @classmethod
    def _populate_columns(cls):
        """Populates the default list of columns for the datagrid.

        The default list contains all columns added in the class definition.
        """
        if cls not in _column_registry:
            _column_registry[cls] = {}

            for key in dir(cls):
                column = getattr(cls, key)

                if isinstance(column, Column):
                    column.id = key

                    if not column.field_name:
                        column.field_name = column.id

                    if not column.db_field:
                        column.db_field = column.field_name

                    cls.add_column(column)

    def __init__(self, request, queryset=None, title="", extra_context={},
                 optimize_sorts=True):
        self.request = request
        self.queryset = queryset
        self.rows = []
        self.columns = []
        self.column_map = {}
        self.id_list = []
        self.paginator = None
        self.page = None
        self.sort_list = None
        self.state_loaded = False
        self.page_num = 0
        self.id = None
        self.extra_context = dict(extra_context)
        self.optimize_sorts = optimize_sorts
        self.special_query_args = []

        if not hasattr(request, "datagrid_count"):
            request.datagrid_count = 0

        self.id = "datagrid-%s" % request.datagrid_count
        request.datagrid_count += 1

        # Customizable variables
        self.title = title
        self.profile_sort_field = None
        self.profile_columns_field = None
        self.paginate_by = 50
        self.paginate_orphans = 3
        self.listview_template = 'datagrid/listview.html'
        self.column_header_template = 'datagrid/column_header.html'
        self.cell_template = 'datagrid/cell.html'
        self.paginator_template = 'datagrid/paginator.html'

    @cached_property
    def cell_template_obj(self):
        obj = get_template(self.cell_template)

        if not obj:
            logging.error("Unable to load template '%s' for datagrid "
                          "cell. This may be an installation issue.",
                          self.cell_template,
                          extra={
                              'request': self.request,
                          })

        return obj

    @cached_property
    def column_header_template_obj(self):
        obj = get_template(self.column_header_template)

        if not obj:
            logging.error("Unable to load template '%s' for datagrid "
                          "column headers. This may be an installation "
                          "issue.",
                          self.column_header_template,
                          extra={
                              'request': self.request,
                          })

        return obj

    @property
    def all_columns(self):
        """Returns all columns in the datagrid, sorted by label."""
        return [
            self.get_stateful_column(column)
            for column in sorted(self.get_columns(),
                                 key=lambda x: x.detailed_label)
        ]

    def get_stateful_column(self, column):
        """Returns a StatefulColumn for the given Column instance.

        If one has already been created, it will be returned.
        """
        if column not in self.column_map:
            self.column_map[column] = StatefulColumn(self, column)

        return self.column_map[column]

    def load_state(self, render_context=None):
        """
        Loads the state of the datagrid.

        This will retrieve the user-specified or previously stored
        sorting order and columns list, as well as any state a subclass
        may need.
        """
        if self.state_loaded:
            return

        profile_sort_list = None
        profile_columns_list = None
        profile = None
        profile_dirty = False

        # Get the saved settings for this grid in the profile. These will
        # work as defaults and allow us to determine if we need to save
        # the profile.
        if self.request.user.is_authenticated():
            try:
                profile = self.request.user.get_profile()

                if self.profile_sort_field:
                    profile_sort_list = \
                        getattr(profile, self.profile_sort_field, None)

                if self.profile_columns_field:
                    profile_columns_list = \
                        getattr(profile, self.profile_columns_field, None)
            except SiteProfileNotAvailable:
                pass
            except ObjectDoesNotExist:
                pass

        # Figure out the columns we're going to display
        # We're also going to calculate the column widths based on the
        # shrink and expand values.
        colnames_str = self.request.GET.get('columns', profile_columns_list)

        if colnames_str:
            colnames = colnames_str.split(',')
        else:
            colnames = self.default_columns
            colnames_str = ",".join(colnames)

        expand_columns = []
        normal_columns = []

        for colname in colnames:
            column_def = self.get_column(colname)

            if not column_def:
                # The user specified a column that doesn't exist. Skip it.
                continue

            column = self.get_stateful_column(column_def)
            self.columns.append(column)
            column.active = True

            if column.expand:
                # This column is requesting all remaining space. Save it for
                # later so we can tell how much to give it. Each expanded
                # column will count as two normal columns when calculating
                # the normal sized columns.
                expand_columns.append(column)
            elif column.shrink:
                # Make this as small as possible.
                column.width = 0
            else:
                # We'll divide the column widths equally after we've built
                # up the lists of expanded and normal sized columns.
                normal_columns.append(column)

        self.columns[-1].last = True

        # Try to figure out the column widths for each column.
        # We'll start with the normal sized columns.
        total_pct = 100

        # Each expanded column counts as two normal columns.
        normal_column_width = total_pct / (len(self.columns) +
                                           len(expand_columns))

        for column in normal_columns:
            column.width = normal_column_width
            total_pct -= normal_column_width

        if len(expand_columns) > 0:
            expanded_column_width = total_pct / len(expand_columns)
        else:
            expanded_column_width = 0

        for column in expand_columns:
            column.width = expanded_column_width

        # Now get the sorting order for the columns.
        sort_str = self.request.GET.get('sort', profile_sort_list)

        if sort_str:
            self.sort_list = sort_str.split(',')
        else:
            self.sort_list = self.default_sort
            sort_str = ",".join(self.sort_list)

        # A subclass might have some work to do for loading and saving
        # as well.
        if self.load_extra_state(profile):
            profile_dirty = True

        # Now that we have all that, figure out if we need to save new
        # settings back to the profile.
        if profile:
            if (self.profile_columns_field and
                    colnames_str != profile_columns_list):
                setattr(profile, self.profile_columns_field, colnames_str)
                profile_dirty = True

            if self.profile_sort_field and sort_str != profile_sort_list:
                setattr(profile, self.profile_sort_field, sort_str)
                profile_dirty = True

            if profile_dirty:
                profile.save()

        self.state_loaded = True

        # Fetch the list of objects and have it ready.
        self.precompute_objects(render_context)

    def load_extra_state(self, profile):
        """
        Loads any extra state needed for this grid.

        This is used by subclasses that may have additional data to load
        and save. This should return True if any profile-stored state has
        changed, or False otherwise.
        """
        return False

    def precompute_objects(self, render_context=None):
        """
        Builds the queryset and stores the list of objects for use in
        rendering the datagrid.
        """
        query = self.queryset
        use_select_related = False

        # Generate the actual list of fields we'll be sorting by
        sort_list = []
        for sort_item in self.sort_list:
            if sort_item[0] == "-":
                base_sort_item = sort_item[1:]
                prefix = "-"
            else:
                base_sort_item = sort_item
                prefix = ""

            if sort_item:
                column = self.get_column(base_sort_item)
                if not column:
                    logging.warning('Skipping non-existing sort column "%s" '
                                    'for user "%s".',
                                    base_sort_item, self.request.user.username)
                    continue

                stateful_column = self.get_stateful_column(column)

                if stateful_column:
                    try:
                        sort_field = stateful_column.get_sort_field()
                    except Exception as e:
                        logging.error('Error when calling get_sort_field for '
                                      'DataGrid Column %r: %s',
                                      column, e, exc_info=1)
                        sort_field = ''

                    sort_list.append(prefix + sort_field)

                    # Lookups spanning tables require that we query from those
                    # tables. In order to keep things simple, we'll just use
                    # select_related so that we don't have to figure out the
                    # table relationships. We only do this if we have a lookup
                    # spanning tables.
                    if '.' in sort_field:
                        use_select_related = True

        if sort_list:
            query = query.order_by(*sort_list)

        query = self.post_process_queryset(query)

        self.paginator = QuerySetPaginator(query.distinct(), self.paginate_by,
                                           self.paginate_orphans)

        page_num = self.request.GET.get('page', 1)

        # Accept either "last" or a valid page number.
        if page_num == "last":
            page_num = self.paginator.num_pages

        try:
            self.page = self.paginator.page(page_num)
        except InvalidPage:
            raise Http404

        self.id_list = []

        if self.optimize_sorts and len(sort_list) > 0:
            # This can be slow when sorting by multiple columns. If we
            # have multiple items in the sort list, we'll request just the
            # IDs and then fetch the actual details from that.
            self.id_list = list(self.page.object_list.values_list(
                'pk', flat=True))

            # Make sure to unset the order. We can't meaningfully order these
            # results in the query, as what we really want is to keep it in
            # the order specified in id_list, and we certainly don't want
            # the database to do any special ordering (possibly slowing things
            # down). We'll set the order properly in a minute.
            self.page.object_list = self.post_process_queryset(
                self.queryset.model.objects.filter(
                    pk__in=self.id_list).order_by())

        if use_select_related:
            self.page.object_list = \
                self.page.object_list.select_related(depth=1)

        if self.id_list:
            # The database will give us the items in a more or less random
            # order, since it doesn't know to keep it in the order provided by
            # the ID list. This will place the results back in the order we
            # expect.
            index = dict([(id, pos) for (pos, id) in enumerate(self.id_list)])
            object_list = [None] * len(self.id_list)

            for obj in list(self.page.object_list):
                object_list[index[obj.pk]] = obj
        else:
            # Grab the whole list at once. We know it won't be too large,
            # and it will prevent one query per row.
            object_list = list(self.page.object_list)

        for column in self.columns:
            column.collect_objects(object_list)

        if render_context is None:
            render_context = self._build_render_context()

        try:
            self.rows = [
                {
                    'object': obj,
                    'cells': [column.render_cell(obj, render_context)
                              for column in self.columns]
                }
                for obj in object_list if obj is not None
            ]
        except Exception as e:
            logging.error('Error when calling render_cell for DataGrid '
                          'Column %r: %s',
                          column, e, exc_info=1)

    def post_process_queryset(self, queryset):
        """Add column-specific data to the queryset.

        Individual columns can define additional joins and extra info to add on
        to the queryset. This handles adding all of those.
        """
        for column in self.columns:
            try:
                queryset = column.augment_queryset(queryset)
            except Exception as e:
                logging.error('Error when calling augment_queryset for '
                              'DataGrid Column %r: %s',
                              column, e, exc_info=1)

        return queryset

    def render_listview(self, render_context=None):
        """
        Renders the standard list view of the grid.

        This can be called from templates.
        """
        try:
            if render_context is None:
                render_context = self._build_render_context()

            self.load_state(render_context)

            context = {
                'datagrid': self,
            }

            context.update(self.extra_context)
            context.update(render_context)

            return mark_safe(render_to_string(self.listview_template,
                                              Context(context)))
        except Exception:
            trace = traceback.format_exc()
            logging.error('Failed to render datagrid:\n%s' % trace,
                          extra={
                              'request': self.request,
                          })
            return mark_safe('<pre>%s</pre>' % trace)

    def render_listview_to_response(self, request=None, render_context=None):
        """
        Renders the listview to a response, preventing caching in the
        process.
        """
        response = HttpResponse(
            six.text_type(self.render_listview(render_context)))
        patch_cache_control(response, no_cache=True, no_store=True, max_age=0,
                            must_revalidate=True)
        return response

    def render_to_response(self, template_name, extra_context={}):
        """
        Renders a template containing this datagrid as a context variable.
        """
        render_context = self._build_render_context()
        self.load_state(render_context)

        # If the caller is requesting just this particular grid, return it.
        if self.request.GET.get('gridonly', False) and \
           self.request.GET.get('datagrid-id', None) == self.id:
            return self.render_listview_to_response(
                render_context=render_context)

        context = {
            'datagrid': self
        }
        context.update(extra_context)
        context.update(render_context)

        return render_to_response(template_name, Context(context))

    def render_paginator(self, adjacent_pages=3):
        """Renders the paginator for the datagrid.

        This can be called from templates.
        """
        extra_query = get_url_params_except(self.request.GET,
                                            'page',
                                            *self.special_query_args)

        page_nums = range(max(1, self.page.number - adjacent_pages),
                          min(self.paginator.num_pages,
                              self.page.number + adjacent_pages)
                          + 1)

        if extra_query:
            extra_query += '&'

        context = {
            'is_paginated': self.page.has_other_pages(),
            'hits': self.paginator.count,
            'results_per_page': self.paginate_by,
            'page': self.page.number,
            'pages': self.paginator.num_pages,
            'page_numbers': page_nums,
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            'show_first': 1 not in page_nums,
            'show_last': self.paginator.num_pages not in page_nums,
            'extra_query': extra_query,
        }

        if self.page.has_next():
            context['next'] = self.page.next_page_number()
        else:
            context['next'] = None

        if self.page.has_previous():
            context['previous'] = self.page.previous_page_number()
        else:
            context['previous'] = None

        context.update(self.extra_context)

        return mark_safe(render_to_string(self.paginator_template,
                                          Context(context)))

    def _build_render_context(self):
        """Builds a dictionary containing RequestContext contents.

        A RequestContext can be expensive, so it's best to reuse the
        contents of one when possible. This is not easy with a standard
        RequestContext, but it's possible to build one and then pull out
        the contents into a dictionary.
        """
        request_context = RequestContext(self.request)
        render_context = {}

        for d in request_context:
            render_context.update(d)

        return render_context

    @staticmethod
    def link_to_object(state, obj, value):
        return obj.get_absolute_url()

    @staticmethod
    def link_to_value(state, obj, value):
        return value.get_absolute_url()


class AlphanumericDataGrid(DataGrid):
    """Datagrid subclass that creates an alphanumerically paginated datagrid.

    This is useful for datasets that need to be queried alphanumerically,
    according to the starting character of their 'sortable' column.
    """
    def __init__(self, request, queryset, sortable_column,
                 extra_regex='^[0-9].*', *args, **kwargs):
        self.current_letter = request.GET.get('letter', 'all')

        regex_match = re.compile(extra_regex)

        if self.current_letter == 'all':
            pass  # No filtering
        elif self.current_letter.isalpha():
            queryset = queryset.filter(**{
                sortable_column + '__istartswith': self.current_letter
            })
        elif regex_match.match(self.current_letter):
            queryset = queryset.filter(**{
                sortable_column + '__regex': extra_regex
            })
        else:
            raise Http404

        super(AlphanumericDataGrid, self).__init__(request, queryset,
                                                   *args, **kwargs)

        self.extra_context['current_letter'] = self.current_letter
        self.extra_context['letters'] = (['all', '0'] +
                                         list(string.ascii_uppercase))

        self.special_query_args.append('letter')
        self.paginator_template = 'datagrid/alphanumeric_paginator.html'
