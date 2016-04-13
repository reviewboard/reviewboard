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
    $(".widget-" + widgetSize).each(function(index, element) {
        positionData[element.id] = index;
    });

    $.ajax({
        type: "POST",
        url: 'widget-move/',
        data: positionData
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

$(document).ready(function() {
    var adminExtras = $("#admin-extras"),
        supportBanner = new RB.SupportBannerView({
            el: $('#support-banner')
        });

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
    $("#dashboard-view .widget-heading .btn-state").click(function() {
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

   /*
    * Calls methods to implement drag and drop
    * for both large and small widgets
    */
    makeDashboardSortable();
    makeSidebarSortable();

    $(".widget-draggable")
        .disableSelection()
        .on('hover', function() {
            $(this).css('cursor', 'move');
        });
    
    supportBanner.render();
});
