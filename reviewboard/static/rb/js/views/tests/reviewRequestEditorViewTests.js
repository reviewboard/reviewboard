describe('views/ReviewRequestEditorView', function() {
    var reviewRequest,
        editor,
        view,
        template = _.template([
            '<div>',
            ' <div id="review-request-warning"></div>',
            ' <div>',
            '  <div id="file-list"><br /></div>',
            ' </div>',
            ' <div>',
            '  <div id="screenshot-thumbnails"><br /></div>',
            ' </div>',
            '</div>'
        ].join('')),
        screenshotThumbnailTemplate = _.template([
            '<div class="screenshot-container" data-screenshot-id="<%= id %>">',
            ' <div class="screenshot-caption">',
            '  <a class="edit"></a>',
            ' </div>',
            ' <a class="delete">X</a>',
            '</div>'
        ].join('')),
        $warning,
        $filesContainer,
        $screenshotsContainer;

    beforeEach(function() {
        var $el = $(template()).appendTo($testsScratch);

        reviewRequest = new RB.ReviewRequest({
            id: 123
        });

        editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest
        });

        view = new RB.ReviewRequestEditorView({
            el: $el,
            model: editor
        });

        $warning = $testsScratch.find('#review-request-warning');
        $filesContainer = $testsScratch.find('#file-list');
        $screenshotsContainer = $testsScratch.find('#screenshot-thumbnails');
    });

    describe('Banners', function() {
        beforeEach(function() {
            view.render();
        });

        describe('Draft banner', function() {
            beforeEach(function() {
                RB.draftBanner = $('<div>')
                    .hide()
                    .appendTo($testsScratch);
                RB.draftBannerButtons = $('<button/>')
                    .appendTo(RB.draftBanner);
            });

            describe('Visibility', function() {
                it('Hidden when saving', function() {
                    expect(RB.draftBanner.is(':visible')).toBe(false);
                    editor.trigger('saving');
                    expect(RB.draftBanner.is(':visible')).toBe(false);
                });

                it('Show when saved', function() {
                    expect(RB.draftBanner.is(':visible')).toBe(false);
                    editor.trigger('saved');
                    expect(RB.draftBanner.is(':visible')).toBe(true);
                });
            });

            describe('Button states', function() {
                it('Enabled by default', function() {
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(false);
                });

                it('Disabled when saving', function() {
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(false);
                    editor.trigger('saving');
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(true);
                });

                it('Enabled when saved', function() {
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(false);
                    editor.trigger('saving');
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(true);
                    editor.trigger('saved');
                    expect(RB.draftBannerButtons.prop('disabled')).toBe(false);
                });
            });
        });
    });

    describe('File attachments', function() {
        it('Rendering when added', function() {
            spyOn(RB.FileAttachmentThumbnail.prototype, 'render')
                .andCallThrough();

            expect($filesContainer.find('.file-container').length).toBe(0);

            view.render();
            editor.createFileAttachment();

            expect(RB.FileAttachmentThumbnail.prototype.render)
                .toHaveBeenCalled();
            expect($filesContainer.find('.file-container').length).toBe(1);
        });

        describe('Importing on render', function() {
            it('No file attachments', function() {
                view.render();

                expect(editor.fileAttachments.length).toBe(0);
            });

            describe('With file attachments', function() {
                var $thumbnail,
                    fileAttachment;

                beforeEach(function() {
                    $thumbnail = $('<div/>')
                        .addClass(RB.FileAttachmentThumbnail.prototype.className)
                        .data('file-id', 42)
                        .html(RB.FileAttachmentThumbnail.prototype.template(
                            _.extend({
                                downloadURL: '',
                                iconURL: '',
                                deleteImageURL: '',
                                filename: '',
                                caption: ''
                             })))
                        .appendTo($filesContainer);

                    spyOn(RB.FileAttachmentThumbnail.prototype, 'render')
                        .andCallThrough();

                    expect($filesContainer.find('.file-container').length).toBe(1);
                });

                it('Without caption', function() {
                    view.render();

                    expect(RB.FileAttachmentThumbnail.prototype.render)
                        .toHaveBeenCalled();
                    expect(editor.fileAttachments.length).toBe(1);

                    fileAttachment = editor.fileAttachments.at(0);
                    expect(fileAttachment.id).toBe(42);
                    expect(fileAttachment.get('caption')).toBe(null);
                    expect($filesContainer.find('.file-container').length).toBe(1);
                });

                it('With caption', function() {
                    $thumbnail.find('.file-caption .edit')
                        .removeClass('empty-caption')
                        .text('my caption');

                    view.render();

                    expect(RB.FileAttachmentThumbnail.prototype.render)
                        .toHaveBeenCalled();
                    expect(editor.fileAttachments.length).toBe(1);

                    fileAttachment = editor.fileAttachments.at(0);
                    expect(fileAttachment.id).toBe(42);
                    expect(fileAttachment.get('caption')).toBe('my caption');
                    expect($filesContainer.find('.file-container').length).toBe(1);
                });
            });
        });

        describe('Events', function() {
            var $thumbnail,
                fileAttachment;

            beforeEach(function() {
                view.render();
                fileAttachment = editor.createFileAttachment();

                $thumbnail = $($filesContainer.find('.file-container')[0]);
                expect($thumbnail.length).toBe(1);
            });

            describe('beginEdit', function() {
                it('Increment edit count', function() {
                    expect(editor.get('editCount')).toBe(0);

                    $thumbnail.find('.file-caption .edit')
                        .inlineEditor('startEdit');

                    expect(editor.get('editCount')).toBe(1);
                });
            });

            describe('endEdit', function() {
                describe('Decrement edit count', function() {
                    var $caption;

                    beforeEach(function() {
                        expect(editor.get('editCount')).toBe(0);

                        $caption = $thumbnail.find('.file-caption .edit')
                            .inlineEditor('startEdit');
                    });

                    it('On cancel', function() {
                        $caption.inlineEditor('cancel');
                        expect(editor.get('editCount')).toBe(0);
                    });

                    it('On submit', function() {
                        spyOn(fileAttachment, 'ready')
                            .andCallFake(function(options, context) {
                                options.ready.call(context);
                            });
                        spyOn(fileAttachment, 'save');

                        $thumbnail.find('input')
                            .val('Foo')
                            .triggerHandler('keyup');

                        $caption.inlineEditor('submit');

                        expect(editor.get('editCount')).toBe(0);
                    });
                });
            });
        });
    });

    describe('Screenshots', function() {
        describe('Importing on render', function() {
            it('No screenshots', function() {
                view.render();

                expect(editor.screenshots.length).toBe(0);
            });

            it('With screenshots', function() {
                $screenshotsContainer.append(
                    screenshotThumbnailTemplate({
                        id: 42
                    }));

                spyOn(RB.ScreenshotThumbnail.prototype, 'render')
                    .andCallThrough();

                view.render();

                expect(RB.ScreenshotThumbnail.prototype.render)
                    .toHaveBeenCalled();
                expect(editor.screenshots.length).toBe(1);
                expect(editor.screenshots.at(0).id).toBe(42);
            });
        });

        describe('Events', function() {
            var $thumbnail,
                screenshot;

            beforeEach(function() {
                $thumbnail = $(screenshotThumbnailTemplate({
                        id: 42
                    }))
                    .appendTo($screenshotsContainer);

                view.render();

                screenshot = editor.screenshots.at(0);
            });

            describe('beginEdit', function() {
                it('Increment edit count', function() {
                    expect(editor.get('editCount')).toBe(0);

                    $thumbnail.find('.screenshot-caption .edit')
                        .inlineEditor('startEdit');

                    expect(editor.get('editCount')).toBe(1);
                });
            });

            describe('endEdit', function() {
                describe('Decrement edit count', function() {
                    var $caption;

                    beforeEach(function() {
                        expect(editor.get('editCount')).toBe(0);

                        $caption = $thumbnail.find('.screenshot-caption .edit')
                            .inlineEditor('startEdit')
                    });

                    it('On cancel', function() {
                        $caption.inlineEditor('cancel');
                        expect(editor.get('editCount')).toBe(0);
                    });

                    it('On submit', function() {
                        spyOn(screenshot, 'ready')
                            .andCallFake(function(options, context) {
                                options.ready.call(context);
                            });
                        spyOn(screenshot, 'save');

                        $thumbnail.find('input')
                            .val('Foo')
                            .triggerHandler('keyup');

                        $caption.inlineEditor('submit');

                        expect(editor.get('editCount')).toBe(0);
                    });
                });
            });
        });
    });
});
