// State variables
var gDiffHighlightBorder = null;


/*
 * Highlights a chunk of the diff.
 *
 * This will create and move four border elements around the chunk. We use
 * these border elements instead of setting a border since few browsers
 * render borders on <tbody> tags the same, and give us few options for
 * styling.
 */
$.fn.highlightChunk = function() {
    var firstHighlight = false;

    if (!gDiffHighlightBorder) {
        var borderEl = $("<div/>")
            .addClass("diff-highlight-border")
            .css("position", "absolute");

        gDiffHighlightBorder = {
            top: borderEl.clone().appendTo("#diffs"),
            bottom: borderEl.clone().appendTo("#diffs"),
            left: borderEl.clone().appendTo("#diffs"),
            right: borderEl.clone().appendTo("#diffs")
        };

        firstHighlight = true;
    }

    var el = this.parents("tbody:first, thead:first");

    var borderWidth = gDiffHighlightBorder.left.width();
    var borderHeight = gDiffHighlightBorder.top.height();
    var borderOffsetX = borderWidth / 2;
    var borderOffsetY = borderHeight / 2;

    if ($.browser.msie && $.browser.version <= 8) {
        /* On IE, the black rectangle is too far to the top. */
        borderOffsetY = -borderOffsetY;

        if ($.browser.msie && $.browser.version == 8) {
            /* And on IE8, it's also too far to the left. */
            borderOffsetX = -borderOffsetX;
        }
    }

    var updateQueued = false;
    var oldLeft;
    var oldTop;
    var oldWidth;
    var oldHeight;

    /*
     * Updates the position of the border elements.
     */
    function updatePosition(event) {
        if (event && event.target &&
            event.target != window &&
            !event.target.getElementsByTagName) {

            /*
             * This is not a container. It might be a text node.
             * Ignore it.
             */
            return;
        }

        var offset = el.position();

        if (!offset) {
            return;
        }

        var left = Math.round(offset.left);
        var top = Math.round(offset.top);
        var width = el.outerWidth();
        var height = el.outerHeight();

        if (left == oldLeft &&
            top == oldTop &&
            width == oldWidth &&
            height == oldHeight) {

            /* The position and size haven't actually changed. */
            return;
        }

        var outerHeight = height + borderHeight;
        var outerWidth  = width + borderWidth;
        var outerLeft   = left - borderOffsetX;
        var outerTop    = top - borderOffsetY;

        gDiffHighlightBorder.left.css({
            left: outerLeft,
            top: outerTop,
            height: outerHeight
        });

        gDiffHighlightBorder.top.css({
            left: outerLeft,
            top: outerTop,
            width: outerWidth
        });

        gDiffHighlightBorder.right.css({
            left: outerLeft + width,
            top: outerTop,
            height: outerHeight
        });

        gDiffHighlightBorder.bottom.css({
            left: outerLeft,
            top: outerTop + height,
            width: outerWidth
        });

        oldLeft = left;
        oldTop = top;
        oldWidth = width;
        oldHeight = height;

        updateQueued = false;
    }

    /*
     * Updates the position after 50ms so we don't call updatePosition too
     * many times in response to a DOM change.
     */
    function queueUpdatePosition(event) {
        if (!updateQueued) {
            updateQueued = true;
            setTimeout(function() { updatePosition(event); }, 50);
        }
    }

    $(document)
        .on("DOMNodeInserted.highlightChunk DOMNodeRemoved.highlightChunk",
            queueUpdatePosition);
    $(window).on("resize.highlightChunk", updatePosition);

    if (firstHighlight) {
        /*
         * There seems to be a bug where we often won't get this right
         * away on page load. Race condition, perhaps.
         */
        queueUpdatePosition();
    } else {
        updatePosition();
    }

    return this;
};


/*
 * Toggles the display state of Whitespace chunks and lines.
 *
 * When a diff is loaded, by default, all whitespace only changes are shown.
 * This function hides the changes shown and show the hidden changes,
 * toggling the state.
 */
function toggleWhitespaceChunks()
{
    var tables = $("table.sidebyside");
    var chunks = tables.children("tbody.whitespace-chunk");

    /* Dim the whole chunk */
    chunks.toggleClass("replace");

    /* Dim the anchor to each chunk in the file list */
    chunks.each(function() {
        var target = this.id.split("chunk")[1];
        $("ol.index a[href='#" + target + "']").toggleClass("dimmed");
    });

    /* Remove chunk identifiers */
    chunks.children(":first-child").toggleClass("first");
    chunks.children(":last-child").toggleClass("last");

    /* Toggle individual lines */
    tables.find("tbody tr.whitespace-line").toggleClass("dimmed");

    /* Toggle the display of the button itself */
    $(".review-request ul.controls li.ws").toggle();

    /* Toggle adjacent chunks, and show the whitespace message */
    tables.children("tbody.whitespace-file").toggle()
                                            .siblings("tbody")
                                                .toggle();
}


/*
 * Read cookie to set user preferences for showing Extra Whitespace or not.
 *
 * Returns true by default, false only if a cookie is set.
 */
function showExtraWhitespace()
{
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(";");
        for (var i in cookies) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie == "show_ew=false") {
                return false;
            }
        }
    }

    return true;
}


/*
 * Write cookie to set user preferences for showing Extra Whitespace or not.
 *
 * This a session cookie.
 */
function setExtraWhitespace(value)
{
    document.cookie="show_ew="+value+"; path=/;";
}


/*
 * Toggles the highlighting state of Extra Whitespace.
 *
 * This function turns off or on the highlighting through the ewhl class.
 */
function toggleExtraWhitespace(init)
{

    /* Toggle the cookie value unless this is the first call */
    if ( init == undefined) {
        toggleExtraWhitespace.show_ew = !toggleExtraWhitespace.show_ew;
        setExtraWhitespace(toggleExtraWhitespace.show_ew);
    }
    else {
        /* Record initial value based on cookie setting */
        toggleExtraWhitespace.show_ew = showExtraWhitespace();

        /* Page is initially loaded with highlighting off */
        if (!toggleExtraWhitespace.show_ew) {
            return;
        }
    }

    /* Toggle highlighting */
    $("#diffs").toggleClass("ewhl");

    /* Toggle the display of the button itself */
    $(".review-request ul.controls li.ew").toggle();
}


$(document).ready(function() {
    if (!window.gRevision) {
        /* We're not running in the diff viewer. No need for setup. */
        return;
    }

    $("ul.controls li a.toggleWhitespaceButton").click(function() {
        toggleWhitespaceChunks();
        return false;
    });

    $("ul.controls li a.toggleExtraWhitespaceButton").click(function() {
        toggleExtraWhitespace();
        return false;
    });

    toggleExtraWhitespace('init');

    /*
     * Make sure any inputs on the page (such as the search box) don't
     * bubble down key presses to the document.
     */
    $("input, textarea").keypress(function(evt) {
        evt.stopPropagation();
    });
});

// vim: set et:
