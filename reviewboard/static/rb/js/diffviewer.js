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


$(document).ready(function() {
    /*
     * Make sure any inputs on the page (such as the search box) don't
     * bubble down key presses to the document.
     */
    $("input, textarea").keypress(function(evt) {
        evt.stopPropagation();
    });
});

// vim: set et:
