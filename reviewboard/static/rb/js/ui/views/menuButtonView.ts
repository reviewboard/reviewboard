import { BaseView, EventsHash, spina } from '@beanbag/spina';

import {
    MenuItemOptions,
    MenuTransitionOptions,
    MenuType,
    MenuView,
} from './menuView';


/**
 * Options for the MenuButtonView.
 *
 * Version Added:
 *     6.0
 */
export interface MenuButtonViewOptions {
    /**
     * A descriptive label for the drop-down menu, for screen readers.
     *
     * This is only needed if a primary button was added. Otherwise, ``text``
     * is used as the label.
     */
    ariaMenuLabel?: string;

    /**
     * Whether there should be a primary button.
     *
     * If true, there will be an additional primary button separate from the
     * drop-down button.
     */
    hasPrimaryButton?: boolean;

    /**
     * The icon class to use for the drop-down icon.
     */
    menuIconClass?: string;

    /**
     * A list of menu items.
     *
     * Each will be passed to :js:meth:RB.MenuView.addItem` If not provided,
     * explicit items should be added to the menu.
     */
    menuItems?: MenuItemOptions[];

    /**
     * The type of menu to use.
     *
     * If provided, this must be one of :js:attr:`MenuType.Standard` or
     * :js:attr:`MenuType.Button`. If not provided, this will default to being
     * a standard menu.
     */
    menuType?: MenuType;

    /**
     * The handler for click events on the primary button.
     *
     * If set, this implies ``hasPrimaryButton: true``.
     */
    onPrimaryButtonClick?: { (eventObject: MouseEvent): void };

    /**
     * The text shown on the button.
     */
    text?: string;
}


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
 */
@spina
export class MenuButtonView<
    TModel extends (Backbone.Model | undefined) = Backbone.Model,
    TElement extends Element = HTMLElement,
    TExtraViewOptions = MenuButtonViewOptions
> extends BaseView<
    TModel,
    TElement,
    TExtraViewOptions
