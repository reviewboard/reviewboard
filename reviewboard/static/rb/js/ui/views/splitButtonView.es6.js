/**
 * A SplitButtonView is a split button with a drop down which, when hovered
 * over, will drop down (or up) a list of alternative options.
 *
 * If the view is to be removed, the remove() method must be called as this
 * view adds elements to the DOM that are not under its root element.
 *
 * Deprecated:
 *     4.0:
 *     Consumers should use :js:class:`RB.MenuButtonView` instead.
 */
RB.SplitButtonView = RB.MenuButtonView.extend({
    /**
     * Set up all initial state and event listeners.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     ariaMenuLabel (string):
     *         A descriptive label for the drop-down menu, for screen readers.
     *
     *     text (string):
     *         The text shown on the button.
     *
     *     click (function or string):
     *         The handler for click events on the primary button.
     *
     *     id (string):
     *         The DOM ID to use for the primary button.
     *
     *     alternatives (Array of object):
     *         A list of alternative buttons. Each item includes ``text``,
     *         ``click``, and ``id`` keys which are equivalent to the options
     *         for the primary button.
     */
    initialize(options={}) {
        RB.MenuButtonView.prototype.initialize.call(this, {
            ariaMenuLabel: options.ariaMenuLabel,
            hasPrimaryButton: true,
            menuType: RB.MenuView.TYPE_BUTTON_MENU,
            onPrimaryButtonClick: options.click,
            text: options.text,
        });

        this._primaryButtonID = options.id;
        this._alternatives = options.alternatives;
    },

    /**
     * Render the split button.
     *
     * Returns:
     *     RB.SplitButtonView:
     *     This object, for chaining.
     */
    render() {
        RB.MenuButtonView.prototype.render.call(this);

        if (this._primaryButtonID) {
            this.$primaryButton.attr('id', this._primaryButtonID);
        }

        const menu = this.menu;

        this._alternatives.forEach(alt => {
            const $item = menu.addItem({
                text: alt.text,
                onClick: alt.click,
            });

            if (alt.id) {
                $item.attr('id', alt.id);
            }
        });

        return this;
    },
});
