/**
 * A view for managing state on a form.
 *
 * This provides some standard behavior for setting up form widgets and
 * handling collapsable fieldsets.
 */
RB.FormView = Backbone.View.extend({
    events: {
        'click .rb-c-form-fieldset__toggle': '_onToggleFieldSetClicked',
    },

    /**
     * Handle the showing or collapsing of a fieldset.
     *
     * This will set the appropriate state on the fieldset to show or hide
     * the content.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event on the Show/Hide button.
     */
    _onToggleFieldSetClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        const $toggle = $(e.target);
        const $fieldset = $toggle.closest('.rb-c-form-fieldset');

        if ($fieldset.hasClass('-is-collapsed')) {
            $fieldset.removeClass('-is-collapsed');
            $toggle.text(gettext('(Hide)'));
        } else {
            $fieldset.addClass('-is-collapsed');
            $toggle.text(gettext('(Show)'));
        }
    },
});
