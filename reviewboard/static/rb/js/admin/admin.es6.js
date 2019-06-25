$(function() {
});


function postWidgetPositions(widgetType, widgetSize) {
    const positionData = {
        type: widgetType,
    };

    const $parent = $(widgetType === 'primary'
                      ? '#admin-widgets'
                      : '#admin-extras');

    $parent.find('.rb-c-admin-widget--' + widgetSize).each((i, el) => {
        positionData[el.id] = i;
    });

    $.ajax({
        type: 'POST',
        url: 'widget-move/',
        data: positionData,
    });
}


function postAddedWidgets(widgetType, widgetSize) {
    const selectionData = {
        type: widgetType,
    };

    $(`#${widgetSize}-widget-modal .widget-label input`).each((i, el) => {
        if ($(el).prop('checked')) {
            selectionData[el.name] = '1';
        }
    });

    $.ajax({
        type: 'POST',
        url: 'widget-select/',
        data: selectionData,
        success: () => {
            postWidgetPositions(widgetType, widgetSize);
            location.reload();
        },
    });
}


function postRemovedWidgets(widgetID, widgetType, widgetSize) {
    const selectionData = {
        type: widgetType,
    };
    selectionData[widgetID] = '0';

    $.ajax({
        beforeSend: () => confirm(
            gettext('Are you sure you want to remove this widget?')),
        type: 'POST',
        url: 'widget-select/',
        data: selectionData,
        success: () => {
            // Remove widget from dashboard
            $(`#${widgetID}`)
                .removeClass('js-masonry-item')
                .parent()
                    .masonry('reload')
                    .end()
                .remove();

            // Add widget to modal
            $(`#${widgetSize}-widget-modal table td`).each((i, el) => {
                const $element = $(el);

                if ($element.html() === '') {
                    const parentID = `#all-modal-${widgetType}-widgets`;
                    const widgetSelectionID = `#${widgetID}-selection`;

                    // Append hidden widget image to modal
                    $element.append($(`${parentID} ${widgetSelectionID}`));

                    if (i === 0) {
                        $(`#no-${widgetSize}-msg`).hide();
                    }
                    return;
                }
            });
            postWidgetPositions(widgetType, widgetSize);
        },
    });
}


function makeDashboardSortable() {
    $('#admin-widgets').sortable({
        items: '.rb-c-admin-widget.-is-large',
        revert: true,
        axis: 'y',
        containment: 'parent',
        stop: () => {
            postWidgetPositions('primary', 'large');

            $('#activity-graph-widget .btn-s').click(function() {
                $(this).toggleClass('btn-s-checked');
                getActivityData('same');
            });
        }
    });
}


function makeSidebarSortable() {
    $('#admin-extras').sortable({
        items: '.rb-c-admin-widget.-is-small',
        revert: true,
        axis: 'y',
        containment: 'parent',
        start: (event, ui) => {
           /*
            * Temporarily remove masonry to avoid conflicts with jQuery UI
            * sortable.
            */
            ui.item.removeClass('js-masonry-item');
            ui.item.parent()
                .masonry('reload');
        },
        change: (event, ui) => ui.item.parent().masonry('reload'),
        stop: (event, ui) => {
            postWidgetPositions('secondary', 'small');
            ui.item.addClass('js-masonry-item');
            ui.item.parent()
                .masonry({
                    itemSelector: '.js-masonry-item'
                })
                .masonry('reload');
        },
    });
}


$(document).ready(function() {
    $('.rb-c-admin-widget').each((i, el) => {
        const $widget = $(el);

        if ($widget.hasClass('widget-hidden')) {
            $widget.trigger('widget-hidden');
        } else {
            $widget.trigger('widget-shown');
        }
    });

    const $adminExtras = $('#admin-extras');
    $adminExtras.masonry({
        itemSelector: '.js-masonry-item',
    });

    function refreshWidgets() {
        const sideWidth = $('#admin-actions').outerWidth();
        const centerWidth = $('#admin-widgets').outerWidth();
        const winWidth = $('#dashboard-view').width();

        $adminExtras
            .width(Math.max(0, winWidth - (sideWidth + centerWidth) - 50))
            .masonry('reload');
    }

    $(window).on('reflowWidgets resize', refreshWidgets);
    refreshWidgets();

    // Calls methods to implement drag and drop for large and small widgets
    makeDashboardSortable();
    makeSidebarSortable();

    $('.rb-c-admin-widget.js-draggable')
        .disableSelection()
        .on('hover', function() {
            $(this).css('cursor', 'move');
        });

    $('.rb-c-admin-widget.-is-large .rb-icon-remove-widget').on('click',
        function() {
            postRemovedWidgets($(this).attr('name'), 'primary', 'large');
        });
    $('.rb-c-admin-widget.-is-small .rb-icon-remove-widget').on('click',
        function() {
            postRemovedWidgets($(this).attr('name'), 'secondary', 'small');
        });

    const $widgetAdders = $('.widget-adders');

    $('#large-widget-adder a').on('click', () => {
        const $largeAdder = $('#large-widget-modal')
            .modalBox({
                discardOnClose: false,
                title: gettext('Add Large Widgets'),
                buttons: [
                    $('<input type="button">')
                        .val(gettext('Close'))
                        .click(() => {
                            $largeAdder
                                .modalBox('destroy')
                                .appendTo($widgetAdders);
                        }),
                    $('<input type="button">')
                        .val(gettext('Save Widgets'))
                        .click(() => {
                            postAddedWidgets('primary', 'large');
                            return false;
                        }),
                ],
            });
    });
    $('#small-widget-adder a').on('click', () => {
        const $smallAdder = $('#small-widget-modal')
            .modalBox({
                discardOnClose: false,
                title: gettext('Add Small Widgets'),
                buttons: [
                    $('<input type="button">')
                        .val(gettext('Close'))
                        .click(() => {
                            $smallAdder
                                .modalBox('destroy')
                                .appendTo($widgetAdders);
                        }),
                    $('<input type="button">')
                        .val(gettext('Save Widgets'))
                        .click(() => {
                            postAddedWidgets('secondary', 'small');
                            return false;
                        }),
                ],
            });
    });

    // Append empty td cells to large widget modal
    const primary_total = $('#all-modal-primary-widgets img').length;
    const primary_unselected = $('#large-widget-modal td').length;
    let primary_selected = primary_total - primary_unselected;

    while (primary_selected > 0) {
        $('#large-widget-modal table').append('<tr><td></td></tr>');
        primary_selected -= 1;
    }

    if (primary_unselected > 0) {
        $('#no-large-msg').hide();
    }

    // Append empty td cells to small widget modal
    const secondary_total = $('#all-modal-secondary-widgets img').length;
    const secondary_unselected = $('#small-widget-modal td').length;
    let secondary_selected = secondary_total - secondary_unselected;

    while (secondary_selected > 0) {
        if (secondary_selected % 2 === 1) {
            $('#small-widget-modal table tr').last().append('<td></td>');
            secondary_selected -= 1;
        } else {
            $('#small-widget-modal table').append('<tr><td></td><td></td></tr>');
            secondary_selected -= 2;
        }
    }

    if (secondary_unselected > 0) {
        $('#no-small-msg').hide();
    }

    const supportBanner = new RB.SupportBannerView({
        el: $('#support-banner'),
    });
    supportBanner.render();
});
