/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2012 Beanbag, Inc.
 *
 * Licensed under the MIT license.
 */
(function($) {


/*
 * Creates a datagrid. This will cause drag and drop and column
 * customization to be enabled.
 */
$.fn.datagrid = function(options) {
    var $grid = this,
        gridId = this.attr("id"),
        $menu = $("#" + gridId + "-menu"),
        $gridContainer = $grid.find('.datagrid'),
        $bodyContainer = $gridContainer.find('.datagrid-body-container'),
        $headTable = $gridContainer.find('.datagrid-head'),
        $bodyTable = $bodyContainer.find('.datagrid-body'),
        $bodyTableHead = $bodyTable.find('thead'),
        $paginator = $gridContainer.find('.paginator'),
        $window = $(window),
        $editButton,

        /* State */
        storedColWidths = [],
        activeColumns = [],
        $activeMenu = null,
        columnMidpoints = [],
        dragColumn = null,
        dragColumnsChanged = false,
        dragColumnWidth = 0,
        dragIndex = 0,
        dragLastX = 0,
        lastWindowWidth;

    options = options || {};


    /********************************************************************
     * Public methods
     ********************************************************************/
    this.reload = function() {
        loadFromServer(null, true);
    };

    /*
     * Resizes the table body to fit into the datagrid's allocated height.
     *
     * This requires a fixed height on the datagrid, which must be
     * done by the caller.
     */
    this.resizeToFit = function() {
        $bodyContainer.height($grid.innerHeight() -
                              $bodyContainer.position().top -
                              ($paginator.outerHeight() || 0));

        syncColumnSizes();
    };


    /********************************************************************
     * Layout
     ********************************************************************/

    /*
     * Sets up the table header.
     *
     * This pulls out the table header into its own table, stores elements
     * and state, and hooks up events.
     *
     * We create a separate table for the header in order to allow for the
     * table body to scroll without scrolling the header. This requires
     * that a caller sets a fixed height for the datagrid and calls
     * resizeToFit on window resize.
     */
    function setupHeader() {
        var $origHeader = $bodyTable.find('thead');

        /* Store the original widths of the colgroup columns. */
        $bodyTable.find('colgroup col').each(function(i, colEl) {
            storedColWidths.push(colEl.width);
        });

        /* Create a copy of the header and place it in a separate table. */
        $headTable
            .find('thead')
                .remove()
            .end()
            .append($origHeader.clone().show());
        $origHeader.hide();

        activeColumns = [];

        /* Add all the non-special columns to the list. */
        $headTable.find("col").not(".datagrid-customize")
            .each(function(i, col) {
                activeColumns.push(col.className);
            });

        $headTable.find("th")
            /* Make the columns unselectable. */
            .disableSelection()

            /* Make the columns draggable. */
            .not(".edit-columns").draggable({
                appendTo: "body",
                axis: "x",
                containment: $headTable.find("thead:first"),
                cursor: "move",
                helper: function() {
                    var $el = $(this);

                    return $("<div/>")
                        .addClass("datagrid-header-drag datagrid-header")
                        .width($el.width())
                        .height($el.height())
                        .css("top", $el.offset().top)
                        .html($el.html());
                },
                start: startColumnDrag,
                stop: endColumnDrag,
                drag: onColumnDrag
            });

        $editButton = $("#" + gridId + "-edit")
            .click(function(evt) {
                evt.stopPropagation();
                toggleColumnsMenu();
            });

        $headTable.find('.datagrid-header-checkbox').change(function() {
            /*
             * Change the checked state of all matching checkboxes to reflect
             * the state of the checkbox in the header.
             */
            var $checkbox = $(this),
                colName = $checkbox.data('checkbox-name');

            $bodyTable.find('tbody input[data-checkbox-name="' + colName + '"]')
                .prop('checked', $checkbox.prop('checked'))
                .change();
        });
    }

    /*
     * Synchronizes the column sizes between the header and body tables.
     *
     * Since we have two tables that we're pretending are one, we need to
     * make sure the columns line up properly. This performs that work by
     * doing the following:
     *
     * 1) Reset the main table back to the defaults we had when the datagrid
     *    was first created.
     *
     * 2) Temporarily show the "real" header, so we can calculate all the
     *    widths.
     *
     * 3) Calculate all the new widths for the colgroups for both tables,
     *    taking into account the scrollbar.
     *
     * 4) Set the widths to their new values.
     */
    function syncColumnSizes() {
        var origHeaderCells = $bodyTableHead[0].rows[0].cells,
            $fixedCols = $headTable.find('colgroup col'),
            $origCols = $bodyTable.find('colgroup col'),
            numCols = origHeaderCells.length,
            bodyWidths = [],
            headWidths = [],
            extraWidth = 0,
            width,
            i;

        /* First, unset all the widths and restore to defaults. */
        for (i = 0; i < numCols; i++) {
            $origCols[i].width = storedColWidths[i];
        }

        /* Store all the widths we'll apply. */
        $bodyTableHead.show();

        $headTable.width($bodyContainer.width() - 1);
        extraWidth = $bodyContainer.width() - $bodyTable.width();

        for (i = 0; i < numCols; i++) {
            width = $(origHeaderCells[i]).outerWidth();
            bodyWidths.push(width);
            headWidths.push(width);
        }

        $bodyTableHead.hide();

        /* Modify the widths to account for the scrollbar and extra spacing */
        headWidths[numCols - 1] = bodyWidths[numCols - 1] - 1;
        headWidths[numCols - 2] = bodyWidths[numCols - 2] - 1 + extraWidth;

        /* Now set the new state. */
        for (i = 0; i < numCols; i++) {
            $origCols[i].width = bodyWidths[i];
            $fixedCols[i].width = headWidths[i];
        }
    }

    /*
     * Handles window resizes.
     *
     * If resizing horizontally, the column widths will be synced up again.
     */
    function onResize() {
        var windowWidth = $window.width();

        if (windowWidth !== lastWindowWidth) {
            lastWindowWidth = windowWidth;

            syncColumnSizes();
        }
    }


    /********************************************************************
     * Server communication
     ********************************************************************/

    function loadFromServer(params, reloadGrid) {
        var search = window.location.search || '?',
            url = window.location.pathname + search +
                  '&gridonly=1&datagrid-id=' + gridId;

        if (params) {
            url += '&' + params;
        }

        $.get(url, function(html) {
            if (reloadGrid) {
                $grid.replaceWith(html);
                $grid = $("#" + gridId).datagrid();
            } else {
                setupHeader();
            }

            $grid.trigger('reloaded');
        });
    }


    /********************************************************************
     * Column customization
     ********************************************************************/

    /*
     * Hides the currently open columns menu.
     */
    function hideColumnsMenu() {
        if ($activeMenu !== null) {
            $activeMenu.hide();
            $activeMenu = null;
        }
    }

    /*
     * Toggles the visibility of the specified columns menu.
     */
    function toggleColumnsMenu() {
        var offset;

        if ($menu.is(":visible")) {
            hideColumnsMenu();
        } else {
            offset = $editButton.position();

            $menu
                .css({
                    left: offset.left - $menu.outerWidth() +
                          $editButton.outerWidth(),
                    top:  offset.top + $editButton.outerHeight()
                })
                .show();

            $activeMenu = $menu;
        }
    }

    /*
     * Saves the new columns list on the server.
     *
     * @param {string}   columnsStr  The columns to display.
     * @param {boolean}  reloadGrid  Reload from the server.
     */
    function saveColumns(columnsStr, reloadGrid) {
        loadFromServer('columns=' + columnsStr, reloadGrid);
    }

    /*
     * Toggles the visibility of a column. This will build the resulting
     * columns string and request a save of the columns, followed by a
     * reload of the page.
     *
     * @param {string}  columnId  The ID of the column to toggle.
     */
    function toggleColumn(columnId) {
        saveColumns(serializeColumns(columnId), true);
    }

    /*
     * Serializes the active column list, optionally adding one new entry
     * to the end of the list.
     *
     * @return The serialized column list.
     */
    function serializeColumns(addedColumn) {
        var columnsStr = "";

        $(activeColumns).each(function(i) {
            var curColumn = activeColumns[i];

            if (curColumn === addedColumn) {
                /* We're removing this column. */
                addedColumn = null;
            } else {
                columnsStr += curColumn;

                if (i < activeColumns.length - 1) {
                    columnsStr += ",";
                }
            }
        });

        if (addedColumn) {
            columnsStr += "," + addedColumn;
        }

        return columnsStr;
    }


    /********************************************************************
     * Column reordering support
     ********************************************************************/

    /*
     * Handles the beginning of the drag.
     *
     * Builds the column information needed for determining when we should
     * switch columns.
     *
     * @param {event}  evt The event.
     * @param {object} ui  The jQuery drag and drop information.
     */
    function startColumnDrag(evt, ui) {
        dragColumn = this;
        dragColumnsChanged = false;
        dragColumnWidth = ui.helper.width();
        dragIndex = 0;
        dragLastX = 0;
        buildColumnInfo();

        /* Hide the column but keep its area reserved. */
        $(dragColumn).css("visibility", "hidden");
    }

    /*
     * Handles the end of a drag.
     *
     * This shows the original header (now in its new place) and saves
     * the new columns configuration.
     */
    function endColumnDrag() {
        var $column = $(this);

        /* Re-show the column header. */
        $column.css("visibility", "visible");

        columnMidpoints = [];

        if (dragColumnsChanged) {
            /* Build the new columns list */
            saveColumns(serializeColumns());
        }
    }

    /*
     * Handles movement while in drag mode.
     *
     * This will check if we've crossed the midpoint of a column. If so, we
     * switch the columns.
     *
     * @param {event}  e  The event.
     * @param {object} ui The jQuery drag and drop information.
     */
    function onColumnDrag(e, ui) {
        /*
         * Check the direction we're moving and see if we're ready to switch
         * with another column.
         */
        var x = e.originalEvent.pageX,
            hitX = -1,
            index = -1;

        if (x === dragLastX) {
            /* No change that we care about. Bail out. */
            return;
        }

        if (x < dragLastX) {
            index = dragIndex - 1;
            hitX = ui.offset.left;
        } else {
            index = dragIndex + 1;
            hitX = ui.offset.left + ui.helper.width();
        }

        if (index >= 0 && index < columnMidpoints.length) {
            /* Check that we're dragging past the midpoint. If so, swap. */
            if (x < dragLastX && hitX <= columnMidpoints[index]) {
                swapColumnBefore(dragIndex, index);
            } else if (x > dragLastX && hitX >= columnMidpoints[index]) {
                swapColumnBefore(index, dragIndex);
            }
        }

        dragLastX = x;
    }

    /*
     * Builds the necessary information on the columns.
     *
     * This will construct an array of midpoints that are used to determine
     * when we should swap columns during a drag. It also sets the index
     * of the currently dragged column.
     */
    function buildColumnInfo() {
        /* Clear and rebuild the list of mid points. */
        columnMidpoints = [];

        $headTable.find("th").not(".edit-columns").each(function(i, column) {
            var $column = $(column),
                offset = $column.offset();

            if (column === dragColumn) {
                dragIndex = i;

                /*
                 * Getting the width of an invisible element is very bad
                 * when the element is a <th>. Use our pre-calculated width.
                 */
                width = dragColumnWidth;
            } else {
                width = $column.width();
            }

            columnMidpoints.push(Math.round(offset.left + width / 2));
        });
    }

    /*
     * Swaps two columns, placing the first before the second.
     *
     * It is assumed that the two columns are siblings. Horrible disfiguring
     * things might happen if this isn't the case, or it might not. Who
     * can tell. Our code behaves, though.
     *
     * @param {int} index       The index of the column to move.
     * @param {int} beforeIndex The index of the column to place the first
     *                          before.
     */
    function swapColumnBefore(index, beforeIndex) {
        var temp;

        /* Swap the list of active columns */
        temp = activeColumns[index];
        activeColumns[index] = activeColumns[beforeIndex];
        activeColumns[beforeIndex] = temp;

        /* Swap the cells. This will include the headers. */
        swapColumns($bodyTable[0], beforeIndex, index);
        swapColumns($headTable[0], beforeIndex, index);

        /* Swap the stored widths. */
        temp = storedColWidths[index];
        storedColWidths[index] = storedColWidths[beforeIndex];
        storedColWidths[beforeIndex] = temp;

        dragColumnsChanged = true;

        /* Everything has changed, so rebuild our view of things. */
        buildColumnInfo();
    }

    function swapColumns(table, beforeIndex, index) {
        var beforeCell,
            tempColSpan,
            colTags = $(table).find('colgroup col'),
            row,
            cell,
            rowsLen,
            i;

        colTags.eq(index).insertBefore(colTags.eq(beforeIndex));

        for (i = 0, rowsLen = table.rows.length; i < rowsLen; i++) {
            row = table.rows[i];
            cell = row.cells[index];
            beforeCell = row.cells[beforeIndex];

            row.insertBefore(cell, beforeCell);

            /* Switch the colspans. */
            tempColSpan = cell.colSpan;
            cell.colSpan = beforeCell.colSpan;
            beforeCell.colSpan = tempColSpan;
        }
    }


    /********************************************************************
     * Datagrid initialization
     ********************************************************************/

    $grid.data('datagrid', this);

    setupHeader();

    /* Register callbacks for the columns. */
    $menu.find("tr").each(function(i, row) {
        var className = row.className;

        $(row).find(".datagrid-menu-checkbox, .datagrid-menu-label a")
            .click(function() {
                toggleColumn(className);
            });
    });

    $(document.body).click(hideColumnsMenu);

    $window.resize(onResize);
    onResize();

    return $grid;
};

$(document).ready(function() {
    $("div.datagrid-wrapper").datagrid();
});

})(jQuery);
