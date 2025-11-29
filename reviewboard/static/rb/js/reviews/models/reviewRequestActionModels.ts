/**
 * Built-in review request action implementations.
 *
 * Version Added:
 *     7.1
 */

import {
    spina,
} from '@beanbag/spina';
import {
    type ButtonView,
    craft,
    paint,
} from '@beanbag/ink';

import {
    type Review,
    Actions,
    ReviewRequest,
} from 'reviewboard/common';
import {
    type StoredItems,
    UserSession,
} from 'reviewboard/common/models/userSessionModel';
import {
    type ReviewRequestEditorView,
} from '../views/reviewRequestEditorView';
import { ReviewDialogView } from '../views/reviewDialogView';


/**
 * Base class for archive actions.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.BaseVisibilityActionView`.
 */
abstract class BaseVisibilityAction extends Actions.Action {
    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    targetCollection: StoredItems;

    /** The visibility type controlled by this action. */
    visibilityType = ReviewRequest.VISIBILITY_ARCHIVED;

    /**
     * Initialize the view.
     */
    initialize() {
        super.initialize();

        const page = RB.PageManager.getPage();
        const reviewRequestEditor = page.getReviewRequestEditorModel();
        const reviewRequest = reviewRequestEditor.get('reviewRequest');

        this.listenTo(reviewRequest, 'change:visibility',
                      this.#onReviewRequestVisibilityChanged);
        this.#onReviewRequestVisibilityChanged(
            reviewRequest,
            reviewRequest.get('visibility'));
    }

    /**
     * Return the label to use for the action.
     *
     * Args:
     *     visibility (number):
     *         The visibility state of the review request.
     *
     * Returns:
     *     string:
     *     The text to use for the label.
     */
    abstract getLabelForVisibility(
        visibility: number,
    ): string;

    /**
     * Toggle the archive state of the review request.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditor = page.getReviewRequestEditorModel();
        const reviewRequest = reviewRequestEditor.get('reviewRequest');

        const visibility = reviewRequest.get('visibility');
        const visible = (visibility !== this.visibilityType);

        if (visible) {
            await this.targetCollection.addImmediately(reviewRequest);
        } else {
            await this.targetCollection.removeImmediately(reviewRequest);
        }

        reviewRequest.set('visibility',
                          visible
                          ? this.visibilityType
                          : ReviewRequest.VISIBILITY_VISIBLE);
    }

    /**
     * Handle changes to the review request's visibility.
     *
     * This will update the label based on the review request's visibility
     * state.
     *
     * Args:
     *     model (RB.ReviewRequest):
     *         The review request being managed.
     *
     *     visibility (number):
     *         The review request's visibility.
     */
    #onReviewRequestVisibilityChanged(
        model: ReviewRequest,
        visibility: number,
    ) {
        this.set('label', this.getLabelForVisibility(visibility));
    }
}


/**
 * Archive action.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.ArchiveActionView`.
 */
@spina
export class ArchiveAction extends BaseVisibilityAction {
    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    targetCollection = UserSession.instance.archivedReviewRequests;

    /**
     * Return the label to use for the action.
     *
     * Args:
     *     visibility (number):
     *         The visibility state of the review request.
     *
     * Returns:
     *     string:
     *     The text to use for the label.
     */
    getLabelForVisibility(
        visibility: number,
    ): string {
        return visibility === this.visibilityType
               ? _`Unarchive`
               : _`Archive`;
    }
}


/**
 * Mute action.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.MuteActionView`.
 */
@spina
export class MuteAction extends BaseVisibilityAction {
    /**********************
     * Instance variables *
     **********************/

    /** The collection to use for making changes to the visibility. */
    targetCollection = UserSession.instance.mutedReviewRequests;

    /** The visibility type controlled by this action. */
    visibilityType = ReviewRequest.VISIBILITY_MUTED;

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
    getLabelForVisibility(
        visibility: number,
    ): string {
        return visibility === this.visibilityType
               ? _`Unmute`
               : _`Mute`;
    }
}


/**
 * Action to create a blank review.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.CreateReviewActionView`.
 */
@spina
export class CreateReviewAction extends Actions.Action {
    /**********************
     * Instance variables *
     **********************/

    /** The pending review to create or manage. */
    #pendingReview: Review;

