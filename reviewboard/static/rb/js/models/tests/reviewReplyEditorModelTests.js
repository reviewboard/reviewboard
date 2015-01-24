suite('rb/models/ReviewReplyEditor', function() {
    var reviewReply,
        review,
        editor;

    beforeEach(function() {
        review = new RB.Review({
            loaded: true,
            links: {
                replies: {
                    href: '/api/review/123/replies/'
                }
            }
        });

        reviewReply = review.createReply();

        spyOn(review, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });

        spyOn(reviewReply, 'ensureCreated')
            .andCallFake(function(options, context) {
                options.success.call(context);
            });

        spyOn(reviewReply, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });
    });

    describe('Event handling', function() {
        describe('reviewReply changes', function() {
            beforeEach(function() {
                editor = new RB.ReviewReplyEditor({
                    contextType: 'body_top',
                    review: review,
                    reviewReply: reviewReply,
                    text: 'My Text'
                });
            });

            it('Sets up events on new reviewReply', function() {
                var reviewReply = new RB.ReviewReply();

                spyOn(reviewReply, 'on');

                editor.set('reviewReply', reviewReply);
                expect(reviewReply.on.calls.length).toBe(2);
                expect(reviewReply.on.calls[0].args[0]).toBe('destroyed');
                expect(reviewReply.on.calls[1].args[0]).toBe('published');
            });

            it('Removes events from old reviewReply', function() {
                spyOn(reviewReply, 'off');

                editor.set('reviewReply', new RB.ReviewReply());
                expect(reviewReply.off).toHaveBeenCalledWith(null, null,
                                                             editor);
            });
        });
    });

    describe('Methods', function() {
        describe('save', function() {
            function testBodySave(options) {
                editor = new RB.ReviewReplyEditor({
                    contextType: options.contextType,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text'
                });

                spyOn(editor, 'trigger');
                spyOn(reviewReply, 'save')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

                editor.save();

                expect(editor.get('replyObject')).toBe(reviewReply);
                expect(editor.get('hasDraft')).toBe(true);
                expect(editor.get('text')).toBe('My Text');
                expect(editor.get('richText')).toBe(true);
                expect(reviewReply.get(options.textAttr)).toBe('My Text');
                expect(reviewReply.get(options.richTextAttr)).toBe(
                    options.richText);
                expect(reviewReply.ready).toHaveBeenCalled();
                expect(reviewReply.save).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('saving');
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            }

            function testCommentSave(options) {
                var replyObject;

                editor = new RB.ReviewReplyEditor({
                    contextType: options.contextType,
                    hasDraft: false,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text'
                });

                spyOn(editor, 'trigger');
                spyOn(options.model.prototype, 'ready')
                    .andCallFake(function(options, context) {
                        options.ready.call(context);
                    });
                spyOn(options.model.prototype, 'save')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

                editor.save();

                replyObject = editor.get('replyObject');

                expect(editor.get('hasDraft')).toBe(true);
                expect(editor.get('text')).toBe('My Text');
                expect(editor.get('richText')).toBe(true);
                expect(replyObject instanceof options.model).toBe(true);
                expect(replyObject.get('text')).toBe('My Text');
                expect(replyObject.get('richText')).toBe(options.richText);
                expect(options.model.prototype.ready).toHaveBeenCalled();
                expect(options.model.prototype.save).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('saving');
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            }

            it('With existing reply object', function() {
                var replyObject = new RB.DiffCommentReply();

                editor = new RB.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    hasDraft: false,
                    replyObject: replyObject,
                    review: review,
                    reviewReply: reviewReply,
                    text: 'My Text'
                });

                spyOn(editor, 'trigger');
                spyOn(replyObject, 'ready')
                    .andCallFake(function(options, context) {
                        options.ready.call(context);
                    });
                spyOn(replyObject, 'save')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

                editor.save();

                expect(editor.get('hasDraft')).toBe(true);
                expect(editor.get('replyObject')).toBe(replyObject);
                expect(replyObject.get('text')).toBe('My Text');
                expect(replyObject.ready).toHaveBeenCalled();
                expect(replyObject.save).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('saving');
                expect(editor.trigger).toHaveBeenCalledWith('saved');
            });

            it('With empty text', function() {
                var replyObject = new RB.DiffCommentReply({
                    text: 'Orig Text'
                });

                editor = new RB.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    review: review,
                    reviewReply: reviewReply
                });

                spyOn(editor, 'trigger');
                spyOn(editor, 'resetStateIfEmpty');
                spyOn(replyObject, 'ready')
                    .andCallFake(function(options, context) {
                        options.ready.call(context);
                    });
                spyOn(replyObject, 'save');

                editor.set({
                    hasDraft: false,
                    replyObject: replyObject,
                    text: ''
                });
                editor.save();

                expect(editor.get('hasDraft')).toBe(false);
                expect(editor.get('replyObject')).toBe(replyObject);
                expect(replyObject.get('text')).toBe('Orig Text');
                expect(replyObject.ready).toHaveBeenCalled();
                expect(replyObject.save).not.toHaveBeenCalled();
                expect(editor.resetStateIfEmpty).toHaveBeenCalled();
                expect(editor.trigger).toHaveBeenCalledWith('saving');
            });

            describe('With body_top', function() {
                function testSave(richText) {
                    testBodySave({
                        contextType: 'body_top',
                        textAttr: 'bodyTop',
                        richTextAttr: 'bodyTopRichText',
                        richText: richText
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });

            describe('With body_bottom', function() {
                function testSave(richText) {
                    testBodySave({
                        contextType: 'body_bottom',
                        textAttr: 'bodyBottom',
                        richTextAttr: 'bodyBottomRichText',
                        richText: richText
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });

            describe('With diff comments', function() {
                function testSave(richText) {
                    testCommentSave({
                        contextType: 'diff_comments',
                        model: RB.DiffCommentReply,
                        richText: richText
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });

            describe('With file attachment comments', function() {
                function testSave(richText) {
                    testCommentSave({
                        contextType: 'file_attachment_comments',
                        model: RB.FileAttachmentCommentReply,
                        richText: richText
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });

            describe('With screenshot comments', function() {
                function testSave(richText) {
                    testCommentSave({
                        contextType: 'screenshot_comments',
                        model: RB.ScreenshotCommentReply,
                        richText: richText
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });
        });

        describe('resetStateIfEmpty', function() {
            var replyObject;

            beforeEach(function() {
                replyObject = new RB.DiffCommentReply();

                editor = new RB.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    hasDraft: true,
                    replyObject: replyObject,
                    review: review,
                    reviewReply: reviewReply
                });

                spyOn(editor, 'trigger');
                spyOn(replyObject, 'destroy')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });
            });

            it('Without empty text', function() {
                editor.set('text', 'My Text');
                editor.resetStateIfEmpty();

                expect(replyObject.destroy).not.toHaveBeenCalled();
                expect(editor.get('hasDraft')).toBe(true);
                expect(editor.trigger).not.toHaveBeenCalledWith('resetState');
            });

            describe('With empty text', function() {
                it('With no reply object', function() {
                    editor.set('replyObject', null);
                    editor.resetStateIfEmpty();

                    expect(replyObject.destroy).not.toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });

                it('With new reply object', function() {
                    replyObject.id = null;
                    editor.resetStateIfEmpty();

                    expect(replyObject.destroy).not.toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });

                it('With existing reply object', function() {
                    replyObject.id = 123;
                    editor.resetStateIfEmpty();

                    expect(replyObject.destroy).toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });
            });
        });
    });
});
