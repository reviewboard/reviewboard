/**
 * Model that handles all operations and state for editing review requests.
 */

import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';

import {
    ResourceCollection,
    FileAttachment,
    FileAttachmentStates,
} from 'reviewboard/common';
import {
    FileAttachmentAttrs,
} from 'reviewboard/common/resources/models/fileAttachmentModel';


/** Attributes for the ReviewRequestEditor model. */
export interface ReviewRequestEditorAttrs extends ModelAttributes {
    /** All files attached to this review request. */
    allFileAttachments: ResourceCollection<FileAttachment>;

    /** The collection of commits on this review request. */
    commits: RB.DiffCommitCollection;

    /** The rendered change description text, if any. */
    changeDescriptionRenderedText: string;

    /** The rendered close description text, if any. */
    closeDescriptionRenderedText: string;

    /** The issue manager for the editor. */
    commentIssueManager: RB.CommentIssueManager;

    /**
     * Whether or not the review request is currently editable.
     *
     * This is derived from the ``mutableByUser`` attribute and the review
     * request's ``state`` attribute.
     */
    editable: boolean;

    /** The number of outstanding edits. */
    editCount: number;

    /** Whether or not a draft currently exists. */
    hasDraft: boolean;

    /**
     * The files attached to this review request to display.
     *
     * This includes active published and draft file attachments, and
     * ones that are pending deletion.
    */
    fileAttachments: ResourceCollection<FileAttachment>;

    /** A mapping of file attachment IDs to their comments. */
    fileAttachmentComments: {
        [key: string]: RB.FileAttachmentComment;
    };

    /** Whether or not the user can mutate the review request. */
    mutableByUser: boolean;

    /** Whether or not we are currently publishing the review request. */
    publishing: boolean;

    /** The review request model. */
    reviewRequest: RB.ReviewRequest;

    /** The legacy screenshots attached to this review request. */
    screenshots: Backbone.Collection<RB.Screenshot>;

    /** Whether or not to show the "Send e-mail" checkbox. */
    showSendEmail: boolean;

    /** Whether or not the status is currently editable. */
    statusEditable: boolean;

    /** Whether or not the status is mutable by the current user. */
    statusMutableByUser: boolean;
}


/**
 * Options for getting a draft field.
 */
export interface GetDraftFieldOptions {
    /**
     * The key to use for the field name in the API.
     *
     * This is required if ``useExtraData`` is set.
     */
    jsonFieldName?: string;

    /**
     * Whether the field is stored as part of extraData.
     *
     * If this is ``false``, the value will instead be stored as a regular
     * attribute on the model. If this is ``true``, ``jsonFieldName`` needs to
     * be set.
     */
    useExtraData?: boolean;

    /**
     * Whether to return the raw text value for a field.
     *
     * This requires ``useExtraData`` to be ``true``.
     */
    useRawTextValue?: boolean;
}


/**
 * Options for setting a draft field.
 */
export interface SetDraftFieldOptions {
    /**
     * Whether the field can support rich text (Markdown).
     *
     * This requires that ``jsonTextTypeFieldName`` is set.
     */
    allowMarkdown?: boolean;

    /** The key to use for the field name in the API. */
    jsonFieldName?: string;

    /** The key to use for the name of the field indicating the text type. */
    jsonTextTypeFieldName?: string;

    /** Whether the field is rich text (Markdown). */
    richText?: boolean;

    /** Whether the field should be set in extraData or as an attribute. */
    useExtraData?: boolean;
}


export interface PublishDraftOptions {
    /** Whether to skip e-mail notifications. */
    trivial?: boolean;
}


/**
 * Model that handles all operations and state for editing review requests.
 *
 * This manages the editing of all fields and objects on a review request,
 * the publishing workflow, and validation.
 */
@spina
export class ReviewRequestEditor extends BaseModel<ReviewRequestEditorAttrs> {
    static strings = {
        UNBALANCED_EDIT_COUNT:
            _`There is an internal error balancing the edit count`,
    };

    static defaults(): Partial<ReviewRequestEditorAttrs> {
        return {
            changeDescriptionRenderedText: '',
            closeDescriptionRenderedText: '',
            commentIssueManager: null,
            commitMessages: [],
            editCount: 0,
            editable: false,
            fileAttachmentComments: {},
            fileAttachments: null,
            hasDraft: false,
            mutableByUser: false,
            publishing: false,
            reviewRequest: null,
            screenshots: null,
            showSendEmail: false,
            statusEditable: false,
            statusMutableByUser: false,
        };
    }

    /**
     * Initialize the editor.
     */
    initialize() {
        const reviewRequest = this.get('reviewRequest');

        // Set up file attachments.
        let fileAttachments = this.get('fileAttachments');
        let allFileAttachments = this.get('allFileAttachments');

        if (fileAttachments === null) {
            fileAttachments = new ResourceCollection<FileAttachment>([], {
                model: FileAttachment,
                parentResource: reviewRequest.draft,
            });
            this.set('fileAttachments', fileAttachments);
        }

        if (allFileAttachments === null) {
            allFileAttachments = new ResourceCollection<FileAttachment>([], {
                model: FileAttachment,
                parentResource: reviewRequest.draft,
            });
            this.set('allFileAttachments', allFileAttachments);
        }

        this.listenTo(fileAttachments, 'add',
                      this._onFileAttachmentOrScreenshotAdded);
        fileAttachments.each(
            this._onFileAttachmentOrScreenshotAdded.bind(this));

        this.listenTo(fileAttachments, 'remove',
                      this._onFileAttachmentRemoved);

        // Set up screenshots.
        let screenshots = this.get('screenshots');

        if (screenshots === null) {
            screenshots = new Backbone.Collection([], {
                model: RB.Screenshot,
            });
            this.set('screenshots', screenshots);
        }

        this.listenTo(screenshots, 'add',
                      this._onFileAttachmentOrScreenshotAdded);
        screenshots.each(
            this._onFileAttachmentOrScreenshotAdded.bind(this));

        // Connect to other signals.
        this.listenTo(reviewRequest.draft, 'saving',
                      () => this.trigger('saving'));
        this.listenTo(reviewRequest.draft, 'saved',
                      () => this.trigger('saved'));
        this.listenTo(reviewRequest, 'change:state', this._computeEditable);
        this._computeEditable();
    }

    /**
     * Parse the given attributes into model attributes.
     *
     * Args:
     *     attrs (object):
     *        The attributes to parse.
     *
     * Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(
        attrs: object,
    ): Partial<ReviewRequestEditorAttrs> {
        return _.defaults({
            commits: new RB.DiffCommitCollection(
                attrs.commits || [],
                {parse: true}
            ),
        }, attrs);
    }

    /**
     * Create a file attachment tracked by the editor.
     *
     * This wraps RB.ReviewRequestDraft.createFileAttachment and stores the
     * file attachment in the fileAttachments collection.
     *
     * This should be used instead of
     * RB.ReviewRequestDraft.createFileAttachment for any existing or newly
     * uploaded file attachments.
     *
     * Args:
     *     attributes (FileAttachmentAttrs, optional):
     *         Model attributes for the new file attachment.
     *
     * Returns:
     *     FileAttachment:
     *     The new file attachment model.
     */
    createFileAttachment(
        attributes: Partial<FileAttachmentAttrs> = {},
    ): FileAttachment {
        const draft = this.get('reviewRequest').draft;
        const fileAttachment = draft.createFileAttachment(attributes);
        const attachmentHistoryID = attributes.attachmentHistoryID;

        const fileAttachments = this.get('fileAttachments');

        if (attachmentHistoryID && attachmentHistoryID > 1) {
            /* We're adding a new revision of an existing attachment. */
            fileAttachment.set({
                state: FileAttachmentStates.NEW_REVISION,
            });
            const replacedAttachment = fileAttachments.findWhere({
                attachmentHistoryID: attributes.attachmentHistoryID,
            });
            const index = fileAttachments.indexOf(replacedAttachment);

            /*
             * Since we're replacing an attachment instead of actually
             * removing one, we silently remove the existing attachment as to
             * not trigger any standard removal handlers.
             *
             * We do however want to remove the existing attachment's
             * thumbnail, so we fire a "replaceAttachment" signal which will
             * be picked up by the ReviewRequestEditorView to remove the
             * thumbnail. Note that we trigger this signal before adding the
             * new attachment so that the existing thumbnail gets removed
             * before the new thumbnail get added.
             */
            fileAttachments.remove(replacedAttachment, {silent: true});
            this.trigger('replaceAttachment', replacedAttachment);
            fileAttachments.add(fileAttachment, { at: index });
        } else {
            fileAttachments.add(fileAttachment);
        }

        return fileAttachment;
    }

    /**
     * Return a field from the draft.
     *
     * This will look either in the draft's data or in the extraData (for
     * custom fields), returning the value provided either when the page
     * was generated or when it was last edited.
     *
     * Args:
     *     fieldName (string):
     *         The name of the field to get.
     *
     *     options (GetDraftFieldOptions, optional):
     *         Options for the operation.
     *
     * Returns:
     *     *:
     *     The value of the field.
     */
    getDraftField(
        fieldName: string,
        options: GetDraftFieldOptions = {},
    ): unknown {
        const reviewRequest = this.get('reviewRequest');
        const draft = reviewRequest.draft;

        if (options.useExtraData) {
            let data;

            if (options.useRawTextValue) {
                const rawTextFields = draft.get('rawTextFields');

                if (rawTextFields && rawTextFields.extra_data) {
                    data = rawTextFields.extra_data;
                }
            }

            if (!data) {
                data = draft.get('extraData');
            }

            return data[fieldName];
        } else if (fieldName === 'closeDescription' ||
                   fieldName === 'closeDescriptionRichText') {
            return reviewRequest.get(fieldName);
        } else {
            return draft.get(fieldName);
        }
    }

    /**
     * Set a field in the draft.
     *
     * If we're in the process of publishing, this will check if we have saved
     * all fields before publishing the draft.
     *
     * Once the field has been saved, two events will be triggered:
     *
     *     * fieldChanged(fieldName, value)
     *     * fieldChanged:<fieldName>(value)
     *
     * Veersion Changed:
     *     6.0:
     *     Removed the callbacks entirely, along with the ``context`` argument.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     fieldName (string):
     *         The name of the field to set.
     *
     *     value (*):
     *         The value to set in the field.
     *
     *     options (SetDraftFieldOptions, optional):
     *         Options for the set operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    setDraftField(
        fieldName: string,
        value: unknown,
        options: SetDraftFieldOptions = {},
    ): Promise<void> {
        const reviewRequest = this.get('reviewRequest');
        const data = {}; // TODO: add typing once RB.ReviewRequest is TS

        let jsonFieldName = options.jsonFieldName;

        console.assert(
            !!jsonFieldName,
            `jsonFieldName must be set when setting draft ` +
            `field "${fieldName}".`);

        if (options.useExtraData) {
            jsonFieldName = `extra_data.${jsonFieldName}`;
        }

        if (options.allowMarkdown) {
            let jsonTextTypeFieldName = options.jsonTextTypeFieldName;

            console.assert(!!jsonTextTypeFieldName,
                           'jsonTextTypeFieldName must be set.');

            if (options.useExtraData) {
                jsonTextTypeFieldName = `extra_data.${jsonTextTypeFieldName}`;
            }

            const richText = !!options.richText;
            data[jsonTextTypeFieldName] = richText ? 'markdown' : 'plain';

            data.force_text_type = 'html';
            data.include_text_types = 'raw';
        }

        data[jsonFieldName] = value;

        return reviewRequest.draft.save({ data })
            .then(() => {
                this.set('hasDraft', true);

                this.trigger('fieldChanged:' + fieldName, value);
                this.trigger('fieldChanged', fieldName, value);
            })
            .catch(err => {
                let message = '';

                this.set('publishing', false);

                const rsp = err.xhr.errorPayload;

                /*
                 * An error can be caused by a 503 when the site is in
                 * read-only mode, in which case the fields will be
                 * empty.
                 */
                if (rsp.fields !== undefined) {
                    const fieldValue = rsp.fields[jsonFieldName];
                    const fieldValueLen = fieldValue.length;

                    /* Wrap each term in quotes or a leading 'and'. */
                    _.each(fieldValue, (value, i) => {
                        // XXX: This method isn't localizable.
                        if (i === fieldValueLen - 1 && fieldValueLen > 1) {
                            if (i > 2) {
                                message += ', ';
                            }

                            message += ` and "${value}"`;
                        } else {
                            if (i > 0) {
                                message += ', ';
                            }

                            message += `"${value}"`;
                        }
                    });

                    if (fieldName === 'targetGroups') {
                        message = interpolate(
                            ngettext('Group %s does not exist.',
                                     'Groups %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    } else if (fieldName === 'targetPeople') {
                        message = interpolate(
                            ngettext('User %s does not exist.',
                                     'Users %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    } else if (fieldName === 'submitter') {
                        message = interpolate(
                            gettext('User %s does not exist.'),
                            [message]);
                    } else if (fieldName === 'dependsOn') {
                        message = interpolate(
                            ngettext('Review Request %s does not exist.',
                                     'Review Requests %s do not exist.',
                                     fieldValue.length),
                            [message]);
                    }
                }

                err.message = message;

                return Promise.reject(err);
            });
    }

    /**
     * Publish the draft to the server.
     *
     * This assumes all fields have been saved.
     *
     * If there's an error during saving or validation, the "publishError"
     * event will be triggered with the error message. Otherwise, upon
     * success, the "publish" event will be triggered. However, users will
     * have the chance to cancel the publish in the event that the submitter
     * has been changed.
     *
     * Args:
     *     options (object):
     *         Options for the publish operation.
     *
     * Option Args:
     *     trivial (boolean):
     *         Whether the publish is "trivial" (if true, no e-mail
     *         notifications will be sent).
     */
    async publishDraft(options: PublishDraftOptions = {}) {
        const reviewRequest = this.get('reviewRequest');

        try {
            await reviewRequest.draft.ensureCreated();

            if (reviewRequest.attributes.links.submitter.title !==
                reviewRequest.draft.attributes.links.submitter.title) {
                const confirmed = confirm(_`
                    Are you sure you want to change the ownership of this
                    review request? Doing so may prevent you from editing
                    the review request afterwards.
                `);

                if (!confirmed) {
                    return;
                }
            }

            await reviewRequest.draft.publish({
                trivial: options.trivial ? 1 : 0,
            });
            this.trigger('published');
        } catch (err) {
            this.trigger('publishError', err.message);
        }
    }

    /**
     * Increment an attribute by 1.
     *
     * The attribute must be an integer.
     *
     * Args:
     *     attr (string):
     *         The name of the attribute to increment.
     */
    incr(
        attr: Backbone._StringKey<ReviewRequestEditorAttrs>,
    ) {
        const value = this.get(attr);
        console.assert(_.isNumber(value));
        this.set(attr, value + 1, {
            validate: true,
        });
    }

    /**
     * Decrement an attribute by 1.
     *
     * The attribute must be an integer.
     *
     * Args:
     *     attr (string):
     *         The name of the attribute to decrement.
     */
    decr(
        attr: Backbone._StringKey<ReviewRequestEditorAttrs>,
    ) {
        const value = this.get(attr);
        console.assert(_.isNumber(value));
        this.set(attr, value - 1, {
            validate: true,
        });
    }

    /**
     * Validate the given attributes.
     *
     * Args:
     *     attrs (object):
     *         The attributes to validate.
     */
    validate(
        attrs: Partial<ReviewRequestEditorAttrs>,
    ): string {
        const strings = ReviewRequestEditor.strings;

        if (_.has(attrs, 'editCount') && attrs.editCount < 0) {
            return strings.UNBALANCED_EDIT_COUNT;
        }
    }

    /**
     * Compute the editable state of the review request and open/close states.
     *
     * The review request is editable if the user has edit permissions and it's
     * not closed.
     *
     * The close state and accompanying description is editable if the user
     * has the ability to close the review request and it's currently closed.
     */
    _computeEditable() {
        const state = this.get('reviewRequest').get('state');
        const pending = (state === RB.ReviewRequest.PENDING);

        this.set({
            editable: this.get('mutableByUser') && pending,
            statusEditable: this.get('statusMutableByUser') && !pending,
        });
    }

    /**
     * Handle when a FileAttachment or Screenshot is added.
     *
     * Listens for events on the FileAttachment or Screenshot and relays
     * them to the editor.
     *
     * Args:
     *     attachment (FileAttachment or RB.Screenshot):
     *         The new file attachment or screenshot.
     */
    _onFileAttachmentOrScreenshotAdded(
        attachment: FileAttachment | RB.Screenshot,
    ) {
        this.listenTo(attachment, 'saving',
                      () => this.trigger('saving'));

        this.listenTo(attachment, 'saved destroy', () => {
            this.set('hasDraft', true);
            this.trigger('saved');
        });
    }

    /**
     * Handle when a FileAttachment is removed.
     *
     * Version Added:
     *     6.0
     *
     * Args:
     *     fileAttachment (RB.FileAttachment):
     *         The file attachment.
     *
     *     collection (Backbone.Collection):
     *         The collection of all file attachments.
     *
     *     options (object):
     *         Options.
     *
     * Option Args:
     *     index (number):
     *         The index of the file attachment being removed.
     */
    _onFileAttachmentRemoved(
        fileAttachment: FileAttachment,
        collection: ResourceCollection<FileAttachment>,
        options: {
            index: number;
        },
    ) {
        const state = fileAttachment.get('state');
        const fileAttachments = this.get('fileAttachments');
        const allFileAttachments = this.get('allFileAttachments');

        if (state === FileAttachmentStates.NEW_REVISION) {
            /*
             * We're removing a new revision of a published file attachment.
             * Add the published file attachment back to the list of file
             * attachments to display it again.
             */
            const historyID = fileAttachment.get('attachmentHistoryID');
            const revision = fileAttachment.get('revision');
            const replacedAttachment = allFileAttachments.findWhere({
                attachmentHistoryID: historyID,
                revision: revision - 1,
            });
            fileAttachments.add(replacedAttachment, { at: options.index });
        } else if (state === FileAttachmentStates.PUBLISHED) {
            /*
             * We're removing a published file attachment. Change its state
             * and add it back to the list to continue displaying it.
             */
            fileAttachment.set({
                state: FileAttachmentStates.PENDING_DELETION,
            });
            fileAttachments.add(fileAttachment.clone(), { at: options.index });
        }
    }
}
