function refreshWidgets() {
    var sideWidth = $("#admin-actions").outerWidth(),
        centerWidth = $("#admin-widgets").outerWidth(),
        winWidth = $(window).width();

    $(".admin-extras")
        .css('width', winWidth - (sideWidth + centerWidth) - 50)
        .masonry('reload');
}

function dashboardFadeIn() {
    $('.admin-extras').masonry('reload', function() {
        $("#dashboard-view").animate({
            opacity: 1
        }, "fast");
    });
}

$(window).load(function() {
    var hiddenWidgets = $(".widget-hidden .widget-content");

    if (hiddenWidgets.length > 0) {
        hiddenWidgets.slideUp("fast", dashboardFadeIn);
    } else {
        dashboardFadeIn();
    }
});

$(document).ready(function() {
    $('.admin-extras').masonry({
        itemSelector: '.admin-widget'
    });

    $(window).resize(refreshWidgets);
    refreshWidgets();

    // Heading Toggle
    $("#dashboard-view .widget-heading").click(function() {
        var widgetBox = $(this).parent(),
            widgetBoxId = widgetBox.attr('id');

        widgetBox.fadeTo('fast', 0, function() {
            widgetBox.find(".widget-content").slideToggle('fast', function() {
                var collapsed;

                $('.admin-extras').masonry('reload');
                widgetBox.fadeTo("fast", 1);

                if (widgetBox.hasClass("widget-hidden")) {
                    widgetBox.removeClass("widget-hidden")
                    collapsed = 0;
                } else {
                    widgetBox.addClass("widget-hidden");
                    collapsed = 1;
                }

                $.post("widget-toggle/?widget=" + widgetBoxId +
                       "&collapse=" + collapsed);
             });
        });
    });
});
