/**
 * A button that offers a drop-down menu when clicked.
 *
 * Menu buttons have the appearance of a button with a drop-down indicator.
 * When clicked, they display a menu either below or above the button
 * (depending on their position on the screen).
 *
 * They may also be grouped into two buttons, one primary button (which works
 * as a standard, independent button) and one drop-down button (which works
 * as above, but just shows the drop-down indicator).
 *
 * Version Added:
 *     4.0
 *
 * Attributes:
 *     $primaryButton (jQuery):
 *         The primary button, if one is configured separate from the drop-down
 *         button.
 *
 *     menu (RB.MenuView):
 *         The menu associated with the button.
 */
RB.MenuButtonView = Backbone.View.extend({
    className: 'rb-c-menu-button',

    events: {
        'mouseenter .rb-c-menu-button__toggle': '_openMenu',
        'focusout': '_onFocusOut',
        'mouseleave': '_closeMenu',
        'keydown .rb-c-menu-button__toggle': '_onToggleButtonKeyDown',
    },

    template: _.template(dedent`
        <% if (hasPrimaryButton) { %>
         <div class="rb-c-button-group" role="group">
          <button class="rb-c-menu-button__primary rb-c-button"
                  type="button"><%- buttonText %></button>
          <button class="rb-c-menu-button__toggle rb-c-button"
                  id="<%- labelID %>"
                  type="button"
                  aria-label="<%- menuLabel %>">
           <span class="rb-icon rb-icon-dropdown-arrow"></span>
          </button>
         </div>
        <% } else { %>
         <button class="rb-c-button rb-c-menu-button__toggle"
                 id="<%- labelID %>"
                 type="button">
          <%- buttonText %>
          <span class="rb-icon rb-icon-dropdown-arrow"></span>
         </button>
        <% } %>
    `),

    /**
     * Initialize the menu button.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     ariaMenuLabel (string, optional):
     *         A descriptive label for the drop-down menu, for screen readers.
     *         This is only needed if a primary button was added. Otherwise,
     *         ``text`` is used as the label.
     *
     *     hasPrimaryButton (boolean, optional):
     *         Whether there should be a primary button separate from the
     *         drop-down button.
     *
     *     menuItems (Array of object, optional):
     *         A list of menu items. Each will be passed to
     *         :js:meth:`RB.MenuView.prototype.addItem`. If not provided,
     *         explicit items should be added to the menu.
     *
     *     menuType (number, optional):
     *         The type of menu to use. If provided, this must be one of
     *         :js:attr:`RB.MenuView.TYPE_STANDARD_MENU` or
     *         :js:attr:`RB.MenuView.TYPE_BUTTON_MENU`. If not provided,
     *         this will be a standard menu.
     *
     *     onPrimaryButtonClick (function, optional):
     *         The handler for click events on the primary button. If set,
     *         this implies ``hasPrimaryButton: true``.
     *
     *     text (string):
     *         The text shown on the button.
     */
    initialize(options={}) {
        this._ariaMenuLabel = options.ariaMenuLabel || gettext('More options');
        this._menuItems = options.menuItems || [];
        this._menuType = options.menuType || RB.MenuView.TYPE_STANDARD_MENU;
        this._buttonText = options.text;
        this._buttonOnClick = options.onPrimaryButtonClick;
        this._hasPrimaryButton = (!!this._buttonOnClick ||
                                  options.hasPrimaryButton);

        this.menu = null;
        this.$primaryButton = null;

        this._$buttonGroup = null;
        this._openDirection = 'down';
    },

    /**
     * Remove the view from the DOM.
     */
    remove() {
        this.menu.remove();

        Backbone.View.prototype.remove.call(this);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.MenuButtonView:
     *     This object, for chaining.
     */
    render() {
        const labelID = _.uniqueId('__rb-menubuttonview__label');
        const hasPrimaryButton = this._hasPrimaryButton;

        this.$el
            .addClass(this.className)
            .attr('role', 'group')
            .html(this.template({
                buttonText: this._buttonText,
                hasPrimaryButton: hasPrimaryButton,
                labelID: labelID,
                menuLabel: this._ariaMenuLabel,
            }));

        if (hasPrimaryButton) {
            this.$primaryButton = this.$('.rb-c-menu-button__primary')
                .on('click', this._buttonOnClick.bind(this));
            console.assert(this.$primaryButton.length === 1);
        }

        this._$dropDownButton = this.$('.rb-c-menu-button__toggle');
        console.assert(this._$dropDownButton.length === 1);

        /* Create and populate the drop-down menu. */
        const menu = new RB.MenuView({
            ariaLabelledBy: labelID,
            $controller: this._$dropDownButton,
            type: this._menuType,
        });
        menu.render();

        this.listenTo(menu, 'opening', () => {
            this._$dropDownButton.addClass('js-hover');
            this._updateMenuPosition();
        });

        this.listenTo(menu, 'closing', () => {
            this._$dropDownButton.removeClass('js-hover');
        });

        for (let i = 0; i < this._menuItems.length; i++) {
            menu.addItem(this._menuItems[i]);
        }

        menu.$el.appendTo(this.$el);

        this.menu = menu;

        return this;
    },

    /**
     * Position the drop-down menu above or below the button.
     *
     * This will attempt to determine whether there's enough space below
     * the button for the menu to fully appear. If there is not, then the
     * menu will appear above the button instead.
     *
     * The resulting direction will also impact the styling of the button and
     * menu, helping to create a connected appearance.
     */
    _updateMenuPosition() {
        const $button = this._$dropDownButton;
        const buttonY1 = $button.offset().top;
        const buttonY2 = buttonY1 + $button.innerHeight();
        const pageY1 = window.pageYOffset;
        const pageY2 = window.pageYOffset + window.innerHeight;
        let direction;

        if (pageY1 >= buttonY1) {
            /*
             * The button is at least partially off-screen, above the current
             * viewport. Drop the menu down.
             */
            direction = 'down';
        } else if (pageY2 <= buttonY2) {
            /*
             * The button is at least partially off-screen, below the current
             * viewport. Drop the menu up.
             */
            direction = 'up';
        } else {
            const menuHeight = this.menu.$el.outerHeight();

            /*
             * The button is fully on-screen. See if there's enough room below
             * the button for the menu.
             */
            if (pageY2 >= buttonY2 + menuHeight) {
                /* The menu can fully fit below the button. */
                direction = 'down';
            } else {
                /* The menu cannot fully fit below the button. */
                direction = 'up';
            }
        }

        this._openDirection = direction;

        this.$el.toggleClass('-opens-up', direction === 'up');
        this.menu.$el.css(direction === 'down' ? 'top' : 'bottom',
                          $button.innerHeight());
    },

    /**
     * Show the menu.
     *
     * Args:
     *     options (object):
     *         Options to pass to :js:meth:`RB.MenuView.prototype.open`.
     */
    _openMenu(options) {
        this.menu.open(options);
    },

    /**
     * Close the menu.
     *
     * Args:
     *     options (object):
     *         Options to pass to :js:meth:`RB.MenuView.prototype.close`.
     */
    _closeMenu(options) {
        this.menu.close(options);
    },

    /**
     * Handle a focus-out event.
     *
     * This will immediately hide the menu, if the newly-focused item is
     * not a child of this view.
     *
     * Args:
     *     evt (jQuery.Event):
     *         The focus-in event.
     */
    _onFocusOut(evt) {
        evt.stopPropagation();

        /*
         * Only close the menu if focus has moved to something outside of
         * this component.
         */
        if (!evt.currentTarget.contains(evt.relatedTarget)) {
            this._closeMenu({
                animate: false,
            });
        }
    },

    /**
     * Handle a keydown event.
     *
     * When the drop-down button has focus, this will take care of handling
     * keyboard-based navigation, allowing the menu to be opened or closed.
     * Opening the menu will transfer focus to the menu items.
     *
     * Args:
     *     evt (jQuery.Event):
     *         The keydown event.
     *
     * Returns:
     *     boolean:
     *     ``True`` if the event was handled explicitly by the menu button.
     *     ``False`` if it should bubble up or invoke default behavior.
     */
    _onToggleButtonKeyDown(evt) {
        switch (evt.which) {
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.RETURN:
            case $.ui.keyCode.SPACE:
            case $.ui.keyCode.UP:
                this._openMenu({
                    animate: false,
                });

                if (this._openDirection === 'up') {
                    this.menu.focusLastItem();
                } else if (this._openDirection === 'down') {
                    this.menu.focusFirstItem();
                }

                return false;

            case $.ui.keyCode.ESCAPE:
                this._closeMenu({
                    animate: false,
                });
                return false;
        }
    },
});
