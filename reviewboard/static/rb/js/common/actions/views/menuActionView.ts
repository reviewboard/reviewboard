import { EventsHash, spina } from '@beanbag/spina';

import { MenuView } from 'reviewboard/ui';

import { MenuAction } from '../models/menuActionModel';
import { ActionView } from './actionView';


/**
 * Base class for menu actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MenuActionView<
    TModel extends MenuAction = MenuAction,
    TElement extends HTMLDivElement = HTMLDivElement,
    TExtraViewOptions extends object = object
> extends ActionView<TModel, TElement, TExtraViewOptions> {
    static events: EventsHash = {
        'focusout': 'onFocusOut',
        'keydown': 'onKeyDown',
        'mouseenter': 'openMenu',
        'mouseleave': 'closeMenu',
        'touchstart': 'onTouchStart',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The menu view. */
    menu: MenuView;

    /**
     * Render the view.
     */
    onInitialRender() {
        this.menu = new MenuView({
            $controller: this.$el,
        });

        this.$el.append(this.menu.render().$el);

        const page = RB.PageManager.getPage();

        for (const childId of this.model.get('children')) {
            if (childId === '--') {
                this.menu.addSeparator();
            } else {
                const childActionView = page.getActionView(childId);

                if (childActionView) {
                    this.menu.addItem({
                        $child: childActionView.$el,
                    });

                    if (childActionView.model.get('visible')) {
                        childActionView.$el.show();
                    }
                } else {
                    console.error('Unable to find action for %s', childId);
                }
            }
        }
    }

    /**
     * Open the menu.
     */
    protected openMenu() {
        if (this.menu.el.children.length > 0) {
            this.menu.open({ animate: true });
        }
    }

    /**
     * Close the menu.
     */
    protected closeMenu() {
        if (this.menu.el.children.length > 0) {
            this.menu.close({ animate: true });
        }
    }

    /**
     * Handle a focus-out event.
     *
     * If the keyboard focus has moved to something outside of the menu, close
     * it.
     *
     * Args:
     *     evt (FocusEvent):
     *         The event object.
     */
    protected onFocusOut(evt: FocusEvent) {
        evt.stopPropagation();

        /*
         * Only close the menu if the focus has moved to something outside of
         * this component.
         */
        const currentTarget = <Element>evt.currentTarget;

        if (!currentTarget.contains(<Element>evt.relatedTarget)) {
            this.menu.close({
                animate: false,
            });
        }
    }

    /**
     * Handle a key-down event.
     *
     * When the menu has focus, this will take care of handling keyboard
     * operations, allowing the menu to be opened or closed. Opening the menu
     * will transfer the focus to the menu items.
     *
     * Args:
     *     evt (KeyboardEvent):
     *         The keydown event.
     */
    protected onKeyDown(evt: KeyboardEvent) {
        if (evt.key === ' ' ||
            evt.key === 'ArrowDown' ||
            evt.key === 'ArrowUp' ||
            evt.key === 'Enter') {
            this.menu.open({
                animate: false,
            });
            this.menu.focusFirstItem();

            evt.stopPropagation();
            evt.preventDefault();
        } else if (evt.key === 'Escape') {
            this.menu.close({
                animate: false,
            });

            evt.stopPropagation();
            evt.preventDefault();
        }
    }

    /**
     * Handle a touchstart event.
     *
     * Args:
     *     e (TouchEvent):
     *         The touch event.
     */
    protected onTouchStart(e: TouchEvent) {
        e.stopPropagation();
        e.preventDefault();

        if (this.menu.isOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
}


/**
 * Base class for an action within a menu.
 *
 * This handles event registration for the click and touch events in order to
 * behave properly on both desktop and mobile.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MenuItemActionView extends ActionView {
    static events: EventsHash = {
        'click': '_onClick',
        'touchstart': '_onTouchStart',
    };

    /**
     * Handle a click event.
     *
     * Args:
     *     e (MouseEvent):
     *         The event.
     */
    protected _onClick(e: MouseEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.activate();
    }

    /**
     * Handle a touchstart event.
     */
    protected _onTouchStart() {
        /*
         * For touch events, we explicitly let the event bubble up so that the
         * parent menu can close.
         */
        this.activate();
    }

    /**
     * Activate the action.
     */
    activate() {
        // This is expected to be overridden by subclasses.
    }
}
