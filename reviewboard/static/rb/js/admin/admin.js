$(window).load(function() {
    $(".admin-widget").each(function() {
        var widget = $(this);

        if (widget.hasClass("widget-hidden")) {
            widget.trigger("widget-hidden");
        } else {
            widget.trigger("widget-shown");
        }
    });
});

function postWidgetPositions(widgetType, widgetSize) {
    var positionData = {'type': widgetType};
    if (widgetType === "primary") {
        $("#admin-widgets .widget-" + widgetSize).each(function(i, el) {
            positionData[el.id] = i;
        });
    } else {
        $("#admin-extras .widget-" + widgetSize).each(function(i, el) {
            positionData[el.id] = i;
        });
    }

    $.ajax({
        type: "POST",
        url: 'widget-move/',
        data: positionData
    });
}

function postAddedWidgets(widgetType, widgetSize) {
    var selectionData = {'type': widgetType},
    widgetCheckbox = "#" + widgetSize + "-widget-modal .widget-label input";
    $(widgetCheckbox).each(function(i, el) {
        if ($(el).prop('checked')) {
            selectionData[el.name] = "1";
        }
    });

    $.ajax({
        type: "POST",
        url: 'widget-select/',
        data: selectionData,
        success: function() {
            postWidgetPositions(widgetType, widgetSize);
            location.reload();
        }
    });
}

function postRemovedWidgets(widgetID, widgetType, widgetSize) {
    var selectionData = {'type': widgetType};
    selectionData[widgetID] = "0";

    $.ajax({
        beforeSend: function() {
            return confirm(gettext("Are you sure you want to remove this widget?"));
        },
        type: "POST",
        url: 'widget-select/',
        data: selectionData,
        success: function() {
            // Remove widget from dashboard
            $("#" + widgetID)
                .removeClass('widget-masonry-item')
                .parent()
                    .masonry('reload')
                    .end()
                .remove();

            // Add widget to modal
            $("#" + widgetSize + "-widget-modal table td")
                .each(function(i, el) {
                    var element = $(el);
                    if (element.html() === "") {
                        parentID = "#all-modal-" + widgetType + "-widgets ";
                        widgetSelectionID = "#" + widgetID + "-selection";

                        // Append hidden widget image to modal
                        element.append($(parentID + widgetSelectionID));

                        if (i === 0) {
                            $("#no-" + widgetSize + "-msg").hide();
                        }
                        return;
                    }
                });
            postWidgetPositions(widgetType, widgetSize);
        }
    });
}

function makeDashboardSortable() {
    $("#admin-widgets").sortable({
        items: '.widget-large',
        revert: true,
        axis: 'y',
        containment: 'parent',
        stop: function() {
            postWidgetPositions('primary', 'large');
            $("#activity-graph-widget .btn-s").click(function() {
                $(this).toggleClass("btn-s-checked");
                getActivityData("same");
            });
        }
    });
}

function makeSidebarSortable() {
    $("#admin-extras").sortable({
        items: '.widget-small',
        revert: true,
        axis: 'y',
        containment: 'parent',
        start: function(event, ui) {
           /*
            * Temporarily remove masonry to avoid conflicts with jQuery UI
            * sortable.
            */
            ui.item.removeClass('widget-masonry-item');
            ui.item.parent()
                .masonry('reload');
        },
        change: function(event, ui) {
            ui.item.parent().masonry('reload');
        },
        stop: function(event, ui) {
            postWidgetPositions('secondary', 'small');
            ui.item.addClass('widget-masonry-item');
            ui.item.parent()
                .masonry({
                    itemSelector: '.widget-masonry-item'
                })
                .masonry('reload');
        }
    });
}

function createWidgetAdderModals() {
    var buttonText = gettext("Save Widgets"),
        buttonsPrimary = {},
        buttonsSecondary = {};

    buttonsPrimary[buttonText] = function() {
        postAddedWidgets('primary', 'large');
        $(this).dialog('close');
    };
    $("#large-widget-modal").dialog({
        height: 550,
        width: 315,
        modal: true,
        autoOpen: false,
        resizable: false,
        buttons: buttonsPrimary
    });

    buttonsSecondary[buttonText] = function() {
        postAddedWidgets('secondary', 'small');
        $(this).dialog('close');
    };
    $("#small-widget-modal").dialog({
        height: 520,
        width: 335,
        modal: true,
        autoOpen: false,
        resizable: false,
        buttons: buttonsSecondary
    });
}

