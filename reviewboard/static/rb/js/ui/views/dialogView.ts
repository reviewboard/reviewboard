/**
 * Displays a modal dialog box with content and buttons.
 */

import {
    type EventsHash,
    type Result,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * Information on a button in the dialog.
 *
 * Version Added:
 *     8.0
 */
export interface DialogButtonInfo {
    /** The class to apply to the button element. */
    class?: string;

    /** Whether the button should have the "danger" class. */
    danger?: boolean;

    /** Whether the button is disabled. */
    disabled?: boolean;

    /** The ID to use for the button element. */
    id: string;

    /** The label for the button. */
    label: string;

    /**
     * The handler to invoke when the button is clicked.
     *
     * If set to a function, that function will be called. If set to a string,
     * it will resolve to a function with that name on the DialogView instance.
     * If unset, the dialog will simply close without invoking any actions.
     *
     * The callback function can return ``false`` to prevent the dialog from
     * being closed.
     */
    onClick?: string | JQuery.TypeEventHandler<HTMLElement, null, HTMLElement,
                                               HTMLElement, 'click'>;

    /** Whether the button is the primary action for the dialog. */
    primary?: boolean;
}


/**
 * Options for the DialogView.
 *
 * Version Added:
 *     8.0
 */
export interface DialogViewOptions {
    /** The body to show in the dialog. */
    body?: Result<string>;

    /** A list of buttons. */
    buttons?: DialogButtonInfo[];

    /** The title for the dialog. */
    title?: Result<string>;
}


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
 *
 * Deprecated:
 *     8.0:
 *     This view has been deprecated in favor of the Dialog component from
 *     @beanbag/ink.
 */
@spina({
    prototypeAttrs: ['title', 'body', 'buttons', 'defaultOptions'],
})
export class DialogView<
    TModel extends (Backbone.Model | undefined) = undefined,
    TElement extends Element = HTMLElement,
    TExtraViewOptions extends DialogViewOptions = DialogViewOptions,
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    /** The default title to show for the dialog. */
    static title: Result<string> | null = null;
    title: Result<string> | null;

    /** The default body to show in the dialog. */
    static body: Result<string> | null = null;
    body: Result<string> | null;

    /** The default list of buttons to show for the dialog. */
    static buttons: DialogButtonInfo[] = [];
    buttons: DialogButtonInfo[];

    /** Default options to pass to $.modalBox(). */
    static defaultOptions: unknown = {};
    defaultOptions: unknown;

    /** Events handled by the view. */
    static events: EventsHash = {
        'submit form': '_onFormSubmit',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The saved options for the view. */
    options: DialogViewOptions;

    /** Whether the dialog is currently visible. */
    visible = false;

    /** A mapping from button ID to the button element. */
    $buttonsMap: Record<string, JQuery> = {};

    /** A list of the button elements. */
    $buttonsList: JQuery[];

    /** The primary button, if one is specified. */
    protected _$primaryButton: JQuery;

    /**
     * Initialize the view.
     *
     * The available options are 'title' and 'buttons'.
     *
     * options.title specifies the title shown on the dialog, overriding
     * the title on the class.
     *
     * Args:
     *     options (DialogViewOptions):
     *         Options for view construction.
     */
    initialize(options: DialogViewOptions = {}) {
        console.warn(dedent`
            RB.DialogView is deprecated and will be removed in Review Board
            9.0. Any code that uses it should be ported to use Ink.Dialog from
            @beanbag/ink.`);

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
    }

    /**
     * Show the dialog.
     *
     * Returns:
     *     DialogView:
     *     This object, for chaining.
     */
    show(): this {
        if (!this.visible) {
            const body = _.result(this, 'body');

            if (body) {
                this.$el.append(body);
            }

            this._makeButtons();
            this.render();

            this.$el.modalBox(_.defaults({
                buttons: this.$buttonsList,
                destroy: () => this.visible = false,
                title: _.result(this, 'title'),
            }, this.options, this.defaultOptions));

            this.$el.closest('.modalbox-inner')
                .on('keydown', this._onDialogKeyDown.bind(this));

            this.visible = true;
        }

        return this;
    }

    /**
     * Hide the dialog.
     *
     * Returns:
     *     DialogView:
     *     This object, for chaining.
     */
    hide(): this {
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

        return this;
    }

    /**
     * Remove the dialog from the DOM.
     *
     * Returns:
     *     DialogView:
     *     This object, for chaining.
     */
    remove(): this {
        this.hide();
        super.remove();

        return this;
    }

    /**
     * Return a list of button elements for rendering.
     *
     * This will take the button list that was provided when constructing
     * the dialog and turn each into an element. The elements are also saved to
     * a map to allow child components to access the buttons.
     */
    _makeButtons() {
        this.$buttonsList = this.buttons.map(buttonInfo => {
            const buttonAttrs = {
                id: buttonInfo.id,
            };

            if (buttonInfo.class) {
                buttonAttrs.class = buttonInfo.class;
            }

            if (buttonInfo.disabled) {
                buttonAttrs.disabled = true;
            }

            if (buttonInfo.primary) {
                buttonAttrs.type = 'primary';
            } else if (buttonInfo.danger) {
                buttonAttrs.type = 'danger';
            }

            if (buttonInfo.onClick) {
                if (typeof buttonInfo.onClick === 'function') {
                    buttonAttrs.onClick = buttonInfo.onClick;
                } else {
                    buttonAttrs.onClick = this[buttonInfo.onClick].bind(this);
                }
            }

            const $button = $(Ink.paintComponent(
                'Ink.Button',
                buttonAttrs,
                buttonInfo.label));

            this.$buttonsMap[buttonInfo.id] = $button;

            if (buttonInfo.primary) {
                this._$primaryButton = $button;
            }

            return $button;
        });
    }

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
    _onFormSubmit(e: Event) {
        if (!$(e.target).attr('action')) {
            e.preventDefault();
            e.stopPropagation();

            if (this._$primaryButton) {
                this._$primaryButton[0].click();
            }
        }
    }

    /**
     * Handle keydown events for the dialog.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onDialogKeyDown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            e.stopPropagation();
            e.preventDefault();

            this.hide();
        }
    }
}
