/**
 * Displays a modal dialog box with content and buttons.
 *
 * The dialog box can have a title and a list of buttons. It can be shown
 * or hidden on demand.
 *
 * This view can either be subclassed (with the contents in render() being
 * used to populate the dialog), or it can be tied to an element that already
 * contains content.
 *
 * Under the hood, this is a wrapper around $.modalBox.
 *
 * Subclasses of DialogView can specify a default title, list of buttons,
 * and default options for modalBox. The title and buttons can be overridden
 * when constructing the view by passing them as options.
 */
RB.DialogView = Backbone.View.extend({
    /** The default title to show for the dialog. */
    title: null,

    /** The default list of buttons to show for the dialog. */
    buttons: [],

    /** Default options to pass to $.modalBox(). */
    defaultOptions: {},

    /**
     * Initialize the view.
     *
     * The available options are 'title' and 'buttons'.
     *
     * options.title specifies the title shown on the dialog, overriding
     * the title on the class.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     title (string):
     *         The title for the dialog.
     *
     *     buttons (Array of object):
     *         A list of buttons. Each button may have the following keys:
     *
     *         label (string):
     *             The label for the button.
     *
     *         primary (boolean):
     *             Whether the button is the primary action for the dialog.
     *
     *         danger (boolean):
     *             Whether the button performs a dangerous operation (such as
     *             deleting user data).
     *
     *         onClick (function or string):
     *             The handler to invoke when the button is clicked. If set to
     *             a function, that function will be called. If set to a
     *             string, it will resolve to a function with that name on the
     *             DialogView instance. If unset, the dialog will simply close
     *             without invoking any actions.
     *
     *             The callback function can return ``false`` to prevent the
     *             dialog from being closed.
     */
    initialize(options={}) {
        this.options = options;

        if (options.title) {
            this.title = options.title;
        }

        if (options.buttons) {
            this.buttons = options.buttons;
        }

        this.visible = false;
    },

    /**
     * Render the content of the dialog.
     *
     * By default, this does nothing. Subclasses can override to render
     * custom content.
     *
     * Note that this will be called every time the dialog is shown, not just
     * when it's first constructed.
     *
     * Returns:
     *     RB.DialogView:
     *     This object, for chaining.
     */
    render() {
        return this;
    },

    /**
     * Show the dialog.
     */
    show() {
        if (!this.visible) {
            this.render();

            this.$el.modalBox(_.defaults({
                title: _.result(this, 'title'),
                buttons: this._getButtons(),
                destroy: () => this.visible = false,
            }, this.options, this.defaultOptions));

            this.visible = true;
        }
    },

    /**
     * Hide the dialog.
     */
    hide() {
        if (this.visible) {
            this.$el.modalBox('destroy');
        }
    },

    /**
     * Remove the dialog from the DOM.
     */
    remove() {
        this.hide();

        _super(this).remove.call(this);
    },

    /**
     * Return a list of button elements for rendering.
     *
     * This will take the button list that was provided when constructing
     * the dialog and turn each into an element.
     *
     * Returns:
     *     Array of jQuery:
     *     An array of button elements.
     */
    _getButtons() {
        return this.buttons.map(buttonInfo => {
            const $button = $('<input type="button" />')
                .val(buttonInfo.label)
                .toggleClass('primary', !!buttonInfo.primary)
                .toggleClass('danger', !!buttonInfo.danger);

            if (buttonInfo.onClick) {
                if (_.isFunction(buttonInfo.onClick)) {
                    $button.click(buttonInfo.onClick);
                } else {
                    $button.click(this[buttonInfo.onClick].bind(this));
                }
            }

            return $button;
        });
    }
});
