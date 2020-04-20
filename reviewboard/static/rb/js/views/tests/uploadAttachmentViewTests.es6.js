suite('rb/views/UploadAttachmentView', function() {
    let reviewRequest;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            summary: 'My Review Request',
            reviewURL: '/r/1/',
        });
    });

    describe('Instances', function() {
        let dialog;

        afterEach(function() {
            if (dialog) {
                dialog.hide();
                dialog = null;
            }
        });

        describe('Buttons', function() {
            beforeEach(function() {
                dialog = new RB.UploadAttachmentView({
                    reviewRequest: reviewRequest,
                });
            });

            describe('Cancel', function() {
                let $button;

                beforeEach(function() {
                    dialog.show();
                    $button = dialog.$buttonsMap.cancel;

                    expect($button.length).toBe(1);
                });

                it('Enabled by default', function() {
                    expect($button.is(':disabled')).toBe(false);
                });

                it('Closes dialog when clicked', function() {
                    spyOn($.fn, 'modalBox').and.callThrough();
                    dialog.delegateEvents();

                    $button.click();
                    expect($.fn.modalBox).toHaveBeenCalledWith('destroy');
                });
            });

            describe('Upload', function() {
                let $button;
                let $path;

                beforeEach(function() {
                    spyOn(dialog, 'send');

                    dialog.show();
                    $button = dialog.$buttonsMap.upload;
                    $path = dialog._$path;

                    /*
                     * Allows the value of the input to be changed
                     * programmatically without security issues.
                     */
                    $path.attr('type', 'text');

                    spyOn(dialog, 'updateUploadButtonEnabledState')
                        .and.callThrough();
                    dialog.delegateEvents();

                    expect($button.length).toBe(1);
                });

                it('Disabled by default until a file is uploaded', function() {
                    expect($button.is(':disabled')).toBe(true);
                });

                it('Enabled when a file is uploaded', function() {
                    expect($button.is(':disabled')).toBe(true);

                    $path
                        .val('fakefile')
                        .trigger('change');

                    expect(dialog.updateUploadButtonEnabledState)
                        .toHaveBeenCalledTimes(1);
                    expect($button.is(':disabled')).toBe(false);
                });

                it('Disabled when an uploaded file is removed', function() {
                    $path
                        .val('fakefile')
                        .trigger('change')
                        .val('')
                        .trigger('change');

                    expect(dialog.updateUploadButtonEnabledState)
                        .toHaveBeenCalledTimes(2);
                    expect($button.is(':disabled')).toBe(true);
                });

                it('Uploads the file attachment', function() {
                    expect($button.is(':disabled')).toBe(true);

                    $path
                        .val('fakefile')
                        .trigger('change');

                    expect(dialog.updateUploadButtonEnabledState).toHaveBeenCalled();
                    expect($button.is(':disabled')).toBe(false);

                    $button.click();
                    expect(dialog.send).toHaveBeenCalled();
                });
            });
        });

        it('Dialog for updating an existing file attachment', function() {
            dialog = new RB.UploadAttachmentView({
                attachmentHistoryID: 14,
                presetCaption: 'fakecaption',
                reviewRequest: reviewRequest,
            });

            dialog.show();
            const $caption = dialog.$('[name="caption"]');
            const $attachmentHistory = dialog.$('[name="attachment_history"]');

            expect($caption.length).toBe(1);
            expect($caption.val()).toBe('fakecaption');

            expect($attachmentHistory.length).toBe(1);
            expect($attachmentHistory.val()).toBe('14');
        });
    });
});
