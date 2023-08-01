import { BaseView, EventsHash, spina } from '@beanbag/spina';


/**
 * Definitions for the type of menus.
 *
 * Version Added:
 *     6.0
 */
export enum MenuType {
    Standard = 1,
    Button = 2,
}


/**
 * Options for the MenuView.
 *
 * Version Added:
 *     6.0
 */
interface MenuViewOptions {
    /**
     * An explicit descriptive ARIA label to set on the menu.
     *
     * This is used to aid screen readers in case the text of the element is
     * insufficient.
     */
    ariaLabel?: string;

    /**
     * The ID of an element that contains an existing descriptive ARIA label.
     *
     * This will be used to set the labeled-by element to use for the menu,
     * to aid screen readers. If provided, this takes precedence over
     * ``ariaLabel``.
     */
    ariaLabelledBy?: string;

    /** The element that's responsible for opening and closing this menu. */
    $controller?: JQuery;

    /**
     * The type of menu.
     *
     * If not provided, the menu will be a standard menu. */
    type?: MenuType;
}


/**
 * Options for menu transitions.
 *
 * Version Added:
 *     6.0
 */
export interface MenuTransitionOptions {
    /**
     * Whether to animate the menu.
     *
     * If unspecified, defaults to ``true``.
     */
    animate?: boolean;

    /**
     * Whether to trigger events from a state change.
     *
     * If unspecified, defaults to ``true``.
     */
    triggerEvents?: boolean;
}


/**
 * Info about a menu item.
 *
 * Version Added:
 *     6.0
 */
export interface MenuItemOptions {
    /**
     * An element to use for the child.
     *
     * If specified, this takes priority over ``text``. This element will
     * be reparented into the menu.
     *
     * Version Added:
     *     6.0
     */
    $child?: JQuery;

    /**
     * A DOM element ID to assign to the menu item.
     *
     * Version Added:
     *     6.0
     */
    id?: string;

    /**
     * Whether to insert the new action at the beginning rather than the end.
     *
     * Version Added:
     *     6.0
     */
    prepend?: boolean;

    /**
     * Explicit text to use for the menu item.
     */
    text?: string;

    /**
     * A function to call when the menu item is clicked.
     */
    onClick?: { (eventObject: MouseEvent): void };
}


/**
 * Options for adding separators.
 *
 * Version Added:
 *     6.0
 */
export interface MenuSeparatorOptions {
    /**
     * Whether to add the separator at the beginning rather than the end.
     */
    prepend?: boolean;
}


/**
 * A standard implementation of drop-down menus.
 *
 * This can be used to create and populate a standard drop-down menu or a
 * button menu (where each menu item is a button). It handles animating the
 * opening and closing of the menu, applying ARIA attributes for accessibility,
 * and handling keyboard-based navigation.
 *
 * Menus are (optionally) associated with a controller element, which is the
 * button or element responsible for opening and closing the menu. Like the
 * menu itself, the appropriate ARIA attributes will be set on the element to
 * help screen readers associate it with the menu.
 *
 * Version Added:
 *     4.0
 *
 * Attributes:
 *     $controller (jQuery):
 *         The jQuery-wrapped element that controls the display of this menu.
 *
 *     isOpen (boolean):
 *         The current menu open state.
 *
 *     type (number):
 *         The configured type of menu. This will be one of
 *         :js:attr:`RB.MenuView.TYPE_BUTTON_MENU` or
 *         :js:attr:`RB.MenuView.TYPE_STANDARD_MENU`.
 */
