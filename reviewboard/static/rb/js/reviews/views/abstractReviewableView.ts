/**
 * Abstract base for review UIs.
 */

import { BaseView, spina } from '@beanbag/spina';

import {
    type AbstractCommentBlock,
} from '../models/abstractCommentBlockModel';
import { type AbstractReviewable } from '../models/abstractReviewableModel';
import { type AbstractCommentBlockView } from './abstractCommentBlockView';
import { CommentDialogView } from './commentDialogView';


/**
 * Options for the AbstractReviewableView.
 *
 * Version Added:
 *     7.0
 */
export interface AbstractReviewableViewOptions {
    /** Whether the Review UI is rendered inline or as a full page. */
    renderedInline?: boolean;
}


/**
 * Abstract base for review UIs.
 *
 * This provides all the basics for creating a review UI. It does the
 * work of loading in comments, creating views, and displaying comment dialogs,
 */
@spina({
    prototypeAttrs: ['commentBlockView', 'commentsListName'],
})
export class AbstractReviewableView<
    TModel extends AbstractReviewable = AbstractReviewable,
    TElement extends Element = HTMLElement,
    TExtraViewOptions extends AbstractReviewableViewOptions =
        AbstractReviewableViewOptions
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    /**
     * The AbstractCommentBlockView subclass.
     *
     * This is the type that will be instantiated for rendering comment blocks.
     */
    static commentBlockView = null;

    /**
     * The list type (as a string) for passing to CommentDlg.
     */
    static commentsListName: string = null;

    /**********************
     * Instance variables *
     **********************/

    /** The comment dialog. */
    commentDlg: CommentDialogView = null;

    /** Whether the Review UI is rendered inline or as a full page. */
    renderedInline: boolean;

    /** The current comment block, if creating or editing a comment. */
    #activeCommentBlock: AbstractCommentBlock = null;

    /**
     * Initialize AbstractReviewableView.
     *
     * Args:
     *     options (object, optional):
     *         Options for the view.
     */
    initialize(options: Partial<TExtraViewOptions> = {}) {
        console.assert(!!this.commentBlockView,
                       'commentBlockView must be defined by the subclass');
        console.assert(!!this.commentsListName,
                       'commentsListName must be defined by the subclass');

        this.renderedInline = options.renderedInline || false;
    }

    /**
     * Render the reviewable to the page.
     *
     * This will call the subclass's renderContent(), and then handle
     * rendering each comment block on the reviewable.
     */
    onInitialRender() {
        this.renderContent();

        this.model.commentBlocks.each(this._addCommentBlockView, this);
        this.model.commentBlocks.on('add', this._addCommentBlockView, this);
    }

    /**
     * Render the content of the reviewable.
     *
     * This should be overridden by subclasses.
     */
    renderContent() {
        // Intentionally left blank.
    }

    /**
     * Create a new comment in a comment block and opens it for editing.
     *
     * Args:
     *     options (object):
     *         Options for the comment block creation.
     */
    createAndEditCommentBlock(options) {
        if (this.commentDlg !== null &&
            this.commentDlg.model.get('dirty') &&
            !confirm(_`
                You are currently editing another comment. Would you like to
                discard it and create a new one?
            `)) {
            return;
        }

        let defaultCommentBlockFields =
            _.result(this.model, 'defaultCommentBlockFields');

        if (defaultCommentBlockFields.length === 0 &&
            this.model.reviewableIDField) {
            console.log(dedent`
                Deprecation notice: Reviewable subclass is missing
                defaultCommentBlockFields. Rename reviewableIDField to
                defaultCommentBlockFields, and make it a list. This will
                be removed in Review Board 8.0.
            `);
            defaultCommentBlockFields = [this.model.reviewableIDField];
        }

        /* As soon as we add the comment block, show the dialog. */
        this.once('commentBlockViewAdded',
                  commentBlockView => this.showCommentDlg(commentBlockView));

        _.extend(options,
                 _.pick(this.model.attributes, defaultCommentBlockFields));
        this.model.createCommentBlock(options);
    }

    /**
     * Show the comment details dialog for a comment block.
     *
     * Args:
     *     commentBlockView (RB.AbstractCommentBlockView):
     *         The comment block to show the dialog for.
     */
    showCommentDlg(
        commentBlockView: AbstractCommentBlockView<AbstractCommentBlock>,
    ) {
        const commentBlock = commentBlockView.model;

        commentBlock.ensureDraftComment();

        if (this.#activeCommentBlock === commentBlock) {
            return;
        }

        this.stopListening(this.commentDlg, 'closed');
        this.commentDlg = CommentDialogView.create({
            comment: commentBlock.get('draftComment'),
            deletedWarning: commentBlock.getDeletedWarning(),
            draftWarning: commentBlock.getDraftWarning(),
            position: dlg => commentBlockView.positionCommentDlg(dlg),
            publishedComments: commentBlock.get('serializedComments'),
            publishedCommentsType: this.commentsListName,
        });
        this.#activeCommentBlock = commentBlock;

        this.listenTo(this.commentDlg, 'closed', () => {
            this.commentDlg = null;
            this.#activeCommentBlock = null;
        });
    }

    /**
     * Add a CommentBlockView for the given CommentBlock.
     *
     * This will create a view for the block, render it, listen for clicks
     * in order to show the comment dialog, and then emit
     * 'commentBlockViewAdded'.
     *
     * Args:
     *     commentBlock (RB.AbstractCommentBlock):
     *         The comment block to add a view for.
     */
    _addCommentBlockView(commentBlock: AbstractCommentBlock) {
        const commentBlockView = new this.commentBlockView({
            model: commentBlock,
        });

        commentBlockView.on('clicked',
                            () => this.showCommentDlg(commentBlockView));
        commentBlockView.render();
        this.trigger('commentBlockViewAdded', commentBlockView);
    }
}
