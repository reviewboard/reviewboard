function refreshWidgets() {
        var sideWidth = $("#admin-actions").outerWidth(),
            centerWidth = $("#admin-widgets").outerWidth(),
            docWidth = $(window).width();
        var widSpace = docWidth - (sideWidth + centerWidth) - 50;

        $(".admin-extras").css('width', widSpace);
        $('.admin-extras').masonry('reload');
}

$(function () {
    $('.admin-extras').masonry({
      itemSelector: '.admin-widget'
    });
    refreshWidgets();
    $(window).resize(function() {
        refreshWidgets();
    });

    // Heading Toggle
    $("#dashboard-view .widget-heading").click(function() {
        var widgetBox = $(this).parent(),
        widgetBoxId = widgetBox.attr('id');
        widgetBox.fadeTo('fast', 0, function() {
            widgetBox.find(".widget-content").slideToggle('fast', function() {
                $('.admin-extras').masonry( 'reload' );
                widgetBox.fadeTo("fast", 1);
                if (widgetBox.hasClass("widget-hidden")) {
                    widgetBox.removeClass("widget-hidden")
                    $.get("widget-toggle/?widget=" + widgetBoxId + "&collapse=0");
                } else {
                    widgetBox.addClass("widget-hidden");
                    $.get("widget-toggle/?widget=" + widgetBoxId + "&collapse=1");
                }
             });
        });
    });
});

function dashboardFadeIn() {
    $('.admin-extras').masonry('reload', function() {
        $("#dashboard-view").animate({
        opacity: 1
        }, 500, function() {});
    });
}

 $(window).load(function() {
     var hiddenWidgets = $(".widget-hidden .widget-content");
     if(hiddenWidgets.length > 0) {
        hiddenWidgets.slideUp("fast", function() {
            dashboardFadeIn();
        });
     } else {
        dashboardFadeIn();
     }

});