@spina
export class MenuView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    MenuViewOptions
> {
    /*
     * These are here for legacy use and will be removed in Review Board 7.0.
     * Callers should use the MenuType enum.
     */
    static TYPE_STANDARD_MENU = MenuType.Standard;
    static TYPE_BUTTON_MENU = MenuType.Button;

    static className = 'rb-c-menu';
    static events: EventsHash = {
        'keydown': '_onKeyDown',
        'touchstart': '_onTouchStart',
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * The jQuery-wrapped element that controls the display of this menu.
     */
    $controller: JQuery = null;

    /**
     * Whether the menu is currently open.
     */
    isOpen = false;

    /**
     * The configured type of menu.
     */
    type: MenuType;

    #ariaLabelledBy: string;
    #ariaLabel: string;
    #activeItemIndex: number = null;
    #activeItemEl: HTMLElement = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (MenuViewOptions, optional):
     *         Options for the view.
     */
    initialize(options: MenuViewOptions = {}) {
        super.initialize(options);

        if (options.type === undefined ||
            options.type === MenuType.Standard) {
            this.type = MenuType.Standard;
        } else if (options.type === MenuType.Button) {
            this.type = MenuType.Button;
        } else {
            console.error('The provided RB.MenuView type (%s) is not ' +
                          'supported. Defaulting to a standard menu.',
                          options.type);
            this.type = MenuType.Standard;
        }

        if (!this.id) {
            this.id = _.uniqueId('__rb-menu');
        }

        this.$controller = options.$controller;

        this.#ariaLabelledBy = options.ariaLabelledBy;
        this.#ariaLabel = options.ariaLabel;
    }

    /**
     * Render the menu.
     *
     * This will set up the elements for the menu and associate it with the
     * controller.
     */
    onInitialRender() {
        this.$el
            .attr({
                id: this.id,
                tabindex: '-1',
            });

        if (this.type === MenuType.Button) {
            this.$el.addClass('rb-c-button-group -is-vertical');
        }

        /* Set ARIA attributes on these and on the controller. */
        this.$el.attr('role', 'menu');

        if (this.#ariaLabelledBy) {
            this.$el.attr('aria-labelledby', this.#ariaLabelledBy);
        } else if (this.#ariaLabel) {
            this.$el.attr('aria-label', this.#ariaLabel);
        }

        if (this.$controller) {
            this.$controller.attr({
                'aria-controls': this.id,
                'aria-expanded': 'false',
                'aria-haspopup': 'true',
            });
        }
    }

    /**
     * Add an item to the menu.
     *
     * This appends an item to the bottom of the menu. It can append an
     * explicit element (if one was already created), or it can build a new
     * item appropriate for the type of menu.
     *
     * In either case, this can assign a DOM element ID to the menu item,
     * assign a click event handler, and will set ARIA roles.
     *
     * Version Changed:
     *     6.0:
     *     * Added the $child option argument.
     *     * Added the ``id`` option arg.
     *     * Added the ''prepend`` option arg.
     *
     * Args:
     *     options (MenuItemOptions, optional):
     *         Options for the menu item.
     *
     * Returns:
     *     jQuery:
     *     The jQuery-wrapped element for the menu item.
     */
    addItem(
        options: MenuItemOptions = {},
    ): JQuery {
        let $el;

        if (this.type === MenuType.Button) {
            $el = $(
                '<button class="rb-c-menu__item rb-c-button" type="button">'
            );
        } else if (this.type === MenuType.Standard) {
            $el = $('<div class="rb-c-menu__item">');
        } else {
            /* This shouldn't be able to be reached. */
            console.assert(false, 'RB.MenuView type is not a supported type.');
        }

        if (options.$child !== undefined) {
            options.$child.appendTo($el);
        } else if (options.text !== undefined) {
            $el.text(options.text);
        }

        if (options.onClick !== undefined) {
            $el.on('click', options.onClick);
        }

        if (options.id !== undefined) {
            $el.attr('id', options.id);
        }

        $el
            .attr({
                role: 'menuitem',
                tabindex: '-1',
            })
            .on('mousemove', e => this.#onMenuItemMouseMove(e));

        if (options.prepend) {
            $el.prependTo(this.el);
        } else {
            $el.appendTo(this.el);
        }

        return $el;
    }

    /**
     * Add a separator to the menu.
     *
     * Version Added:
     *     6.0
     *
     * Returns:
     *     jQuery:
     *     The jQuery-wrapped element for the separator.
     */
    addSeparator(
        options: MenuSeparatorOptions = {},
    ): JQuery {
        const $el = $('<div class="rb-c-menu__separator" role="separator">');

        if (options.prepend) {
            $el.prependTo(this.el);
        } else {
            $el.appendTo(this.el);
        }

        return $el;
    }

    /**
     * Clear all the menu items.
     */
    clearItems() {
        this.$('.rb-c-menu__item').remove();
    }

    /**
     * Open the menu.
     *
     * This will show the menu on the screen. Before it's shown, an ``opening``
     * event will be emitted. Once shown (and after the animation finishes),
     * the ``opened`` event will be emitted.
     *
     * Args:
     *     options (MenuTransitionOptions, optional):
     *         Options to use when opening the menu.
     */
    open(options: MenuTransitionOptions = {}) {
        this.#setOpened(true, options);
    }

    /**
     * Close the menu.
     *
     * This will hide the menu. Before it's hidden, a ``closing`` event will
     * be emitted. Once hidden (and after the animation finishes), the
     * ``closed`` event will be emitted.
     *
     * Args:
     *     options (MenuTransitionOptions, optional):
     *         Options to use when closing the menu.
     */
    close(options: MenuTransitionOptions = {}) {
        this.#setOpened(false, options);
    }

    /**
     * Focus the first item in the menu.
     *
     * This should be used by callers when programmatically displaying the
     * menu (such as a result of keyboard input), when showing the menu below
     * the controller.
     *
     * Once focused, arrow keys can be used to navigate the menu.
     */
    focusFirstItem() {
        if (this.el.children.length > 0) {
            this.focusItem(0);
        }
    }

    /**
     * Focus the last item in the menu.
     *
     * This should be used by callers when programmatically displaying the
     * menu (such as a result of keyboard input), when showing the menu above
     * the controller.
     *
     * Once focused, arrow keys can be used to navigate the menu.
     */
    focusLastItem() {
        const numChildren = this.el.children.length;

        if (numChildren > 0) {
            this.focusItem(numChildren - 1);
        }
    }

    /**
     * Set the menu's open/closed state.
     *
     * This takes care of emitting the opening/opened/closing/closed events,
     * setting active item states, setting the classes or display states, and
     * setting appropriate ARIA attributes on the controller.
     *
     * Args:
     *     opened (boolean):
     *         Whether the menu is set to opened.
     *
     *     options (MenuTransitionOptions, optional):
     *         The options to use when setting state.
     */
    #setOpened(
        opened: boolean,
        options: MenuTransitionOptions = {},
    ) {
        if (this.isOpen === opened) {
            return;
        }

        this.#activeItemIndex = null;
        this.#activeItemEl = null;

        if (options.animate === false) {
            this.$el.addClass('js-no-animation');
            _.defer(() => this.$el.removeClass('js-no-animation'));
        }

        this.isOpen = opened;

        const triggerEvents = (options.triggerEvents !== false);

        if (triggerEvents) {
            this.trigger(opened ? 'opening' : 'closing');
        }

        this.$el.toggleClass('-is-open', opened);

        if (this.$controller) {
            this.$controller
                .toggleClass('-is-open', opened)
                .attr('aria-expanded', opened ? 'true' : 'false');
        }

        if (triggerEvents) {
            this.trigger(opened ? 'opened' : 'closed');
        }
    }

    /**
     * Focus an item at the specified index.
     *
     * Args:
     *     index (number):
     *         The index of the menu item to focus. This is expected to be
     *         a valid index in the list of items.
     */
    focusItem(index) {
        this.#activeItemIndex = index;
        this.#activeItemEl = this.el.children[index] as HTMLElement;
        this.#activeItemEl.focus();
    }

    /**
     * Focus the previous item in the menu.
     *
     * This takes care of wrapping the focus around to the end of the menu,
     * if focus was already on the first item.
     */
    #focusPreviousItem() {
        if (this.#activeItemIndex === null) {
            this.focusFirstItem();
        } else {
            let index = this.#activeItemIndex - 1;

            if (index < 0) {
                index = this.el.children.length - 1;
            }

            this.focusItem(index);
        }
    }

    /**
     * Focus the next item in the menu.
     *
     * This takes care of wrapping the focus around to the beginning of
     * the menu, if focus was already on the last item.
     */
    #focusNextItem() {
        if (this.#activeItemIndex === null) {
            this.focusFirstItem();
        } else {
            let index = this.#activeItemIndex + 1;

            if (index >= this.el.children.length) {
                index = 0;
            }

            this.focusItem(index);
        }
    }

    /**
     * Handle a keydown event.
     *
     * When the menu or a menu item has focus, this will take care of
     * handling keyboard-based navigation, allowing the menu to be closed,
     * or the focused menu item to be changed or activated.
     *
     * Args:
     *     evt (KeyboardEvent):
     *         The keydown event.
     */
    private _onKeyDown(evt: KeyboardEvent) {
        let preventDefault = true;

        if (evt.key === 'Enter') {
            /* Activate any selected item. */
            $(this.#activeItemEl).triggerHandler('click');
        } else if (evt.key === 'Escape' ||
                   evt.key === 'Tab') {
            /* Close the menu and bring focus back to the controller. */
            if (this.$controller) {
                this.$controller.focus();
            }

            this.close({
                animate: false,
            });
        } else if (evt.key === 'ArrowUp') {
            /* Move up an item. */
            this.#focusPreviousItem();
        } else if (evt.key === 'ArrowDown') {
            /* Move down an item. */
            this.#focusNextItem();
        } else if (evt.key === 'Home' ||
                   evt.key === 'PageUp') {
            /* Move to the first item. */
            this.focusFirstItem();
        } else if (evt.key === 'End' ||
                   evt.key === 'PageDown') {
            /* Move to the last item. */
            this.focusLastItem();
        } else {
            /* Let the default event handlers run. */
            preventDefault = false;
        }

        if (preventDefault) {
            evt.stopPropagation();
            evt.preventDefault();
        }
    }

    /**
     * Handle mousemove events on a menu item.
     *
     * This will move the focus to the menu item.
     *
     * Args:
     *     evt (MouseEvent):
     *         The mousemove event.
     */
    #onMenuItemMouseMove(evt: MouseEvent) {
        const targetEl = evt.currentTarget;

        if (targetEl === this.#activeItemEl) {
            /* The mouse has moved but the item hasn't changed. */
            return;
        }

        const menuItems = this.el.children;
        const itemIndex = _.indexOf(menuItems, targetEl as Element);

        if (itemIndex !== -1) {
            this.focusItem(itemIndex);
        }
    }

    /**
     * Return the active item index.
     *
     * This is for use with unit tests.
     *
     * Returns:
     *     number:
     *     The active item index.
     */
    get _activeItemIndex(): number {
        return this.#activeItemIndex;
    }
}
