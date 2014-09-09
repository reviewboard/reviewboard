/*
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
 *
 * The list of buttons contain objects with the following keys:
 *
 *     * label: The label for the button.
 *
 *     * primary: A boolean indicating if the button is the primary button
 *                on the dialog.
 *
 *     * danger: A boolean indicating if the button performs a dangerous
 *               operation (such as deleting or reverting).
 *
 *     * onClick: The handler to invoke when the button is clicked. If set to
 *                a function, that function will be invoked. If a string, it
 *                will map to a function on the DialogView instance. If unset,
 *                it will simply close the dialog without invoking a function.
 *
 *                The callback function can return 'false' to prevent the
 *                dialog from being closed.
 */
RB.DialogView = Backbone.View.extend({
    /* The default title to show for the dialog. */
    title: null,

    /* The default list of buttons to show for the dialog. */
    buttons: [],

    /* Default options to pass to $.modalBox(). */
    defaultOptions: {},

    /*
     * Initializes the view.
     *
     * The available options are 'title' and 'buttons'.
     *
     * options.title specifies the title shown on the dialog, overriding
     * the title on the class.
     */
    initialize: function(options) {
        options = options || {};

        this.options = options;

        if (options.title) {
            this.title = options.title;
        }

        if (options.buttons) {
            this.buttons = options.buttons;
        }

        this.visible = false;
    },

    /*
     * Renders the content of the dialog.
     *
     * By default, this does nothing. Subclasses can override to render
     * custom content.
     *
     * Note that this will be called every time the dialog is shown, not just
     * when it's first constructed.
     */
    render: function() {
        return this;
    },

    /*
     * Shows the dialog.
     */
    show: function() {
        if (!this.visible) {
            this.render();

            this.$el.modalBox(_.defaults({
                title: _.result(this, 'title'),
                buttons: this._getButtons(),
                destroy: function() {
                    this.visible = false;
                }
            }, this.options, this.defaultOptions));

            this.visible = true;
        }
    },

    /*
     * Hides the dialog.
     */
    hide: function() {
        if (this.visible) {
            this.$el.modalBox('destroy');
        }
    },

    /*
     * Removes the dialog from the DOM.
     */
    remove: function() {
        this.hide();

        _super(this).remove.call(this);
    },

    /*
     * Returns a list of buttons elements for rendering.
     *
     * This will take the button list that was provided when constructing
     * the dialog and turn each into an element.
     */
    _getButtons: function() {
        var buttons = [];

        _.each(this.buttons, function(buttonInfo) {
            var $button = $('<input type="button"/>')
                .val(buttonInfo.label);

            if (buttonInfo.primary) {
                $button.addClass('primary');
            }

            if (buttonInfo.danger) {
                $button.addClass('danger');
            }

            if (buttonInfo.onClick) {
                if (_.isFunction(buttonInfo.onClick)) {
                    $button.click(buttonInfo.onClick);
                } else {
                    $button.click(_.bind(this[buttonInfo.onClick], this));
                }
            }

            buttons.push($button);
        }, this);

        return buttons;
    }
});
