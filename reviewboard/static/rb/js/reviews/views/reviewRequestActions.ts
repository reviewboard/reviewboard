import { spina } from '@beanbag/spina';

import { Actions } from 'reviewboard/common/actions';


/**
 * The view to manage the archive menu.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ArchiveMenuActionView extends Actions.MenuActionView {
    events = {
        'click': 'onClick',
        'focusout': 'onFocusOut',
        'keydown': 'onKeyDown',
        'keyup': 'onKeyUp',
        'mouseenter': 'openMenu',
        'mouseleave': 'closeMenu',
        'touchend': 'onTouchEnd',
    };

    /**********************
     * Instance variables *
     **********************/
    #activationKeyDown = false;
    #reviewRequest: RB.ReviewRequest;

    /**
     * Initialize the view.
     */
    initialize() {
        super.initialize();

        const page = RB.PageManager.getPage();
        const reviewRequestEditor = page.getReviewRequestEditorModel();
        this.#reviewRequest = reviewRequestEditor.get('reviewRequest');

        this.listenTo(this.#reviewRequest, 'change:visibility', this.render);
    }

    /**
     * Render the view.
     */
    onRender() {
        super.onRender();

        const visibility = this.#reviewRequest.get('visibility');
        const visible = (visibility === RB.ReviewRequest.VISIBILITY_VISIBLE);

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
                visibility === RB.ReviewRequest.VISIBILITY_VISIBLE);
            const collection = (
                visibility === RB.ReviewRequest.VISIBILITY_MUTED
                ? RB.UserSession.instance.mutedReviewRequests
                : RB.UserSession.instance.archivedReviewRequests)

            if (visible) {
                await collection.addImmediately(this.#reviewRequest);
            } else {
                await collection.removeImmediately(this.#reviewRequest);
            }

            this.#reviewRequest.set('visibility',
                                    visible
                                    ? RB.ReviewRequest.VISIBILITY_ARCHIVED
                                    : RB.ReviewRequest.VISIBILITY_VISIBLE);
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
 * Base class for archive views.
 *
 * Version Added:
 *     6.0
 */
@spina
abstract class BaseVisibilityActionView extends Actions.ActionView {
    events = {
        'click': '_toggle',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    collection: RB.BaseResource;

    /** The visibility type controlled by this action. */
    visibilityType = RB.ReviewRequest.VISIBILITY_ARCHIVED;

    #reviewRequest: RB.ReviewRequest;

    /**
     * Initialize the view.
     */
    initialize() {
        super.initialize();

        const page = RB.PageManager.getPage();
        const reviewRequestEditor = page.getReviewRequestEditorModel();
        this.#reviewRequest = reviewRequestEditor.get('reviewRequest');

        this.listenTo(this.#reviewRequest, 'change:visibility', this.render);
    }

    /**
     * Render the view.
     *
     * Returns:
     *     BaseVisibilityActionView:
     *     This object, for chaining.
     */
    onRender() {
        this.$('span').text(
            this.getLabel(this.#reviewRequest.get('visibility')));
    }

    /**
     * Return the label to use for the menu item.
     *
     * Args:
     *     visibility (number):
     *         The visibility state of the review request.
     *
     * Returns:
     *     string:
     *     The label to show based on the current visibility state.
     */
    abstract getLabel(
        visibility: number,
    ): string;

    /**
     * Toggle the archive state of the review request.
     *
     * Args:
     *     e (Event):
     *         The event that triggered the action.
     */
    private async _toggle(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        const visibility = this.#reviewRequest.get('visibility');
        const visible = (visibility !== this.visibilityType);

        if (visible) {
            await this.collection.addImmediately(this.#reviewRequest);
        } else {
            await this.collection.removeImmediately(this.#reviewRequest);
        }

        this.#reviewRequest.set('visibility',
                                visible
                                ? this.visibilityType
                                : RB.ReviewRequest.VISIBILITY_VISIBLE);
    }
}


/**
 * Archive action view.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ArchiveActionView extends BaseVisibilityActionView {
    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    collection = RB.UserSession.instance.archivedReviewRequests;

    /**
     * Return the label to use for the menu item.
     *
     * Args:
     *     visibility (number):
     *         The visibility state of the review request.
     *
     * Returns:
     *     string:
     *     The text to use for the label.
     */
    getLabel(
        visibility: number,
    ): string {
        return visibility === this.visibilityType
               ? _`Unarchive`
               : _`Archive`;
    }
}


/**
 * Mute action view.
 *
 * Version Added:
 *     6.0
 */
@spina
export class MuteActionView extends BaseVisibilityActionView {
    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    collection = RB.UserSession.instance.mutedReviewRequests;

    /** The visibility type controlled by this action. */
    visibilityType = RB.ReviewRequest.VISIBILITY_MUTED;

    /**
     * Return the label to use for the menu item.
     *
     * Args:
     *     visibility (number):
     *         The visibility state of the review request.
     *
     * Returns:
     *     string:
     *     The text to use for the label.
     */
    getLabel(
        visibility: number,
    ): string {
        return visibility === this.visibilityType
               ? _`Unmute`
               : _`Mute`;
    }
}


/**
 * Action view to create a blank review.
 *
 * Version Added:
 *     6.0
 */
@spina
export class CreateReviewActionView extends Actions.ActionView {
    events = {
        'click': '_onClick',
    };

    /**********************
     * Instance variables *
     **********************/

    #pendingReview;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options to pass through to the parent class.
     */
    initialize(options: object) {
        super.initialize(options);

        const page = RB.PageManager.getPage();
        this.#pendingReview = page.pendingReview;
    }

    /**
     * Render the action.
     *
     * Returns:
     *     CreateReviewActionView:
     *     This object, for chaining.
     */
    onInitialRender() {
        this.listenTo(this.#pendingReview, 'saved destroy sync', this.#update);
        this.#update();
    }

    /**
     * Update the visibility state of the action.
     *
     * This will show the action only when there's no existing pending review.
     */
    #update() {
        this.$el.parent().setVisible(this.#pendingReview.isNew());
    }

    /**
     * Handle a click on the action.
     *
     * Args:
     *     e (MouseEvent):
     *         The event.
     */
    private _onClick(e: MouseEvent) {
        e.stopPropagation();
        e.preventDefault();

        this.#pendingReview.save();
    }
}


/**
 * Action view to pop up the edit review dialog.
 *
 * Version Added:
 *     6.0
 */
@spina
export class EditReviewActionView extends Actions.ActionView {
    events = {
        'click': '_onClick',
    };

    /**********************
     * Instance variables *
     **********************/

    #pendingReview;
    #reviewRequestEditor;

    /**
     * Create the view.
     *
     * Args:
     *     options (object):
     *         Options to pass through to the parent class.
     */
    initialize(options: object) {
        super.initialize(options);

        const page = RB.PageManager.getPage();
        this.#pendingReview = page.pendingReview;
        this.#reviewRequestEditor = page.reviewRequestEditorView.model;
    }

    /**
     * Render the action.
     */
    onInitialRender() {
        this.listenTo(this.#pendingReview, 'saved destroy sync', this.#update);
        this.#update();
    }

    /**
     * Update the visibility state of the action.
     */
    #update() {
        this.$el.parent().setVisible(!this.#pendingReview.isNew());
    }

    /**
     * Handle a click on the action.
     *
     * Args:
     *     e (MouseEvent):
     *         The event.
     */
    private _onClick(e: MouseEvent) {
        e.stopPropagation();
        e.preventDefault();

        RB.ReviewDialogView.create({
            review: this.#pendingReview,
            reviewRequestEditor: this.#reviewRequestEditor,
        });
    }
}


/**
 * Action view to mark a review request as "Ship It".
 *
 * Version Added:
 *     6.0
 */
@spina
export class ShipItActionView extends RB.Actions.ActionView {
    events = {
        'click': '_onClick',
    };

    /**
     * Handle a click on the action.
     *
     * Args:
     *     e (MouseEvent):
     *         The event.
     */
    private _onClick(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();

        RB.PageManager.getPage().shipIt();
    }
}