$(document).ready(function() {
    var adminExtras = $("#admin-extras"),
        supportBanner = new RB.SupportBannerView({
            el: $('#support-banner')
        }),
        primary_total,
        primary_unselected,
        primary_selected,
        secondary_total,
        secondary_unselected,
        secondary_selected;

    function refreshWidgets() {
        var sideWidth = $("#admin-actions").outerWidth(),
            centerWidth = $("#admin-widgets").outerWidth(),
            winWidth = $("#dashboard-view").width();

        adminExtras
            .width(Math.max(0, winWidth - (sideWidth + centerWidth) - 50))
            .masonry('reload');
    }

    adminExtras.masonry({
        itemSelector: '.widget-masonry-item'
    });

    $(window).on('reflowWidgets resize', refreshWidgets);
    refreshWidgets();

    // Heading Toggle
    $("#dashboard-view .widget-heading .expand-collapse").click(function() {
        var $stateIcon = $(this),
            $widgetBox = $stateIcon.parents('.admin-widget'),
            widgetBoxId = $widgetBox.attr('id');

        $widgetBox.find(".widget-content").slideToggle('fast', function() {
            var collapsed;

            adminExtras.masonry('reload');

            if ($widgetBox.hasClass("widget-hidden")) {
                $widgetBox.removeClass("widget-hidden");
                collapsed = 0;
                $widgetBox.trigger("widget-shown");
                $stateIcon
                    .removeClass('rb-icon-admin-expand')
                    .addClass('rb-icon-admin-collapse');
            } else {
                $widgetBox.addClass("widget-hidden");
                $widgetBox.trigger("widget-hidden");
                collapsed = 1;
                $stateIcon
                    .removeClass('rb-icon-admin-collapse')
                    .addClass('rb-icon-admin-expand');
            }

            $.post("widget-toggle/?widget=" + widgetBoxId +
                   "&collapse=" + collapsed);
         });
    });

    // Calls methods to implement drag and drop for large and small widgets
    makeDashboardSortable();
    makeSidebarSortable();

    $(".widget-draggable")
        .disableSelection()
        .on('hover', function() {
            $(this).css('cursor', 'move');
        });

    $(".widget-large .rb-icon-remove-widget").on('click', function() {
        postRemovedWidgets($(this).attr('name'), 'primary', 'large');
    });
    $(".widget-small .rb-icon-remove-widget").on('click', function() {
        postRemovedWidgets($(this).attr('name'), 'secondary', 'small');
    });

    // Makes two modals that display large and small widgets to be added
    createWidgetAdderModals();
    $("#large-widget-adder a").on('click', function() {
        $("#large-widget-modal").dialog("open");
    });
    $("#small-widget-adder a").on('click', function() {
        $("#small-widget-modal").dialog("open");
    });

    // Append empty td cells to large widget modal
    primary_total = $("#all-modal-primary-widgets img").length;
    primary_unselected = $("#large-widget-modal td").length;
    primary_selected = primary_total - primary_unselected;

    while (primary_selected > 0) {
        $("#large-widget-modal table").append("<tr><td></td></tr>");
        primary_selected -= 1;
    }

    if (primary_unselected > 0) {
        $("#no-large-msg").hide();
    }

    // Append empty td cells to small widget modal
    secondary_total = $("#all-modal-secondary-widgets img").length;
    secondary_unselected = $("#small-widget-modal td").length;
    secondary_selected = secondary_total - secondary_unselected;

    while (secondary_selected > 0) {
        if (secondary_selected % 2 === 1) {
            $("#small-widget-modal table tr").last().append("<td></td>");
            secondary_selected -= 1;
        } else {
            $("#small-widget-modal table").append("<tr><td></td><td></td></tr>");
            secondary_selected -= 2;
        }
    }

    if (secondary_unselected > 0) {
        $("#no-small-msg").hide();
    }

    supportBanner.render();
});
