suite('rb/reviewRequestPage/models/ReviewReplyEditor', function() {
    let reviewReply;
    let review;
    let editor;

    beforeEach(function() {
        review = new RB.Review({
            loaded: true,
            links: {
                replies: {
                    href: '/api/review/123/replies/',
                },
            },
        });

        reviewReply = review.createReply();

        spyOn(review, 'ready').and.callFake(
            (options, context) => options.ready.call(context));

        spyOn(reviewReply, 'ensureCreated').and.callFake(
            (options, context) => options.success.call(context));

        spyOn(reviewReply, 'ready').and.callFake(
            (options, context) => options.ready.call(context));
    });

    describe('Event handling', function() {
        describe('reviewReply changes', function() {
            beforeEach(function() {
                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: 'body_top',
                    review: review,
                    reviewReply: reviewReply,
                    text: 'My Text',
                });
            });

            it('Sets up events on new reviewReply', function() {
                spyOn(editor, 'listenTo').and.callThrough();

                const reviewReply = new RB.ReviewReply();
                editor.set('reviewReply', reviewReply);

                expect(editor.listenTo.calls.count()).toEqual(2);
                expect(editor.listenTo.calls.argsFor(0)[1]).toEqual('destroyed');
                expect(editor.listenTo.calls.argsFor(1)[1]).toEqual('published');
            });

            it('Removes events from old reviewReply', function() {
                editor.set('reviewReply', new RB.ReviewReply());

                expect(editor._listeningTo.hasOwnProperty(reviewReply._listenId))
                    .toBe(false);
            });
        });
    });

    describe('Methods', function() {
        describe('save', function() {
            function testBodySave(options) {
                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: options.contextType,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text',
                });

                spyOn(editor, 'trigger');
                spyOn(reviewReply, 'save').and.callFake(
                    (options, context) => options.success.call(context));

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
                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: options.contextType,
                    hasDraft: false,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text',
                });

                spyOn(editor, 'trigger');
                spyOn(options.model.prototype, 'ready').and.callFake(
                    (options, context) => options.ready.call(context));
                spyOn(options.model.prototype, 'save').and.callFake(
                    (options, context) => options.success.call(context));

                editor.save();

                const replyObject = editor.get('replyObject');

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
                const replyObject = new RB.DiffCommentReply();

                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    hasDraft: false,
                    replyObject: replyObject,
                    review: review,
                    reviewReply: reviewReply,
                    text: 'My Text',
                });

                spyOn(editor, 'trigger');
                spyOn(replyObject, 'ready').and.callFake(
                    (options, context) => options.ready.call(context));
                spyOn(replyObject, 'save').and.callFake(
                    (options, context) => options.success.call(context));

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
                const replyObject = new RB.DiffCommentReply({
                    text: 'Orig Text',
                });

                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    review: review,
                    reviewReply: reviewReply,
                });

                spyOn(editor, 'trigger');
                spyOn(editor, 'resetStateIfEmpty');
                spyOn(replyObject, 'ready').and.callFake(
                    (options, context) => options.ready.call(context));
                spyOn(replyObject, 'save');

                editor.set({
                    hasDraft: false,
                    replyObject: replyObject,
                    text: '',
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
                        richText: richText,
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
                        richText: richText,
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
                        richText: richText,
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
                        richText: richText,
                    });
                }

                it('richText=true', function() {
                    testSave(true);
                });

                it('richText=false', function() {
                    testSave(false);
                });
            });

            describe('With general comments', function() {
                function testSave(richText) {
                    testCommentSave({
                        contextType: 'general_comments',
                        model: RB.GeneralCommentReply,
                        richText: richText,
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
                        richText: richText,
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
            let replyObject;

            beforeEach(function() {
                replyObject = new RB.DiffCommentReply();

                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    hasDraft: true,
                    replyObject: replyObject,
                    review: review,
                    reviewReply: reviewReply,
                });

                spyOn(editor, 'trigger');
                spyOn(replyObject, 'destroy').and.callFake(
                    (options, context) => options.success.call(context));
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
                    replyObject.set('id', null);
                    editor.resetStateIfEmpty();

                    expect(replyObject.destroy).not.toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });

                it('With existing reply object', function() {
                    replyObject.set('id', 123);
                    editor.resetStateIfEmpty();

                    expect(replyObject.destroy).toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });

                describe('With context type', function() {
                    beforeEach(function() {
                        replyObject.set('id', 123);

                        spyOn(editor, '_resetState');
                        spyOn(reviewReply, 'discardIfEmpty');
                    });

                    it('body_top', function() {
                        editor.set('contextType', 'body_top');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).not.toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith(true);
                    });

                    it('body_bottom', function() {
                        editor.set('contextType', 'body_bottom');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).not.toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith(true);
                    });

                    it('diff_comments', function() {
                        editor.set('contextType', 'diff_comments');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('file_attachment_comments', function() {
                        editor.set('contextType', 'file_attachment_comments');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('general_comments', function() {
                        editor.set('contextType', 'general_comments');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('screenshot_comments', function() {
                        editor.set('contextType', 'screenshot_comments');
                        editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });
                });
            });
        });
    });
});
