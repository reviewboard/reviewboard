/*
 * A dialog for updating file attachments.
 */
RB.UploadAttachmentView = RB.DialogView.extend({
    className: 'upload-attachment',
    title: gettext('Upload File'),
    buttons: [
        {
            id: 'cancel',
            label: gettext('Cancel'),
        },
        {
            id: 'upload',
            label: gettext('Upload'),
            primary: true,
            disabled: true,
            onClick: 'send',
        },
    ],
    template: _.template([
        '<div class="formdlg" style="width: 50em;">',
        ' <div class="error" style="display: none;"></div>',
        ' <form encoding="multipart/form-data" enctype="multipart/form-data"',
        '       id="attachment-upload-form">',
        '  <table>',
        '   <tbody>',
        '    <tr>',
        '     <td class="label"><label><%- captionText %></label></td>',
        '     <td><input name="caption" type="text" value="<%- presetCaption %>"></td>',
        '     <td><ul class="errorlist" style="display: none;"></ul></td>',
        '    </tr>',
        '    <tr>',
        '     <td class="label">',
        '      <label class="required"><%- pathText %></label>',
        '     </td>',
        '     <td><input name="path" type="file" class="js-path"></td>',
        '     <td><ul class="errorlist" style="display: none;"></ul></td>',
        '    </tr>',
        '   </tbody>',
        '  </table>',
        '  <% if (attachmentHistoryID >= 0) { %>',
        '    <input type="hidden" name="attachment_history"',
        '           value="<%- attachmentHistoryID %>" />',
        '  <% } %>',
        ' </form>',
        '</div>',
    ].join('')),

    events: _.extend({
        'change .js-path': 'updateUploadButtonEnabledState',
    }, RB.DialogView.prototype.events),

    /*
     * Initializes the view. New attachments don't have attachmentHistoryID
     * specified, so we set it to default value of -1.
     */
    initialize: function(options={}) {
        _.defaults(options, {
            attachmentHistoryID: -1,
            presetCaption: '',
        });

        const body = this.template({
            attachmentHistoryID: options.attachmentHistoryID,
            captionText: gettext('Caption:'),
            pathText: gettext('Path:'),
            presetCaption: options.presetCaption,
        });

        RB.DialogView.prototype.initialize.call(this, $.extend({
            body: body,
        }, options));
    },

    /*
     * Attempt to create a file attachment. In case of success, we will reload
     * the page, otherwise we will display errors.
     */
    send: function() {
        this.options.reviewRequest.createFileAttachment().save({
            form: this.$('#attachment-upload-form'),
            success: function() {
                window.location.reload();
            },
            error: function(model, xhr) {
                this.displayErrors($.parseJSON(xhr.responseText));
            }
        }, this);
    },

    /*
     * Displays errors on the form.
     *
     * @param {object} rsp  The server response.
     */
    displayErrors: function(rsp) {
        var errorStr = (rsp && rsp.err) ? rsp.err.msg : gettext('Unknown Error'),
            fieldName,
            $errorList,
            i,
            nameToRow = {'caption': 0, 'path': 1};

        this.$(".error")
            .text(errorStr)
            .show();

        if (rsp && rsp.fields) {
            /* Invalid form data */
            for (fieldName in rsp.fields) {
                if (rsp.fields.hasOwnProperty(fieldName)) {
                    $errorList = this.$(".errorlist")
                        .css("display", "block")[nameToRow[fieldName]];

                    for (i = 0; i < rsp.fields[fieldName].length; i++) {
                        $("<li/>")
                            .html(rsp.fields[fieldName][i])
                            .appendTo($errorList);
                    }
                }
            }
        }
    },

    /**
     * Render the dialog.
     *
     * Returns:
     *     UploadAttachmentView:
     *     This object, for chaining.
     */
    render: function() {
        RB.DialogView.prototype.render.call(this);

        this._$path = this.$('.js-path');
        this._$uploadBtn = this.$buttonsMap.upload;

        return this;
    },

    /*
     * Set the upload button to be clickable or not based on context.
     */
    updateUploadButtonEnabledState: function() {
        this._$uploadBtn.enable(this._$path.val());
    }
});
