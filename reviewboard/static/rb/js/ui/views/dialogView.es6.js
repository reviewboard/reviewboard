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

    /** The default body to show in the dialog. */
    body: null,

    /** The default list of buttons to show for the dialog. */
    buttons: [],

    /** Default options to pass to $.modalBox(). */
    defaultOptions: {},

    /** Events handled by the view. */
    events: {
        'submit form': '_onFormSubmit',
    },

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
     *     body (string or function, optional):
     *         The body to show in the dialog.
     *
     *     buttons (Array of object):
     *         A list of buttons. Each button may have the following keys:
     *
     *         danger (boolean, optional):
     *             Whether the button performs a dangerous operation (such as
     *             deleting user data).
     *
     *         disabled (boolean, optional):
     *             Whether the button is disabled.
     *
     *         id (string, required):
     *             The ID for the button.
     *
     *         label (string, required):
     *             The label for the button.
     *
     *         onClick (function or string, optional):
     *             The handler to invoke when the button is clicked. If set to
     *             a function, that function will be called. If set to a
     *             string, it will resolve to a function with that name on the
     *             DialogView instance. If unset, the dialog will simply close
     *             without invoking any actions.
     *
     *             The callback function can return ``false`` to prevent the
     *             dialog from being closed.
     *
     *         primary (boolean, optional):
     *             Whether the button is the primary action for the dialog.
     *
     *     title (string):
     *         The title for the dialog.
     */
    initialize(options={}) {
        this.options = options;

        if (options.title) {
            this.title = options.title;
        }

        if (options.body) {
            this.body = options.body;
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
            const body = _.result(this, 'body');

            if (body) {
                this.$el.append(body);
            }

            this._makeButtons();
            this.render();

            this.$el.modalBox(_.defaults({
                title: _.result(this, 'title'),
                buttons: this.$buttonsList,
                destroy: () => this.visible = false,
            }, this.options, this.defaultOptions));

            this.$el.closest('.modalbox-inner')
                .on('keydown', this._onDialogKeyDown.bind(this));

            this.visible = true;
        }
    },

    /**
     * Hide the dialog.
     */
    hide() {
        if (this.visible) {
            /*
             * The jQuery-UI widget can self-destruct in some cases depending
             * on how events bubble. If that's the case, we skip an extra
             * destroy call because otherwise we get errors on the console.
             */
            if (this.$el.data('uiModalBox')) {
                this.$el.modalBox('destroy');
            }

            this.visible = false;
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
     * the dialog and turn each into an element. The elements are also saved to
     * a map to allow child components to access the buttons.
     *
     * Returns:
     *     Array of jQuery:
     *     An array of button elements.
     */
    _makeButtons() {
        this.$buttonsMap = {};
        this.$buttonsList = this.buttons.map(buttonInfo => {
            const $button = $('<input type="button" />')
                .val(buttonInfo.label)
                .attr('id', buttonInfo.id);

            if (buttonInfo.class) {
                $button.addClass(buttonInfo.class);
            }

            if (buttonInfo.disabled) {
                $button.attr('disabled', true);
            }

            if (buttonInfo.primary) {
                $button.addClass('primary');
                this._$primaryButton = $button;
            }

            if (buttonInfo.danger) {
                $button.addClass('danger');
            }

            if (buttonInfo.onClick) {
                if (_.isFunction(buttonInfo.onClick)) {
                    $button.click(buttonInfo.onClick);
                } else {
                    $button.click(this[buttonInfo.onClick].bind(this));
                }
            }

            this.$buttonsMap[buttonInfo.id] = $button;

            return $button;
        });
    },

    /**
     * Handle form submission events for the dialog.
     *
     * This will trigger the primary button if the form in the dialog does not
     * have an explicit action.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onFormSubmit(e) {
        if (!$(e.target).attr('action')) {
            e.preventDefault();
            e.stopPropagation();

            if (this._$primaryButton) {
                this._$primaryButton[0].click();
            }
        }
    },

    /**
     * Handle keydown events for the dialog.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onDialogKeyDown(e) {
        if (e.which === $.ui.keyCode.ESCAPE) {
            e.stopPropagation();
            e.preventDefault();

            this.hide();
        }
    },
});
