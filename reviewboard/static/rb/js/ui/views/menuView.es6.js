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
RB.MenuView = Backbone.View.extend({
    className: 'rb-c-menu',

    events: {
        'keydown': '_onKeyDown',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object, optional):
     *         Options for the view.
     *
     * Option Args:
     *     $controller (jQuery, optional):
     *         The jQuery-wrapped element that's responsible for opening and
     *         closing this menu.
     *
     *     ariaLabel (string, optional):
     *         An explicit descriptive ARIA label to set on the menu, to aid
     *         screen readers.
     *
     *     ariaLabelledBy (string, optional):
     *         The ID of an element that contains an existing descriptive
     *         ARIA label to use for the menu, to aid screen readers. If
     *         provided, this takes precedence over ``ariaLabel``.
     *
     *     type (number, optional):
     *         The type of menu. If provided, this must be one of
     *         :js:attr:`RB.MenuView.TYPE_BUTTON_MENU` or
     *         :js:attr:`RB.MenuView.TYPE_STANDARD_MENU`. If not provided,
     *         this will be a standard menu.
     */
    initialize(options={}) {
        if (options.type === undefined ||
            options.type === RB.MenuView.TYPE_STANDARD_MENU) {
            this.type = RB.MenuView.TYPE_STANDARD_MENU;
        } else if (options.type === RB.MenuView.TYPE_BUTTON_MENU) {
            this.type = RB.MenuView.TYPE_BUTTON_MENU;
        } else {
            console.error('The provided RB.MenuView type (%s) is not ' +
                          'supported. Defaulting to a standard menu.',
                          options.type);
            this.type = RB.MenuView.TYPE_STANDARD_MENU;
        }

        if (!this.id) {
            this.id = _.uniqueId('__rb-menu');
        }

        this.$controller = options.$controller;
        this.isOpen = false;

        this._ariaLabelledBy = options.ariaLabelledBy;
        this._ariaLabel = options.ariaLabel;
        this._activeItemIndex = null;
        this._activeItemEl = null;
    },

    /**
     * Render the menu.
     *
     * This will set up the elements for the menu and associate it with the
     * controller.
     *
     * Returns:
     *     RB.MenuView:
     *     This menu, for chaining.
     */
    render() {
        this.$el
            .attr({
                id: this.id,
                tabindex: '-1',
            });

        if (this.type === RB.MenuView.TYPE_BUTTON_MENU) {
            this.$el.addClass('rb-c-button-group -is-vertical');
        }

        /* Set ARIA attributes on these and on the controller. */
        this.$el.attr('role', 'menu');

        if (this._ariaLabelledBy) {
            this.$el.attr('aria-labelledby', this._ariaLabelledBy);
        } else if (this._ariaLabel) {
            this.$el.attr('aria-label', this._ariaLabel);
        }

        if (this.$controller) {
            this.$controller.attr({
                'aria-controls': this.id,
                'aria-expanded': 'false',
                'aria-haspopup': 'true',
            });
        }

        return this;
    },

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
     * Args:
     *     options (object, optional):
     *         Options for the menu item.
     *
     * Option Args:
     *     id (string, optional):
     *         A DOM element ID to assign to the menu item.
     *
     *     onClick (function, optional):
     *         A function to call when the menu item is clicked.
     *
     *     text (string, optional):
     *         Explicit text to use for the menu item.
     *
     * Returns:
     *     jQuery:
     *     The jQuery-wrapped element for the menu item.
     */
    addItem(options={}) {
        let $el;

        if (this.type === RB.MenuView.TYPE_BUTTON_MENU) {
            $el = $(
                '<button class="rb-c-menu__item rb-c-button" type="button">'
            );
        } else if (this.type === RB.MenuView.TYPE_STANDARD_MENU) {
            $el = $('<div class="rb-c-menu__item">');
        } else {
            /* This shouldn't be able to be reached. */
            console.assert(false, 'RB.MenuView type is not a supported type.');
        }

        if (options.text !== undefined) {
            $el.text(options.text);
        }

        if (options.onClick !== undefined) {
            $el.on('click', options.onClick);
        }

        $el
            .attr({
                role: 'menuitem',
                tabindex: '-1',
            })
            .on('mousemove', this._onMenuItemMouseMove.bind(this))
            .appendTo(this.el);

        return $el;
    },

    /**
     * Open the menu.
     *
     * This will show the menu on the screen. Before it's shown, an ``opening``
     * event will be emitted. Once shown (and after the animation finishes),
     * the ``opened`` event will be emitted.
     *
     * Args:
     *     options (object, optional):
     *         Options to use when opening the menu.
     *
     * Option Args:
     *     animate (boolean, optional):
     *         Whether to animate the menu. This defaults to ``true``.
     */
    open(options) {
        this._setOpened(true, options);
    },

    /**
     * Close the menu.
     *
     * This will hide the menu. Before it's hidden, a ``closing`` event will
     * be emitted. Once hidden (and after the animation finishes), the
     * ``closed`` event will be emitted.
     *
     * Args:
     *     options (object, optional):
     *         Options to use when closing the menu.
     *
     * Option Args:
     *     animate (boolean, optional):
     *         Whether to animate the menu. This defaults to ``true``.
     */
    close(options) {
        this._setOpened(false, options);
    },

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
            this._focusItem(0);
        }
    },

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
            this._focusItem(numChildren - 1);
        }
    },

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
     *     options (object, optional):
     *         The options to use when setting state.
     *
     * Option Args:
     *     triggerEvents (boolean, optional):
     *         Whether to trigger events from a state change. This defaults
     *         to ``true``.
     */
    _setOpened(opened, options={}) {
        if (this.isOpen === opened) {
            return;
        }

        this._activeItemIndex = null;
        this._activeItemEl = null;

        if (options.animate === false) {
            this.$el.addClass('js-no-animation');
            _.defer(() => this.$el.removeClass('js-no-animation'));
        }

        this.isOpen = opened;

        const triggerEvents = (options.triggerEvents !== false);

        if (triggerEvents) {
            this.trigger(opened ? 'opening' : 'closing');
        }

        if (opened) {
            this.$el.addClass('-is-open');
        } else {
            this.$el.removeClass('-is-open');
        }

        if (this.$controller) {
            this.$controller.attr('aria-expanded', opened);
        }

        if (triggerEvents) {
            this.trigger(opened ? 'opened' : 'closed');
        }
    },

    /**
     * Focus an item at the specified index.
     *
     * Args:
     *     index (number):
     *         The index of the menu item to focus. This is expected to be
     *         a valid index in the list of items.
     */
    _focusItem(index) {
        this._activeItemIndex = index;
        this._activeItemEl = this.el.children[index];
        this._activeItemEl.focus();
    },

    /**
     * Focus the previous item in the menu.
     *
     * This takes care of wrapping the focus around to the end of the menu,
     * if focus was already on the first item.
     */
    _focusPreviousItem() {
        if (this._activeItemIndex === null) {
            this.focusFirstItem();
        } else {
            let index = this._activeItemIndex - 1;

            if (index < 0) {
                index = this.el.children.length - 1;
            }

            this._focusItem(index);
        }
    },

    /**
     * Focus the next item in the menu.
     *
     * This takes care of wrapping the focus around to the beginning of
     * the menu, if focus was already on the last item.
     */
    _focusNextItem() {
        if (this._activeItemIndex === null) {
            this.focusFirstItem();
        } else {
            let index = this._activeItemIndex + 1;

            if (index >= this.el.children.length) {
                index = 0;
            }

            this._focusItem(index);
        }
    },

    /**
     * Handle a keydown event.
     *
     * When the menu or a menu item has focus, this will take care of
     * handling keyboard-based navigation, allowing the menu to be closed,
     * or the focused menu item to be changed or activated.
     *
     * Args:
     *     evt (jQuery.Event):
     *         The keydown event.
     *
     * Returns:
     *     boolean:
     *     ``True`` if the event was handled explicitly by the menu.
     *     ``False`` if it should bubble up or invoke default behavior.
     */
    _onKeyDown(evt) {
        switch (evt.which) {
            case $.ui.keyCode.ENTER:
                /* Activate any selected item. */
                $(this._activeItemEl).triggerHandler('click');
                return false;

            case $.ui.keyCode.ESCAPE:
            case $.ui.keyCode.TAB:
                /* Close the menu and bring focus back to the controller. */
                if (this.$controller) {
                    this.$controller.focus();
                }

                this.close({
                    animate: false,
                });
                return false;

            case $.ui.keyCode.UP:
                /* Move up an item. */
                this._focusPreviousItem();
                return false;

            case $.ui.keyCode.DOWN:
                /* Move down an item. */
                this._focusNextItem();
                return false;

            case $.ui.keyCode.HOME:
            case $.ui.keyCode.PAGE_UP:
                /* Move to the first item. */
                this.focusFirstItem();
                return false;

            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_DOWN:
                /* Move to the last item. */
                this.focusLastItem();
                return false;
        }
    },

    /**
     * Handle mousemove events on a menu item.
     *
     * This will move the focus to the menu item.
     *
     * Args:
     *     evt (jQuery.Event):
     *         The mousemove event.
     */
    _onMenuItemMouseMove(evt) {
        const targetEl = evt.currentTarget;

        if (targetEl === this._activeItemEl) {
            /* The mouse has moved but the item hasn't changed. */
            return;
        }

        const menuItems = this.el.children;

        for (let i = 0; i < menuItems.length; i++) {
            if (menuItems[i] === targetEl) {
                this._focusItem(i);
                break;
            }
        }
    },
}, {
    /** Standard drop-down menus. */
    TYPE_STANDARD_MENU: 1,

    /** Button-based menus. */
    TYPE_BUTTON_MENU: 2,
});
