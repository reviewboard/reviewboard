/*
 * A dialog for updating file attachments.
 */
RB.UploadAttachmentView = Backbone.View.extend({
    className: 'upload-attachment',
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
        '     <td><input name="path" id="path" type="file"></td>',
        '     <td><ul class="errorlist" style="display: none;"></ul></td>',
        '    </tr>',
        '   </tbody>',
        '  </table>',
        '  <% if (attachmentHistoryID >= 0) { %>',
        '    <input type="hidden" name="attachment_history"',
        '           value="<%- attachmentHistoryID %>" />',
        '  <% } %>',
        ' </form>',
        '</div>'
    ].join('')),

    events: {
        'change #path': 'updateUploadButtonEnabledState'
    },

    /*
     * Initializes the view. New attachments don't have attachmentHistoryID
     * specified, so we set it to default value of -1.
     */
    initialize: function(options) {
        this.options = $.extend({
            attachmentHistoryID: -1,
            presetCaption: ''
        }, options);
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
        var errorStr = rsp.err.msg,
            fieldName,
            $errorList,
            i,
            nameToRow = {'caption': 0, 'path': 1};

        this.$(".error")
            .text(errorStr)
            .show();

        if (rsp.fields) {
            /* Invalid form data */
            for (fieldName in rsp.fields) {
                $errorList = this.$(".errorlist")
                    .css("display", "block")[nameToRow[fieldName]];

                for (i = 0; i < rsp.fields[fieldName].length; i++) {
                    $("<li/>")
                        .html(rsp.fields[fieldName][i])
                        .appendTo($errorList);
                }
            }
        }
    },

    /*
     * Renders the popup window for attachment upload.
     */
    render: function() {
        var self = this;

        this.$el
            .append(this.template({
                attachmentHistoryID: this.options.attachmentHistoryID,
                captionText: gettext("Caption:"),
                pathText: gettext("Path:"),
                presetCaption: this.options.presetCaption
            }))
            .modalBox({
                title: gettext("Upload File"),
                buttons: [
                    $('<input type="button"/>')
                        .val(gettext("Cancel")),
                    $('<input id="upload" type="button" disabled/>')
                        .val(gettext("Upload"))
                        .click(function() {
                            self.send();
                            return false;
                        })
                ]
            });

        this._$path = $('#path');
        this._$uploadBtn = $('#upload');

        return this;
    },

    /*
     * Set the upload button to be clickable or not based on context.
     */
    updateUploadButtonEnabledState: function() {
        this._$uploadBtn.enable(this._$path.val());
    }
});
