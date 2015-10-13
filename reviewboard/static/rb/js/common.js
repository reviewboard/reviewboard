RB = {};


/*
 * Registers handlers for the toggleable stars.
 *
 * These will listen for when a star is clicked, which will toggle
 * whether an object is starred. Right now, we support "reviewrequests"
 * and "groups" types. Loads parameters from data attributes on the element.
 * Attaches at the document level so it applies to future stars.
 *
 * @param {string} object-type  The type used for constructing the path.
 * @param {string} object-id    The object ID to star/unstar.
 * @param {bool}   starred      The default value.
 */
function registerToggleStar() {
    $(document).on('click', '.star', function() {
        var self = $(this),
            obj = self.data("rb.obj"),
            type,
            objid,
            on,
            altTitle;

        if (!obj) {
            type = self.attr("data-object-type");
            objid = self.attr("data-object-id");

            if (type === "reviewrequests") {
                obj = new RB.ReviewRequest({
                    id: objid
                });
            } else if (type === "groups") {
                obj = new RB.ReviewGroup({
                    id: objid
                });
            } else {
                self.remove();
                return;
            }
        }

        on = (parseInt(self.attr("data-starred"), 10) === 1) ? 0 : 1;
        obj.setStarred(on);
        self.data("rb.obj", obj);

        altTitle = on ? gettext("Starred") : gettext("Click to star");

        if (on) {
            self
                .removeClass('rb-icon-star-off')
                .addClass('rb-icon-star-on');
        } else {
            self
                .removeClass('rb-icon-star-on')
                .addClass('rb-icon-star-off');
        }

        self.attr({
            'data-starred': on,
            title: altTitle
        });

        return false;
    });
}

var gInfoBoxCache = {};

/*
 * Bug and user infoboxes. These are shown when hovering over links to users
 * and bugs.
 *
 * The infobox is displayed after a 1 second delay.
 */
$.fn.infobox = function(id) {
    var POPUP_DELAY_MS = 500,
        HIDE_DELAY_MS = 300,
        OFFSET_LEFT = -20,
        OFFSET_TOP = 10,
        $infobox = $('#' + id);

    if ($infobox.length === 0) {
        $infobox = $('<div/>')
            .attr('id', id)
            .hide();
        $(document.body).append($infobox);
    }

    function showInfobox(url, $target) {
        $infobox
            .empty()
            .html(gInfoBoxCache[url])
            .positionToSide($target, {
                side: 'tb',
                xOffset: OFFSET_LEFT,
                yDistance: OFFSET_TOP,
                fitOnScreen: true
            })
            .fadeIn();

        $infobox.find('.gravatar')
            .retinaGravatar();
    }

    function fetchInfobox(url, $target) {
        if (!gInfoBoxCache[url]) {
            $.get(url, function(responseText) {
                gInfoBoxCache[url] = responseText;
            }).done(function() {
                showInfobox(url, $target);
            });
        } else {
            showInfobox(url, $target);
        }
    }

    return this.each(function() {
        var $target = $(this),
            timeout = null,
            url = $target.attr('href') + 'infobox/';

        $target.on('mouseover', function() {
            timeout = setTimeout(function() {
                fetchInfobox(url, $target);
            }, POPUP_DELAY_MS);
        });

        $([$target[0], $infobox[0]]).on({
            mouseover: function() {
                if ($infobox.is(':visible')) {
                    clearTimeout(timeout);
                }
            },
            mouseout: function() {
                clearTimeout(timeout);

                if ($infobox.is(':visible')) {
                    timeout = setTimeout(function() {
                        $infobox.fadeOut();
                    }, HIDE_DELAY_MS);
                }
            }
        });
    });
};

$.fn.user_infobox = function() {
    $(this).infobox('user_infobox');
    return this;
};

$.fn.bug_infobox = function() {
    $(this).infobox('bug_infobox');
    return this;
};


$(document).ready(function() {
    $('.user').user_infobox();
    $('.bug').bug_infobox();
    $('time.timesince').timesince();

    $('.gravatar').retinaGravatar();

    registerToggleStar();
});

// vim: set et:sw=4:
