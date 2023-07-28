/** The state for editing a new or existing draft comment. */
import { BaseModel, spina } from '@beanbag/spina';

import {
    ExtraDataMixin,
    UserSession,
} from 'reviewboard/common';

import { ReviewRequestEditor } from './reviewRequestEditorModel';


/**
 * Attributes for the CommentEditor model.
 */
interface CommentEditorAttrs {
    /** Whether the draft comment can be deleted. */
    canDelete: boolean;

    /** Whether the draft comment can be edited. */
    canEdit: boolean;

    /** Whether the draft comment can be saved. */
    canSave: boolean;

    /** Whether the comment is currently being edited. */
    editing: boolean;

    /** The draft state for the comment's extra data. */
    extraData: object;

    /** The comment model. */
    comment: RB.BaseComment;

    /** Whether the draft comment has been edited but not saved. */
    dirty: boolean;

    /** Whether the comment opens an issue. */
    openIssue: boolean;

    /** The thread of previous comments that this draft is a reply to. */
    publishedComments: RB.BaseComment[];

    /** The type of comment that this draft is a reply to, if applicable. */
    publishedCommentsType: string;

    /** Whether this draft comment requires issue verification. */
    requireVerification: boolean;

    /** The review request that this comment is on. */
    reviewRequest: RB.ReviewRequest;

    /** The review request editor for the review request. */
    reviewRequestEditor: ReviewRequestEditor;

    /** Whether the comment is formatted in Markdown. */
    richText: boolean;

    /** The comment text. */
    text: string;
}

/**
 * Represents the state for editing a new or existing draft comment.
 *
 * From here, a comment can be created, edited, or deleted.
 *
 * This will provide state on what actions are available on a comment,
 * informative text, dirty states, existing published comments on the
 * same region this comment is on, and more.
 */
@spina({
    mixins: [ExtraDataMixin],
})
export class CommentEditor extends BaseModel<CommentEditorAttrs> {
    /**
     * Return the default values for the model attributes.
     *
     * Returns:
     *     CommentEditorAttrs:
     *     The default values for the attributes.
     */
    static defaults(): CommentEditorAttrs {
        const userSession = UserSession.instance;

        return {
            canDelete: false,
            canEdit: undefined,
            canSave: false,
            comment: null,
            dirty: false,
            editing: false,
            extraData: {},
            openIssue: userSession.get('commentsOpenAnIssue'),
            publishedComments: [],
            publishedCommentsType: null,
            requireVerification: false, // TODO: add a user preference for this
            reviewRequest: null,
            reviewRequestEditor: null,
            richText: userSession.get('defaultUseRichText'),
            text: '',
        };
    }

    /**
     * Initialize the comment editor.
     */
    initialize() {
        this.listenTo(this, 'change:comment', this.#updateFromComment);
        this.#updateFromComment();

        /*
         * Unless a canEdit value is explicitly given, we want to compute
         * the proper state.
         */
        if (this.get('canEdit') === undefined) {
            this.#updateCanEdit();
        }

        this.listenTo(this, 'change:dirty', (model, dirty) => {
            const reviewRequestEditor = this.get('reviewRequestEditor');

            if (reviewRequestEditor) {
                if (dirty) {
                    reviewRequestEditor.incr('editCount');
                } else {
                    reviewRequestEditor.decr('editCount');
                }
            }
        });

        this.listenTo(
            this,
            'change:openIssue change:requireVerification change:richText ' +
            'change:text',
            () => {
                if (this.get('editing')) {
                    this.set('dirty', true);
                    this.#updateState();
                }
            });

        this.#updateState();

        this._setupExtraData();
    }

    /**
     * Set the editor to begin editing a new or existing comment.
     */
    beginEdit() {
        console.assert(this.get('canEdit'),
                       'beginEdit() called when canEdit is false.');
        console.assert(this.get('comment'),
                       'beginEdit() called when no comment was first set.');

        this.set({
            dirty: false,
            editing: true,
        });

        this.#updateState();
    }

    /**
     * Delete the current comment, if it can be deleted.
     *
     * This requires that there's a saved comment to delete.
     *
     * The editor will be marked as closed, requiring a new call to beginEdit.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async deleteComment() {
        console.assert(this.get('canDelete'),
                       'deleteComment() called when canDelete is false.');

        const comment = this.get('comment');
        await comment.destroy();
        this.trigger('deleted');
        this.close();
    }

    /**
     * Cancel editing of a comment.
     *
     * If there's a saved comment and it's been made empty, it will end
     * up being deleted. Then this editor will be marked as closed,
     * requiring a new call to beginEdit.
     */
    cancel() {
        this.stopListening(this, 'change:comment');

        const comment = this.get('comment');

        if (comment) {
            comment.destroyIfEmpty();
            this.trigger('canceled');
        }

        this.close();
    }

    /**
     * Close editing of the comment.
     *
     * The comment state will be reset, and the "closed" event will be
     * triggered.
     *
     * To edit a comment again after closing it, the proper state must be
     * set again and beginEdit must be called.
     */
    close() {
        /* Set this first, to prevent dirty firing. */
        this.set('editing', false);

        this.set({
            comment: null,
            dirty: false,
            extraData: new RB.ExtraData(),
            text: '',
        });

        this.trigger('closed');
    }

    /**
     * Save the comment.
     *
     * If this is a new comment, it will be created on the server.
     * Otherwise, the existing comment will be updated.
     *
     * The editor will not automatically be marked as closed. That is up
     * to the caller.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         The context to use when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async save(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.CommentEditor.save was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.save(newOptions));
        }

        console.assert(this.get('canSave'),
                       'save() called when canSave is false.');

        const extraData = _.clone(this.get('extraData'));
        extraData.require_verification = this.get('requireVerification');

        const comment = this.get('comment');
        comment.set({
            extraData: extraData,
            includeTextTypes: 'html,raw,markdown',
            issueOpened: this.get('openIssue'),
            richText: this.get('richText'),
            text: this.get('text'),
        });

        await comment.save();

        this.set('dirty', false);
        this.trigger('saved');
    }

    /**
     * Update the state of the editor from the currently set comment.
     */
    async #updateFromComment() {
        const oldComment = this.previous('comment');
        const comment = this.get('comment');

        if (oldComment) {
            oldComment.destroyIfEmpty();
        }

        if (comment) {
            const defaults = _.result(this, 'defaults');
            const defaultRichText = defaults.richText;

            /*
             * Set the attributes based on what we know at page load time.
             *
             * Note that it is *possible* that the comments will have changed
             * server-side since loading the page (if the user is reviewing
             * the same diff in two tabs). However, it's unlikely.
             *
             * Doing this before the ready() call ensures that we'll have the
             * text and state up-front and that it won't overwrite what the
             * user has typed after load.
             *
             * Note also that we'll always want to use our default richText
             * value if it's true, and we'll fall back on the comment's value
             * if false. This is so that we can keep a consistent experience
             * when the "Always edit Markdown by default" value is set.
             */
            this.set({
                dirty: false,
                extraData: comment.get('extraData'),
                openIssue: comment.get('issueOpened') === null
                           ? defaults.openIssue
                           : comment.get('issueOpened'),
                requireVerification: comment.requiresVerification(),
                richText: defaultRichText || !!comment.get('richText'),
            });

            /*
             * We'll try to set the one from the appropriate text fields, if it
             * exists and is not empty. If we have this, then it came from a
             * previous save. If we don't have it, we'll fall back to "text",
             * which should be normalized content from the initial page load.
             */
            const textFields = (comment.get('richText') || !defaultRichText
                                ? comment.get('rawTextFields')
                                : comment.get('markdownTextFields'));

            this.set('text',
                     !_.isEmpty(textFields)
                     ? textFields.text
                     : comment.get('text'));

            await comment.ready();

            this.#updateState();
        }
    }

    /**
     * Update the canEdit state of the editor.
     *
     * This is based on the authentication state of the user, and
     * whether or not there's an existing draft for the review request.
     */
    #updateCanEdit() {
        const userSession = UserSession.instance;

        this.set('canEdit',
                 userSession.get('authenticated') &&
                 !userSession.get('readOnly'));
    }

    /**
     * Update the capability states of the editor.
     *
     * Some of the can* properties will change to reflect the various
     * actions that can be performed with the editor.
     */
    #updateState() {
        const canEdit = this.get('canEdit');
        const editing = this.get('editing');
        const comment = this.get('comment');

        this.set({
            canDelete: canEdit && editing && comment && !comment.isNew(),
            canSave: canEdit && editing && this.get('text') !== '',
        });
    }
}