> {
    static className = 'rb-c-menu-button';

    static events: EventsHash = {
        'click .rb-c-menu-button__toggle': '_onToggleClick',
        'focusout': '_onFocusOut',
        'keydown .rb-c-menu-button__toggle': '_onToggleButtonKeyDown',
        'mouseenter .rb-c-menu-button__toggle': '_openMenu',
        'mouseleave': '_closeMenu',
    };

    private static template = _.template(dedent`
        <% if (hasPrimaryButton) { %>
         <div class="rb-c-button-group" role="group">
          <button class="rb-c-menu-button__primary rb-c-button"
                  type="button"><%- buttonText %></button>
          <button class="rb-c-menu-button__toggle rb-c-button"
                  id="<%- labelID %>"
                  type="button"
                  aria-label="<%- menuLabel %>">
           <span class="<%- menuIconClass %>"></span>
          </button>
         </div>
        <% } else { %>
         <button class="rb-c-button rb-c-menu-button__toggle"
                 id="<%- labelID %>"
                 type="button">
          <%- buttonText %>
          <span class="<%- menuIconClass %>"></span>
         </button>
        <% } %>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The primary button, if one is configured. */
    $primaryButton: JQuery = null;

    /** The menu associated with the button. */
    menu: MenuView = null;

    /**
     * The direction that the menu will open.
     *
     * This is public so unit tests can set it, but should otherwise not be
     * necessary outside of this class.
     */
    openDirection = 'down';

    #$dropDownButton: JQuery = null;
    #ariaMenuLabel: string;
    #buttonText: string;
    #hasPrimaryButton: boolean;
    #menuIconClass: string;
    #menuItems: MenuItemOptions[];
    #menuType: MenuType;
    #onPrimaryButtonClick: { (eventObject: MouseEvent): void };

    /**
     * Initialize the menu button.
     *
     * Args:
     *     options (MenuButtonViewOptions):
     *         Options for the view.
     */
    initialize(options: MenuButtonViewOptions) {
        this.#ariaMenuLabel = options.ariaMenuLabel || gettext('More options');
        this.#menuItems = options.menuItems || [];
        this.#menuType = options.menuType || MenuType.Standard;
        this.#menuIconClass = (options.menuIconClass ||
                               'rb-icon rb-icon-dropdown-arrow');
        this.#buttonText = options.text;
        this.#onPrimaryButtonClick = options.onPrimaryButtonClick;
        this.#hasPrimaryButton = (!!this.#onPrimaryButtonClick ||
                                  options.hasPrimaryButton);
    }

    /**
     * Remove the view from the DOM.
     *
     * Returns:
     *     MenuButtonView:
     *     This object, for chaining.
     */
    remove(): this {
        this.menu.remove();
        super.remove();

        return this;
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        const labelID = _.uniqueId('__rb-menubuttonview__label');

        this.$el
            .addClass(this.className)
            .attr('role', 'group')
            .html(MenuButtonView.template({
                buttonText: this.#buttonText,
                hasPrimaryButton: this.#hasPrimaryButton,
                labelID: labelID,
                menuIconClass: this.#menuIconClass,
                menuLabel: this.#ariaMenuLabel,
            }));

        if (this.#hasPrimaryButton) {
            this.$primaryButton = this.$('.rb-c-menu-button__primary')
                .on('click', this.#onPrimaryButtonClick.bind(this));
            console.assert(this.$primaryButton.length === 1);
        }

        this.#$dropDownButton = this.$('.rb-c-menu-button__toggle');
        console.assert(this.#$dropDownButton.length === 1);

        /* Create and populate the drop-down menu. */
        const menu = new MenuView({
            $controller: this.#$dropDownButton,
            ariaLabelledBy: labelID,
            type: this.#menuType,
        });
        menu.render();

        this.listenTo(menu, 'opening', () => {
            this.#$dropDownButton.addClass('js-hover');
            this.updateMenuPosition();
        });

        this.listenTo(menu, 'closing', () => {
            this.#$dropDownButton.removeClass('js-hover');
        });

        for (const item of this.#menuItems) {
            menu.addItem(item);
        }

        menu.$el.appendTo(this.$el);

        this.menu = menu;
    }

    /**
     * Position the drop-down menu above or below the button.
     *
     * This will attempt to determine whether there's enough space below
     * the button for the menu to fully appear. If there is not, then the
     * menu will appear above the button instead.
     *
     * The resulting direction will also impact the styling of the button and
     * menu, helping to create a connected appearance.
     *
     * This is public because unit tests need to be able to spy on it.
     */
    updateMenuPosition() {
        const $button = this.#$dropDownButton;
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

        this.openDirection = direction;

        this.$el.toggleClass('-opens-up', direction === 'up');
        this.menu.$el.css(direction === 'down' ? 'top' : 'bottom',
                          $button.innerHeight());
    }

    /**
     * Show the menu.
     *
     * Args:
     *     options (MenuTransitionOptions):
     *         Options to pass to :js:meth:`RB.MenuView.open`.
     */
    private _openMenu(options: MenuTransitionOptions) {
        this.menu.open(options);
    }

    /**
     * Close the menu.
     *
     * Args:
     *     options (MenuTransitionOptions):
     *         Options to pass to :js:meth:`RB.MenuView.close`.
     */
    private _closeMenu(options: MenuTransitionOptions) {
        this.menu.close(options);
    }

    /**
     * Handle a focus-out event.
     *
     * This will immediately hide the menu, if the newly-focused item is
     * not a child of this view.
     *
     * Args:
     *     evt (FocusEvent):
     *         The focus-in event.
     */
    private _onFocusOut(evt: FocusEvent) {
        evt.stopPropagation();

        /*
         * Only close the menu if focus has moved to something outside of
         * this component.
         */
        const currentTarget = evt.currentTarget as Element;

        if (!currentTarget.contains(evt.relatedTarget as Element)) {
            this._closeMenu({
                animate: false,
            });
        }
    }

    /**
     * Handle a keydown event.
     *
     * When the drop-down button has focus, this will take care of handling
     * keyboard-based navigation, allowing the menu to be opened or closed.
     * Opening the menu will transfer focus to the menu items.
     *
     * Args:
     *     evt (KeyboardEvent):
     *         The keydown event.
     */
    private _onToggleButtonKeyDown(evt: KeyboardEvent) {
        if (evt.key === 'ArrowDown' ||
            evt.key === 'ArrowUp' ||
            evt.key === 'Enter' ||
            evt.key === ' ') {
            this._openMenu({
                animate: false,
            });

            if (this.openDirection === 'up') {
                this.menu.focusLastItem();
            } else if (this.openDirection === 'down') {
                this.menu.focusFirstItem();
            }

            evt.stopPropagation();
            evt.preventDefault();
        } else if (evt.key === 'Escape') {
            this._closeMenu({
                animate: false,
            });

            evt.stopPropagation();
            evt.preventDefault();
        }
    }

    /**
     * Handle a click event on the dropdown toggle.
     *
     * Clicking on the dropdown toggle is not supposed to do anything,
     * since hovering it with the cursor is sufficient for opening the
     * alternatives menu. We handle the click and stop the event from
     * propagating so that the modal library doesn't interpret this as
     * an attempt to close the dialog.
     *
     * Args:
     *     evt (MouseEvent):
     *         The click event.
     */
    private _onToggleClick(evt: MouseEvent) {
        evt.stopPropagation();
        evt.preventDefault();
    }
}
