/**
 * A dialog for updating file attachments.
 */
RB.UploadAttachmentView = Backbone.View.extend({
    className: 'upload-attachment',
    template: _.template(dedent`
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
             <td><input name="path" id="path" type="file"></td>
             <td><ul class="errorlist" style="display: none;"></ul></td>
            </tr>
           </tbody>
          </table>
          <% if (attachmentHistoryID >= 0) { %>
            <input type="hidden" name="attachment_history"
                   value="<%- attachmentHistoryID %>" />
          <% } %>
         </form>
        </div>
    `),

    events: {
        'change #path': 'updateUploadButtonEnabledState',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     attachmentHistoryID (number, optional):
     *         The ID of the attachment history to add to. This can be omitted
     *         if this is a new attachment (as opposed to updating an existing
     *         one).
     *
     *     presetCaption (string):
     *         The initial caption of the attachment.
     *
     *     reviewRequest (RB.ReviewRequest):
     *         The review request.
     */
    initialize(options) {
        /*
         * New attachments don't have attachmentHistoryID specified, so we set
         * it to default value of -1.
         */
        this.options = _.defaults(options, {
            attachmentHistoryID: -1,
            presetCaption: '',
        });
    },

    /**
     * Create a file attachment on the review request.
     *
     * On success, the dialog will be closed.
     *
     * Otherwise, on error, the dialog will display the errors.
     */
    send() {
        this.options.reviewRequestEditor.createFileAttachment().save({
            form: this.$('#attachment-upload-form'),
            success: function() {
                // Close 'Add File' modal.
                this.$el.modalBox('destroy');
            },
            error: function(model, xhr) {
                this.displayErrors($.parseJSON(xhr.responseText));
            },
        }, this);
    },

    /**
     * Display errors on the form.
     *
     * Args:
     *     rsp (object):
     *         The server response.
     */
    displayErrors(rsp) {
        const errorStr = ((rsp && rsp.err)
            ? rsp.err.msg
            : gettext('Unknown Error'));
        this.$('.error')
            .text(errorStr)
            .show();

        if (rsp && rsp.fields) {
            /* Invalid form data */
            const nameToRow = {
                caption: 0,
                path: 1,
            };

            for (let fieldName in rsp.fields) {
                if (rsp.fields.hasOwnProperty(fieldName)) {
                    const $errorList = this.$('.errorlist')
                        .css('display', 'block');
                    const elIndex = nameToRow[fieldName];
                    const errorListEl = $errorList[elIndex];

                    for (let i = 0; i < rsp.fields[fieldName].length; i++) {
                        $('<li>')
                            .html(rsp.fields[fieldName][i])
                            .appendTo(errorListEl);
                    }
                }
            }
        }
    },

    /**
     * Render the popup window for attachment upload.
     *
     * Returns:
     *     RB.UploadAttachmentView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .append(this.template({
                attachmentHistoryID: this.options.attachmentHistoryID,
                captionText: gettext('Caption:'),
                pathText: gettext('Path:'),
                presetCaption: this.options.presetCaption,
            }))
            .modalBox({
                title: gettext('Upload File'),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext('Cancel')),
                    $('<input id="upload" type="button" disabled/>')
                        .val(gettext('Upload'))
                        .click(ev => {
                            ev.stopPropagation();
                            ev.preventDefault();

                            this.send();
                        }),
                ],
            });

        this._$path = $('#path');
        this._$uploadBtn = $('#upload');

        return this;
    },

    /**
     * Set the upload button to be clickable or not based on context.
     */
    updateUploadButtonEnabledState() {
        this._$uploadBtn.enable(this._$path.val());
    },
});
