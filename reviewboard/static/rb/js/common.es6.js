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


/*
 * Bug and user infoboxes. These are shown when hovering over links to users
 * and bugs.
 */
$.fn.infobox = function(id) {
    let $el = $(`.${id}`);

    if ($el.length === 0) {
        $el = $('<div/>')
            .addClass(id)
            .hide()
            .appendTo(document.body);
    }

    this.each(function() {
        const view = new RB.InfoboxView({
            $target: $(this),
            el: $el
        });

        view.render();
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
