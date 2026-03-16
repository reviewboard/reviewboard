import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    ReviewRequest,
} from 'reviewboard/common';
import {
    ReviewRequestEditor,
    UploadAttachmentView,
} from 'reviewboard/reviews';


suite('rb/views/UploadAttachmentView', function() {
    let reviewRequest: ReviewRequest;
    let editor: ReviewRequestEditor;

    beforeEach(function() {
        reviewRequest = new ReviewRequest({
            reviewURL: '/r/1/',
            summary: 'My Review Request',
        });
        editor = new ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });
    });

    describe('Instances', function() {
        let dialog: UploadAttachmentView;

        afterEach(function() {
            if (dialog) {
                dialog.remove();
                dialog = null;
            }
        });

        describe('Buttons', function() {
            beforeEach(function() {
                dialog = new UploadAttachmentView({
                    reviewRequestEditor: editor,
                });
                dialog.render();
            });

            describe('Cancel', function() {
                beforeEach(function() {
                    dialog.show();
                });

                it('Enabled by default', function() {
                    expect(dialog._cancelButton.disabled).toBe(false);
                });

                it('Closes dialog when clicked', function() {
                    spyOn(dialog, 'close').and.callThrough();
                    dialog._cancelButton.el.click();

                    expect(dialog.close).toHaveBeenCalled();
                });
            });

            describe('Upload', function() {
                beforeEach(function() {
                    spyOn(dialog, 'send');

                    dialog.show();

                    /*
                     * Allows the value of the input to be changed
                     * programmatically without security issues.
                     */
                    dialog._$path.attr('type', 'text');

                    spyOn(dialog, '_updateUploadButtonEnabledState')
                        .and.callThrough();
                    dialog.delegateEvents();
                });

                it('Disabled by default until a file is uploaded', function() {
                    expect(dialog._uploadButton.disabled).toBe(true);
                });

                it('Enabled when a file is uploaded', function() {
                    expect(dialog._uploadButton.disabled).toBe(true);

                    dialog._$path
                        .val('fakefile')
                        .trigger('change');

                    expect(dialog._updateUploadButtonEnabledState)
                        .toHaveBeenCalledTimes(1);
                    expect(dialog._uploadButton.disabled).toBe(false);
                });

                it('Disabled when an uploaded file is removed', function() {
                    dialog._$path
                        .val('fakefile')
                        .trigger('change')
                        .val('')
                        .trigger('change');

                    expect(dialog._updateUploadButtonEnabledState)
                        .toHaveBeenCalledTimes(2);
                    expect(dialog._uploadButton.disabled).toBe(true);
                });

                it('Uploads the file attachment', function() {
                    expect(dialog._uploadButton.disabled).toBe(true);

                    dialog._$path
                        .val('fakefile')
                        .trigger('change');

                    expect(dialog._updateUploadButtonEnabledState)
                        .toHaveBeenCalled();
                    expect(dialog._uploadButton.disabled).toBe(false);

                    dialog._uploadButton.el.click();
                    expect(dialog.send).toHaveBeenCalled();
                });
            });
        });

        it('Dialog for updating an existing file attachment', function() {
            dialog = new UploadAttachmentView({
                attachmentHistoryID: 14,
                presetCaption: 'fakecaption',
                reviewRequestEditor: editor,
            });
            dialog.render();

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
