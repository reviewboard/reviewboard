import {
    type EventsHash,
    spina,
} from '@beanbag/spina';

import {
    Actions,
    ReviewRequest,
    UserSession,
} from 'reviewboard/common';
import { OverlayView } from 'reviewboard/ui';

import { type ReviewRequestEditor } from '../models/reviewRequestEditorModel';
import { type ReviewRequestEditorView } from './reviewRequestEditorView';
import { ReviewDialogView } from './reviewDialogView';
import { UploadAttachmentView } from './uploadAttachmentView';


/**
 * The view to manage the archive menu.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ArchiveMenuActionView extends Actions.MenuActionView {
    static events: EventsHash = {
        'click': 'onClick',
        'focusout': 'onFocusOut',
        'keydown': 'onKeyDown',
        'keyup': 'onKeyUp',
        'mouseenter': 'openMenu',
        'mouseleave': 'closeMenu',
        'touchend .menu-title': 'onTouchEnd',
    };

    /**********************
     * Instance variables *
     **********************/

    /** Whether the activation key is pressed. */
    #activationKeyDown = false;

    /** The review request */
    #reviewRequest: ReviewRequest;

    /**
     * Render the view (the first time).
     */
    protected onInitialRender() {
        super.onInitialRender();

        const page = RB.PageManager.getPage();
        const reviewRequestEditor = page.getReviewRequestEditorModel();
        const reviewRequest = reviewRequestEditor.get('reviewRequest');
        this.#reviewRequest = reviewRequest;

        this.listenTo(reviewRequest, 'change:visibility', this.render);
    }

    /**
     * Render or re-render the view.
     */
    protected onRender() {
        super.onRender();

        const visibility = this.#reviewRequest.get('visibility');
        const visible = (visibility === ReviewRequest.VISIBILITY_VISIBLE);

        this.$('.rb-icon')
            .toggleClass('rb-icon-archive-on', !visible)
            .toggleClass('rb-icon-archive-off', visible)
            .attr('title',
                  visible
                  ? _`Unarchive review request`
                  : _`Archive review request`);
    }

    /**
     * Handle a click event.
     *
     * Args:
     *     e (MouseEvent):
     *         The event object.
     */
    protected async onClick(e: MouseEvent) {
        if (!this.#activationKeyDown) {
            e.preventDefault();
            e.stopPropagation();

            const visibility = this.#reviewRequest.get('visibility');
            const visible = (
                visibility === ReviewRequest.VISIBILITY_VISIBLE);
            const collection = (
                visibility === ReviewRequest.VISIBILITY_MUTED
                ? UserSession.instance.mutedReviewRequests
                : UserSession.instance.archivedReviewRequests)

            if (visible) {
                await collection.addImmediately(this.#reviewRequest);
            } else {
                await collection.removeImmediately(this.#reviewRequest);
            }

            this.#reviewRequest.set('visibility',
                                    visible
                                    ? ReviewRequest.VISIBILITY_ARCHIVED
                                    : ReviewRequest.VISIBILITY_VISIBLE);
        }
    }

    /**
     * Handle a keydown event.
     *
     * We use this to track whether the activation keys are being pressed
     * (Enter or Space) so that we can avoid triggering the default click
     * behavior, which is a shortcut to the archive functionality.
     *
     * Args:
     *     e (KeyboardEvent):
     *         The event object.
     */
    protected onKeyDown(e: KeyboardEvent) {
        if (e.key === 'Enter' || e.key === 'Space') {
            this.#activationKeyDown = true;
        }

        super.onKeyDown(e);
    }

    /**
     * Handle a keyup event.
     */
    protected onKeyUp() {
        this.#activationKeyDown = false;
    }

    /**
     * Handle a touchstart event.
     */
    protected onTouchStart() {
        // Do nothing.
    }

    /**
     * Handle a touchend event.
     *
     * Args:
     *     e (TouchEvent):
     *         The event object.
     */
    protected onTouchEnd(e: TouchEvent) {
        /*
         * With mouse clicks, we allow users to click on the menu header itself
         * as a shortcut for just choosing archive, but with touch events we
         * can't do that because then the user would never have access to the
         * menu.
         *
         * If we allow this event to run the default handler, it would also
         * give us a 'click' event after.
         */
        e.preventDefault();

        if (this.menu.isOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
}


/**
 * Action view for the review menu.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ReviewMenuActionView extends Actions.MenuActionView {
    /**********************
     * Instance variables *
     **********************/

    /** The event overlay when the menu is shown in mobile mode. */
    #overlay: OverlayView = null;

    /**
     * Render the view.
     */
    protected onInitialRender() {
        super.onInitialRender();

        this.listenTo(this.menu, 'closing', this._removeOverlay);
    }

    /**
     * Handle a touchstart event.
     *
     * Args:
     *     e (TouchEvent):
     *         The touch event.
     */
    protected onTouchStart(e: TouchEvent) {
        super.onTouchStart(e);

        if (this.menu.isOpen) {
            if (!this.#overlay) {
                this.#overlay = new OverlayView();
                this.#overlay.$el.appendTo('body');

                this.listenTo(this.#overlay, 'click', () => {
                    this.closeMenu();
                });
            }
        }
    }

    /**
     * Position the menu.
     *
     * Version Added:
     *     7.0.3
     */
    protected positionMenu() {
        const $menuEl = this.menu.$el;

        if (RB.PageManager.getPage().inMobileMode) {
            /*
             * Make the review menu take up the full width of the screen
             * when on mobile.
             *
             * This needs to happen before the call to the parent class so
             * that the parent uses the updated width for the menu.
             */
            $menuEl.css({
                'text-wrap': 'wrap',
                width: $(window).width(),
            });
        } else {
            /* Use default styling on desktop. */
            $menuEl.css({
                'text-wrap': '',
                width: '',
            });
        }

        super.positionMenu();
    }

    /**
     * Remove the event overlay that's shown in mobile mode.
     *
     * Version Added:
     *     7.0.3
     */
    private _removeOverlay() {
        if (this.#overlay) {
            this.#overlay.remove();
            this.#overlay = null;
        }
    }
}
