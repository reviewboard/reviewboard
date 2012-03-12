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

$(document).ready(function() {
    var adminExtras = $("#admin-extras");

    function refreshWidgets() {
        var sideWidth = $("#admin-actions").outerWidth(),
            centerWidth = $("#admin-widgets").outerWidth(),
            winWidth = $(window).width();

        adminExtras
            .css('width', winWidth - (sideWidth + centerWidth) - 50)
            .masonry('reload');
    }

    adminExtras.masonry({
        itemSelector: '.admin-widget'
    });

    $(window).resize(refreshWidgets);
    refreshWidgets();

    // Heading Toggle
    $("#dashboard-view .widget-heading").click(function() {
        var widgetBox = $(this).parent(),
            widgetBoxId = widgetBox.attr('id');

        widgetBox.find(".widget-content").slideToggle('fast', function() {
            var collapsed;

            adminExtras.masonry('reload');

            if (widgetBox.hasClass("widget-hidden")) {
                widgetBox.removeClass("widget-hidden")
                collapsed = 0;
                widgetBox.trigger("widget-shown");
            } else {
                widgetBox.addClass("widget-hidden");
                widgetBox.trigger("widget-hidden");
                collapsed = 1;
            }

            $.post("widget-toggle/?widget=" + widgetBoxId +
                   "&collapse=" + collapsed);
         });
    });
});
