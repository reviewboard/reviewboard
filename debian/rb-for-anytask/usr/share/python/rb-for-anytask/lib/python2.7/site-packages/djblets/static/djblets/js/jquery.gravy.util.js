/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2013 Beanbag, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
(function($) {


if ($.support.touch === undefined) {
    $.support.touch = ('ontouchstart' in window ||
                       navigator.msMaxTouchPoints);
}

$.fn.extend({
    /*
     * Sets one or more elements' visibility based on the specified value.
     *
     * @param {bool} visible The visibility state.
     *
     * @return {jQuery} This jQuery.
     */
    setVisible: function(visible) {
        return $(this).each(function() {
            if (visible) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    },

    /*
     * Sets the position of an element.
     *
     * @param {int}    left     The new left position.
     * @param {int}    top      The new top position.
     * @param {string} posType  The optional position type.
     *
     * @return {jQuery} This jQuery.
     */
    move: function(left, top, posType) {
        return $(this).each(function() {
            $(this).css({
                left: left,
                top: top
            });

            if (posType) {
                $(this).css("position", posType);
            }
        });
    },

    /*
     * Scrolls an element so that it's fully in view, if it wasn't already.
     *
     * @return {jQuery} This jQuery.
     */
    scrollIntoView: function() {
        var $document = $(document),
            $window = $(window);

        return $(this).each(function() {
            var $this = $(this),
                offset = $this.offset(),
                scrollLeft = $document.scrollLeft(),
                scrollTop = $document.scrollTop(),
                elLeft = (scrollLeft + $window.width()) -
                         (offset.left + $this.outerWidth(true)),
                elTop = (scrollTop + $window.height()) -
                         (offset.top + $this.outerHeight(true));

            if (elLeft < 0) {
                $window.scrollLeft(scrollLeft - elLeft);
            }

            if (elTop < 0) {
                $window.scrollTop(scrollTop - elTop);
            }
        });
    }
});

$.fn.getExtents = function(types, sides) {
    var val = 0;

    this.each(function() {
        var self = $(this),
            type,
            side,
            prop,
            t,
            s,
            i;

        for (t = 0; t < types.length; t++) {
            type = types.charAt(t);

            for (s = 0; s < sides.length; s++) {
                side = sides.charAt(s);

                if (type === "b") {
                    type = "border";
                } else if (type === "m") {
                    type = "margin";
                } else if (type === "p") {
                    type = "padding";
                }

                if (side === "l" || side === "left") {
                    side = "Left";
                } else if (side === "r" || side === "right") {
                    side = "Right";
                } else if (side === "t" || side === "top") {
                    side = "Top";
                } else if (side === "b" || side === "bottom") {
                    side = "Bottom";
                }

                prop = type + side;

                if (type === "border") {
                    prop += "Width";
                }

                i = parseInt(self.css(prop), 10);

                if (!isNaN(i)) {
                    val += i;
                }
            }
        }
    });

    return val;
};


/*
 * Positions an element to the side of another element.
 *
 * This can take a number of options to customize how the element is
 * positioned.
 *
 * The 'side' option is a string of sides ('t', 'b', 'l', 'r') that
 * incidate the element should be positioned to the top, bottom, left,
 * or right of the other element.
 *
 * If multiple sides are provided, then this will loop through them in
 * order, trying to find the best top and the best left that fit on the
 * screen.
 *
 * If the 'distance' option is set, the element will be that many pixels
 * away from the side of the other element. Alternatively, the
 * 'xDistance' and 'yDistance' options can be set to customize that distance
 * only when positioned to the left/right of the element (for xDistance) or
 * above/below (yDistance).
 *
 * The 'xOffset' and 'yOffset' options will offset the element on that
 * axis, but only when it's not positioned relative to the other element
 * along that axis. So, if positioned to the left of the element, 'xOffset'
 * will not take affect, but 'yOffset' would. This helps with better
 * aligning horizontally/vertically with content.
 *
 * The 'fitOnScreen' option, if set to true, will ensure that the element
 * is not scrolled off the screen on any side. It will update the final
 * position of the element to be fully shown on-screen (provided the element
 * can fit on the screen).
 */
$.fn.positionToSide = function(el, options) {
    var offset = $(el).offset(),
        thisWidth = this.outerWidth(),
        thisHeight = this.outerHeight(),
        elWidth = el.width(),
        elHeight = el.height(),
        scrollLeft = $(document).scrollLeft(),
        scrollTop = $(document).scrollTop(),
        scrollWidth = $(window).width(),
        scrollHeight = $(window).height();

    options = $.extend({
        side: 'b',
        xDistance: options.distance || 0,
        yDistance: options.distance || 0,
        xOffset: 0,
        yOffset: 0,
        fitOnScreen: false
    }, options);

    return $(this).each(function() {
        var bestLeft = null,
            bestTop = null,
            side,
            left,
            top,
            i;

        for (i = 0; i < options.side.length; i++) {
            side = options.side.charAt(i);
            left = null;
            top = null;

            if (side === "t") {
                top = offset.top - thisHeight - options.yDistance;
            } else if (side === "b") {
                top = offset.top + elHeight + options.yDistance;
            } else if (side === "l") {
                left = offset.left - thisWidth - options.xDistance;
            } else if (side === "r") {
                left = offset.left + elWidth + options.xDistance;
            } else {
                continue;
            }

            if ((left !== null &&
                 left >= scrollLeft &&
                 left + thisWidth - scrollLeft < scrollWidth) ||
                (top !== null &&
                 top >= scrollTop &&
                 top + thisHeight - scrollTop < scrollHeight)) {
                bestLeft = left;
                bestTop = top;
                break;
            } else if (bestLeft === null && bestTop === null) {
                bestLeft = left;
                bestTop = top;
            }
        }

        if (bestLeft === null) {
            bestLeft = offset.left + options.xOffset;
        }

        if (bestTop === null) {
            bestTop = offset.top + options.yOffset;
        }

        if (options.fitOnScreen) {
            bestLeft = Math.max(
                Math.min(bestLeft, scrollLeft + scrollWidth - thisWidth),
                scrollLeft);
            bestTop = Math.max(
                Math.min(bestTop, scrollTop + scrollHeight - thisHeight),
                scrollTop);
        }

        $(this).move(bestLeft, bestTop, "absolute");
    });
};


$.fn.delay = function(msec) {
    return $(this).each(function() {
        var self = $(this);
        self.queue(function() {
            window.setTimeout(function() { self.dequeue(); }, msec);
        });
    });
};


$.fn.proxyTouchEvents = function(events) {
    events = events || "touchstart touchmove touchend";

    return $(this).bind(events, function(event) {
        var touches = event.originalEvent.changedTouches,
            first = touches[0],
            type = "",
            mouseEvent;

        switch (event.type) {
        case "touchstart":
            type = "mousedown";
            break;

        case "touchmove":
            type = "mousemove";
            break;

        case "touchend":
            type = "mouseup";
            break;
        }

        mouseEvent = document.createEvent("MouseEvent");
        mouseEvent.initMouseEvent(type, true, true, window, 1,
                                  first.screenX, first.screenY,
                                  first.clientX, first.clientY,
                                  false, false, false, false, 0, null);

        if (!event.target.dispatchEvent(mouseEvent)) {
            event.preventDefault();
        }
    });
};


$.extend(String.prototype, {
    strip: function() {
        return this.replace(/^\s+/, '').replace(/\s+$/, '');
    },

    stripTags: function() {
        return this.replace(/<\/?[^>]+>/gi, '');
    },

    htmlEncode: function() {
        if (this === "") {
          return "";
        }

        str = this.replace(/&/g, "&amp;");
        str = str.replace(/</g, "&lt;");
        str = str.replace(/>/g, "&gt;");

        return str;
    },

    htmlDecode: function() {
        if (this === "") {
          return "";
        }

        str = this.replace(/&amp;/g, "&");
        str = str.replace(/&lt;/g, "<");
        str = str.replace(/&gt;/g, ">");

        return str;
    },

    truncate: function(numChars) {
        numChars = numChars || 100;

        var str = this.toString();

        if (this.length > numChars) {
            str = this.substring(0, numChars - 3); // minus length of "..."
            i = str.lastIndexOf(".");

            if (i !== -1) {
                str = str.substring(0, i + 1);
            }

            str += "...";
        }

        return str;
    }
});


})(jQuery);

// vim: set et:
