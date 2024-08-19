/**
 * A dialog for uploading file attachments.
 */

import {
    type ButtonView,
    type DialogViewOptions,
    DialogView,
    craft,
    ComponentChild,
} from '@beanbag/ink';
import {
    type BaseModel,
    type EventsHash,
    spina,
} from '@beanbag/spina';
import { BackboneError } from 'reviewboard/common';

import { ReviewRequestEditor } from '../models/reviewRequestEditorModel';


/**
 * Options for the UploadAttachmentView.
 *
 * Version Added:
 *     8.0
 */
export interface UploadAttachmentViewOptions extends DialogViewOptions {
    /**
     * The ID of the attachment history to add to.
     *
     * This is only used if updating an existing attachment.
     */
    attachmentHistoryID?: number;

    /** The initial caption of the attachment. */
    presetCaption?: string;

    /** The review request editor. */
    reviewRequestEditor: ReviewRequestEditor;
}


/**
 * A dialog for uploading file attachments.
 */
@spina
export class UploadAttachmentView extends DialogView<
    BaseModel,
    UploadAttachmentViewOptions
> {
    static className = 'ink-c-dialog upload-attachment';
    static title = _`Upload File`;
    static events: EventsHash = {
        'change .js-path': '_updateUploadButtonEnabledState',
    };

    static template = _.template(dedent`
        <div class="formdlg" style="width: 50em;">
         <div class="error" style="display: none;"></div>
         <form encoding="multipart/form-data" enctype="multipart/form-data"
               id="attachment-upload-form">
          <table>
           <tbody>
            <tr>
             <td class="label"><label><%- captionText %></label></td>
             <td>
              <input name="caption" type="text" value="<%- presetCaption %>">
             </td>
             <td><ul class="errorlist" style="display: none;"></ul></td>
            </tr>
            <tr>
             <td class="label">
              <label class="required"><%- pathText %></label>
             </td>
             <td><input name="path" id="path" type="file" class="js-path"></td>
             <td><ul class="errorlist" style="display: none;"></ul></td>
            </tr>
           </tbody>
          </table>
          <% if (attachmentHistoryID >= 0) { %>
            <input type="hidden" name="attachment_history"
                   value="<%- attachmentHistoryID %>">
          <% } %>
         </form>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The input element for the path field. */
    _$path: JQuery<HTMLInputElement>;

    /** The "Cancel" button. */
    _cancelButton: ButtonView;

    /** The "Upload" button. */
    _uploadButton: ButtonView;

    /** The ID of the attachment history to use. */
    #attachmentHistoryID: number;

    /** The review request editor. */
    #reviewRequestEditor: ReviewRequestEditor;

    /**
     * Handle the initial rendering of the component.
     */
    protected onComponentInitialRender() {
        super.onComponentInitialRender();

        this._$path = this.$('input[name="path"]') as JQuery<HTMLInputElement>;
    }

    /**
     * Render the body for the dialog.
     *
     * Returns:
     *     ComponentChild or Array of ComponentChild:
     *     The elements to add for the body.
     */
    protected renderBody(): ComponentChild | ComponentChild[] {
        const options = this.initialComponentState.options;
        this.#attachmentHistoryID = options.attachmentHistoryID;
        this.#reviewRequestEditor = options.reviewRequestEditor;

        const historyID = (this.#attachmentHistoryID !== undefined)
            ? this.#attachmentHistoryID
            : -1;

        const $els = $(UploadAttachmentView.template({
            attachmentHistoryID: historyID,
            captionText: _`Caption:`,
            pathText: _`Path:`,
            presetCaption: options.presetCaption || '',
        }));

        return $els[0];
    }

    /**
     * Render the primary actions.
     *
     * Returns:
     *     ComponentChild or Array of ComponentChild:
     *     The elements to add for the primary actions.
     */
    protected renderPrimaryActions(): ComponentChild | ComponentChild[] {
        this._cancelButton = craft<ButtonView>`
            <Ink.DialogAction action="close">
             ${_`Cancel`}
            </Ink.DialogAction>
        `;
        this._uploadButton = craft<ButtonView>`
            <Ink.DialogAction type="primary"
                              disabled
                              callback=${() => this.send()}>
             ${_`Upload`}
            </Ink.DialogAction>
        `;

        return [
            this._cancelButton,
            this._uploadButton,
        ];
    }

    /**
     * Create a file attachment on the review request.
     *
     * On success, the dialog will be closed.
     *
     * Otherwise, on error, the dialog will display the errors.
     */
    async send() {
        const attachment = this.#reviewRequestEditor.createFileAttachment({
            attachmentHistoryID: this.#attachmentHistoryID,
        });

        try {
            await attachment.save({
                form: this.$('#attachment-upload-form'),
            });

            this.close();
        } catch(err) {
            await attachment.destroy();

            if (err instanceof BackboneError) {
                const rsp = JSON.parse(err.xhr.responseText);

                if (rsp) {
                    this.#displayError(rsp.err?.msg || _`Unknown Error`);

                    if (rsp.fields) {
                        this.#displayFieldErrors(rsp.fields);
                    }
                } else {
                    this.#displayError(err.toString());
                }
            } else {
                this.#displayError(err.toString());
            }
        }
    }

    /**
     * Display an error.
     *
     * Args:
     *     error (string):
     *         The error to show.
     */
    #displayError(error: string) {
        this.$('.error')
            .text(error)
            .show();
    }

    /**
     * Display errors for individual fields.
     *
     * Args:
     *     fieldErrors (object):
     *         A mapping from the field name to a list of errors associated
     *         with that field.
     */
    #displayFieldErrors(fieldErrors: Record<string, string[]>) {
        const $errorLists = this.$('.errorlist')
            .show();

        for (const [fieldName, errors] of Object.entries(fieldErrors)) {
            let $errorList: JQuery;

            if (fieldName === 'caption') {
                $errorList = $errorLists.eq(0);
            } else if (fieldName === 'path') {
                $errorList = $errorLists.eq(1);
            } else {
                console.error(dedent`
                    UploadAttachmentView received form error for unknown
                    field: ${fieldName}
                `);
                continue;
            }

            for (const error of errors) {
                $('<li>')
                    .html(error)
                    .appendTo($errorList);
            }
        }
    }

    /**
     * Set the upload button to be clickable or not based on context.
     *
     * This is public for consumption in unit tests.
     */
    private _updateUploadButtonEnabledState() {
        this._uploadButton.disabled = !this._$path.val();
    }
}
