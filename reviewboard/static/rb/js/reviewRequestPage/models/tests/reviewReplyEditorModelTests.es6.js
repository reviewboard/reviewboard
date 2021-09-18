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

        spyOn(review, 'ready').and.resolveTo();
        spyOn(reviewReply, 'ensureCreated').and.resolveTo();
        spyOn(reviewReply, 'ready').and.resolveTo();
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
            function testBodySave(options, done) {
                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: options.contextType,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text',
                });

                spyOn(editor, 'trigger');
                spyOn(reviewReply, 'save').and.resolveTo();

                editor.save()
                    .then(() => {
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

                        done();
                    })
                    .catch(err => done.fail(err));
            }

            function testCommentSave(options, done) {
                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: options.contextType,
                    hasDraft: false,
                    review: review,
                    reviewReply: reviewReply,
                    richText: options.richText,
                    text: 'My Text',
                });

                spyOn(editor, 'trigger');
                spyOn(options.model.prototype, 'ready').and.resolveTo();
                spyOn(options.model.prototype, 'save').and.resolveTo();

                editor.save()
                    .then(() => {
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

                        done();
                    })
                    .catch(err => done.fail(err));
            }

            it('With existing reply object', function(done) {
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
                spyOn(replyObject, 'ready').and.resolveTo();
                spyOn(replyObject, 'save').and.resolveTo();

                editor.save()
                    .then(() => {
                        expect(editor.get('hasDraft')).toBe(true);
                        expect(editor.get('replyObject')).toBe(replyObject);
                        expect(replyObject.get('text')).toBe('My Text');
                        expect(replyObject.ready).toHaveBeenCalled();
                        expect(replyObject.save).toHaveBeenCalled();
                        expect(editor.trigger).toHaveBeenCalledWith('saving');
                        expect(editor.trigger).toHaveBeenCalledWith('saved');

                        done();
                    })
                    .catch(err => done.fail(err));
            });

            it('With empty text', function(done) {
                const replyObject = new RB.DiffCommentReply({
                    text: 'Orig Text',
                });

                editor = new RB.ReviewRequestPage.ReviewReplyEditor({
                    contextType: 'diff_comments',
                    review: review,
                    reviewReply: reviewReply,
                });

                spyOn(editor, 'trigger');
                spyOn(editor, 'resetStateIfEmpty').and.resolveTo();
                spyOn(replyObject, 'ready').and.resolveTo();
                spyOn(replyObject, 'save');

                editor.set({
                    hasDraft: false,
                    replyObject: replyObject,
                    text: '',
                });
                editor.save()
                    .then(() => {
                        expect(editor.get('hasDraft')).toBe(false);
                        expect(editor.get('replyObject')).toBe(replyObject);
                        expect(replyObject.get('text')).toBe('Orig Text');
                        expect(replyObject.ready).toHaveBeenCalled();
                        expect(replyObject.save).not.toHaveBeenCalled();
                        expect(editor.resetStateIfEmpty).toHaveBeenCalled();
                        expect(editor.trigger).toHaveBeenCalledWith('saving');

                        done();
                    })
                    .catch(err => done.fail(err));
            });

            describe('With body_top', function() {
                function testSave(richText, done) {
                    testBodySave({
                        contextType: 'body_top',
                        textAttr: 'bodyTop',
                        richTextAttr: 'bodyTopRichText',
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
                });
            });

            describe('With body_bottom', function() {
                function testSave(richText, done) {
                    testBodySave({
                        contextType: 'body_bottom',
                        textAttr: 'bodyBottom',
                        richTextAttr: 'bodyBottomRichText',
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
                });
            });

            describe('With diff comments', function() {
                function testSave(richText, done) {
                    testCommentSave({
                        contextType: 'diff_comments',
                        model: RB.DiffCommentReply,
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
                });
            });

            describe('With file attachment comments', function() {
                function testSave(richText, done) {
                    testCommentSave({
                        contextType: 'file_attachment_comments',
                        model: RB.FileAttachmentCommentReply,
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
                });
            });

            describe('With general comments', function() {
                function testSave(richText, done) {
                    testCommentSave({
                        contextType: 'general_comments',
                        model: RB.GeneralCommentReply,
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
                });
            });

            describe('With screenshot comments', function() {
                function testSave(richText, done) {
                    testCommentSave({
                        contextType: 'screenshot_comments',
                        model: RB.ScreenshotCommentReply,
                        richText: richText,
                    }, done);
                }

                it('richText=true', function(done) {
                    testSave(true, done);
                });

                it('richText=false', function(done) {
                    testSave(false, done);
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
                spyOn(replyObject, 'destroy').and.resolveTo();
                spyOn(reviewReply, 'discardIfEmpty').and.resolveTo(true);
            });

            it('Without empty text', async function() {
                editor.set('text', 'My Text');

                await editor.resetStateIfEmpty();

                expect(replyObject.destroy).not.toHaveBeenCalled();
                expect(editor.get('hasDraft')).toBe(true);
                expect(editor.trigger).not.toHaveBeenCalledWith('resetState');
            });

            describe('With empty text', function() {
                it('With no reply object', async function() {
                    editor.set('replyObject', null);

                    await editor.resetStateIfEmpty();

                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                    expect(replyObject.destroy).not.toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                });

                it('With new reply object', async function() {
                    replyObject.set('id', null);

                    await editor.resetStateIfEmpty();

                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                    expect(replyObject.destroy).not.toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                });

                it('With existing reply object', async function() {
                    replyObject.set('id', 123);

                    await editor.resetStateIfEmpty();

                    expect(replyObject.destroy).toHaveBeenCalled();
                    expect(editor.get('hasDraft')).toBe(false);
                    expect(editor.trigger).toHaveBeenCalledWith('resetState');
                });

                describe('With context type', function() {
                    beforeEach(function() {
                        replyObject.set('id', 123);

                        spyOn(editor, '_resetState').and.resolveTo();
                    });

                    it('body_top', async function() {
                        editor.set('contextType', 'body_top');

                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).not.toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith(true);
                    });

                    it('body_bottom', async function() {
                        editor.set('contextType', 'body_bottom');

                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).not.toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith(true);
                    });

                    it('diff_comments', async function() {
                        editor.set('contextType', 'diff_comments');

                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('file_attachment_comments', async function() {
                        editor.set('contextType', 'file_attachment_comments');

                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('general_comments', async function() {
                        editor.set('contextType', 'general_comments');
                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });

                    it('screenshot_comments', async function() {
                        editor.set('contextType', 'screenshot_comments');

                        await editor.resetStateIfEmpty();

                        expect(replyObject.destroy).toHaveBeenCalled();
                        expect(editor._resetState).toHaveBeenCalledWith();
                    });
                });
            });
        });
    });
});
