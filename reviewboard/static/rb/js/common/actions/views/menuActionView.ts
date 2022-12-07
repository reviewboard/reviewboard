import { spina } from '@beanbag/spina';

import { ActionView } from './actionView';


/**
 * Base class for menu actions.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MenuActionView extends ActionView {
    events = {
        'focusout': this.onFocusOut,
        'keydown': this.onKeyDown,
        'mouseenter': this.openMenu,
        'mouseleave': this.closeMenu,
    };

    /**********************
     * Instance variables *
     **********************/

    /** The menu view. */
    menu: RB.MenuView;

    /**
     * Render the view.
     */
    onInitialRender() {
        this.menu = new RB.MenuView({
            $controller: this.$el,
        });

        this.$el.append(this.menu.render().$el);

        const page = RB.PageManager.getPage();

        for (const childId of this.model.get('children')) {
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
}