    /**
     * Initialize the action.
     */
    initialize() {
        super.initialize();

        const page = RB.PageManager.getPage();
        this.#pendingReview = page.pendingReview;

        this.listenTo(this.#pendingReview, 'saved destroy sync', this.#update);
        this.#update();
    }

    /**
     * Update the visibility state of the action.
     *
     * This will show the action only when there's no existing pending review.
     */
    #update() {
        this.set('visible', this.#pendingReview.isNew());
    }

    /**
     * Handle activation of the action.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        const pendingReview = this.#pendingReview;
        const page = RB.PageManager.getPage();

        await pendingReview.save();

        ReviewDialogView.create({
            review: pendingReview,
            reviewRequestEditor: page.getReviewRequestEditorModel(),
        });
    }
}


/**
 * Action to pop up the Edit Review dialog.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.EditReviewActionView`.
 */
@spina
export class EditReviewAction extends Actions.Action {
    /**********************
     * Instance variables *
     **********************/

    /** The pending review to create or manage. */
    #pendingReview: Review;

    /**
     * Initialize the action.
     */
    initialize() {
        super.initialize();

        const page = RB.PageManager.getPage();
        this.#pendingReview = page.pendingReview;

        this.listenTo(this.#pendingReview, 'saved destroy sync', this.#update);
        this.#update();
    }

    /**
     * Update the visibility state of the action.
     *
     * This will show the action only when there is an existing pending review.
     */
    #update() {
        this.set('visible', !this.#pendingReview.isNew());
    }

    /**
     * Handle activation of the action.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        const page = RB.PageManager.getPage();

        ReviewDialogView.create({
            review: this.#pendingReview,
            reviewRequestEditor: page.getReviewRequestEditorModel(),
        });
    }
}


/**
 * Action to add a general comment.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.AddGeneralCommentActionView`.
 */
@spina
export class AddGeneralCommentAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        RB.PageManager.getPage().addGeneralComment();
    }
}


/**
 * Action to mark a review request as "Ship It".
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.ShipItActionView`.
 */
@spina
export class ShipItAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        await RB.PageManager.getPage().shipIt();
    }
}


/**
 * Action for the "Add File" command.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.AddFileActionView`.
 */
@spina
export class AddFileAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditorView = page.reviewRequestEditorView as
            ReviewRequestEditorView;
        const reviewRequestEditor = reviewRequestEditorView.model;

        if (reviewRequestEditor.hasUnviewedUserDraft) {
            await reviewRequestEditorView.promptToLoadUserDraft();
        } else {
            const uploadDialog = new RB.UploadAttachmentView({
                reviewRequestEditor: reviewRequestEditor,
            });
            uploadDialog.show();
        }
    }
}


/**
 * Action for the "Update Diff" command.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.UpdateDiffActionView`.
 */
@spina
export class UpdateDiffAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the activation.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditorView = page.reviewRequestEditorView as
            ReviewRequestEditorView;
        const reviewRequestEditor = reviewRequestEditorView.model;
        const reviewRequest = reviewRequestEditor.get('reviewRequest');

        if (reviewRequestEditor.hasUnviewedUserDraft) {
            await reviewRequestEditorView.promptToLoadUserDraft();
        } else if (reviewRequestEditor.get('commits').length > 0) {
            const rbtoolsURL = 'https://www.reviewboard.org/docs/rbtools/latest/';

            const $dialog = $('<div>')
                .append($('<p>')
                    .html(_`
                        This review request was created with
                        <a href="${rbtoolsURL}">RBTools</a>,
                        and is tracking commit history.
                    `))
                .append($('<p>')
                    .html(_`
                        To add a new diff revision, you will need to use
                        <code>rbt post -u</code> instead of uploading a diff
                        file.
                    `))
                .modalBox({
                    buttons: [
                        paint<HTMLButtonElement>`
                            <Ink.Button>${_`Cancel`}</Ink.Button>
                        `,
                    ],
                    title: _`Use RBTools to update the diff`,
                })
                .on('close', () => {
                    $dialog.modalBox('destroy');
                });
        } else {
            const updateDiffView = new RB.UpdateDiffView({
                model: new RB.UploadDiffModel({
                    changeNumber: reviewRequest.get('commitID'),
                    repository: reviewRequest.get('repository'),
                    reviewRequest: reviewRequest,
                }),
            });
            updateDiffView.render();
        }
    }
}


/**
 * Action for the "Close > Discarded" command.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.CloseDiscardedActionView`.
 */
@spina
export class CloseDiscardedAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the close operation.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditorView = page.reviewRequestEditorView as
            ReviewRequestEditorView;

        await reviewRequestEditorView.closeDiscarded();
    }
}


/**
 * Action for the "Close > Completed" command.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.CloseCompletedActionView`.
 */
@spina
export class CloseCompletedAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the close operation.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditorView = page.reviewRequestEditorView as
            ReviewRequestEditorView;

        await reviewRequestEditorView.closeCompleted();
    }
}


/**
 * Action for the "Close > Delete Permanently" command.
 *
 * Version Added:
 *     7.1:
 *     This implements the action logic formerly found in
 *     :js:class:`RB.DeleteActionView`.
 */
@spina
export class DeleteAction extends Actions.Action {
    /**
     * Handle the action activation.
     *
     * Returns:
     *     Promise<void>:
     *     The promise for the delete operation.
     */
    async activate() {
        const page = RB.PageManager.getPage();
        const reviewRequestEditorView = page.reviewRequestEditorView as
            ReviewRequestEditorView;

        await reviewRequestEditorView.deleteReviewRequest();
    }
}
