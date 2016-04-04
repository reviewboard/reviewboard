window.RB = {};


/**
 * Register handlers for the toggleable stars.
 *
 * These will listen for when a star is clicked, which will toggle
 * whether an object is starred. Right now, we support 'reviewrequests'
 * and 'groups' types. Loads parameters from data attributes on the element.
 * Attaches at the document level so it applies to future stars.
 *
 * @param {string} object-type  The type used for constructing the path.
 * @param {string} object-id    The object ID to star/unstar.
 * @param {bool}   starred      The default value.
 */
function registerToggleStar() {
    $(document).on('click', '.star', function() {
        const $el = $(this);
        let obj = $el.data('rb.obj');

        if (!obj) {
            const type = $el.attr('data-object-type'),
                  objid = $el.attr('data-object-id');

            if (type === 'reviewrequests') {
                obj = new RB.ReviewRequest({
                    id: objid
                });
            } else if (type === 'groups') {
                obj = new RB.ReviewGroup({
                    id: objid
                });
            } else {
                $el.remove();
                return;
            }
        }

        const on = (parseInt($el.attr('data-starred'), 10) !== 1);
        obj.setStarred(on);

        $el
            .toggleClass('rb-icon-star-on', on)
            .toggleClass('rb-icon-star-off', !on)
            .data('rb.obj', obj)
            .attr({
                'data-starred': on ? 1 : 0,
                title: on ? gettext('Starred') : gettext('Click to star')
            });

        return false;
    });
}


const gInfoBoxCache = {};


/*
 * Bug and user infoboxes. These are shown when hovering over links to users
 * and bugs.
 *
 * The infobox is displayed after a 1 second delay.
 */
$.fn.infobox = function(id) {
    const POPUP_DELAY_MS = 500,
          HIDE_DELAY_MS = 300,
          OFFSET_LEFT = -20,
          OFFSET_TOP = 10;

    let $infobox = $(`#${id}`);

    if ($infobox.length === 0) {
        $infobox = $('<div/>')
            .attr('id', id)
            .hide()
            .appendTo(document.body);
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

        $infobox.find('.avatar')
            .retinaAvatar();
    }

    function fetchInfobox(url, $target) {
        if (!gInfoBoxCache[url]) {
            $.get(url, responseText => { gInfoBoxCache[url] = responseText; })
                .done(() => showInfobox(url, $target));
        } else {
            showInfobox(url, $target);
        }
    }

    return this.each(function() {
        const $target = $(this),
              url = `${$target.attr('href')}infobox/`;
        let timeout = null;

        $target.on('mouseover', function() {
            timeout = setTimeout(() => fetchInfobox(url, $target),
                                 POPUP_DELAY_MS);
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
                    timeout = setTimeout(() => $infobox.fadeOut(),
                                         HIDE_DELAY_MS);
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

    $('.avatar').retinaAvatar();

    registerToggleStar();
});

// vim: set et:sw=4:
