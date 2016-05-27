window.RB = {};


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
