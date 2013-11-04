describe('views/ReviewDialogView', function() {
    var baseEmptyCommentListPayload = {
            stat: 'ok',
            total_results: 0,
            links: {}
        },
        emptyDiffCommentsPayload = _.defaults({
            diff_comments: []
        }, baseEmptyCommentListPayload),
        emptyFileAttachmentCommentsPayload = _.defaults({
            file_attachment_comments: []
        }, baseEmptyCommentListPayload),
        emptyScreenshotCommentsPayload = _.defaults({
            screenshot_comments: []
        }, baseEmptyCommentListPayload),
        baseCommentPayload = {
            id: 1,
            issue_opened: true,
            issue_status: 'opened',
            text: 'My comment'
        },
        diffCommentPayload = _.defaults({
            first_line: 10,
            num_lines: 5,
            filediff: {
                id: 1,
                source_file: 'my-file',
                dest_file: 'my-file',
                source_revision: '1'
            },
            interfilediff: {
                id: 2,
                source_file: 'my-file',
                dest_file: 'my-file',
                source_revision: '2'
            }
        }, baseCommentPayload),
        fileAttachmentCommentPayload = _.defaults({
            extra_data: {},
            link_text: 'my-link-text',
            thumbnail_html: '<blink>Boo</blink>',
            review_url: '/review-ui/',
            file_attachment: {
                id: 10,
                filename: 'file.txt',
                icon_url: 'data:image/gif;base64,'
            }
        }, baseCommentPayload),
        screenshotCommentPayload = _.defaults({
            x: 10,
            y: 20,
            w: 30,
            h: 40,
            thumbnail_url: 'data:image/gif;base64,',
            screenshot: {
                id: 10,
                caption: 'My caption',
                filename: 'image.png',
                review_url: '/review-ui/'
            }
        }, baseCommentPayload),
        reviewRequestEditor,
        review,
        dlg;

    function createCommentDialog() {
        return RB.ReviewDialogView.create({
            review: review,
            container: $testsScratch,
            reviewRequestEditor: reviewRequestEditor
        });
    }

    beforeEach(function() {
        var origMove = $.fn.move,
            reviewRequest = new RB.ReviewRequest({
                summary: 'My Review Request'
            });

        reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest
        });

        review = new RB.Review({
            parentObject: reviewRequest
        });

        spyOn(review, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });

        /*
         * modalBox uses move(... 'fixed') for all positioning, which will
         * cause the box to flash on screen during tests. Override this to
         * disallow fixed.
         */
        spyOn($.fn, 'move').andCallFake(function(x, y, pos) {
            if (pos === 'fixed') {
                pos = 'absolute';
            }

            return origMove.call(this, x, y, pos);
        });

        /* Prevent these from being called. */
        spyOn(RB.DiffFragmentQueueView.prototype, 'queueLoad');
        spyOn(RB.DiffFragmentQueueView.prototype, 'loadFragments');
    });

    afterEach(function() {
        RB.ReviewDialogView._instance = null;
    });

    describe('Class methods', function() {
        describe('create', function() {
            it('Without a review', function() {
                expect(function() {
                    RB.ReviewDialogView.create({
                        container: $testsScratch,
                        reviewRequestEditor: reviewRequestEditor
                    });
                }).toThrow();

                expect(RB.ReviewDialogView._instance).toBeFalsy();
                expect($testsScratch.children().length).toBe(0);
            });

            it('With a review', function() {
                dlg = createCommentDialog();

                expect(dlg).toBeTruthy();
                expect(RB.ReviewDialogView._instance).toBe(dlg);

                /* One for the dialog, one for the background box. */
                expect($testsScratch.children().length).toBe(2);
            });

            it('With existing instance', function() {
                dlg = createCommentDialog();

                expect(createCommentDialog).toThrow();

                expect(RB.ReviewDialogView._instance).toBe(dlg);
                expect($testsScratch.children().length).toBe(2);
            });
        });
    });

    describe('Instances', function() {
        describe('Methods', function() {
            it('close', function() {
                dlg = createCommentDialog();
                expect($testsScratch.children().length).toBe(2);

                dlg.close();
                expect($testsScratch.children().length).toBe(0);
                expect(RB.ReviewDialogView._instance).toBe(null);
            });
        });

        describe('Loading', function() {
            it('With new review', function() {
                expect(review.isNew()).toBe(true);

                dlg = RB.ReviewDialogView.create({
                    review: review,
                    container: $testsScratch,
                    reviewRequestEditor: reviewRequestEditor
                });

                expect(dlg._bodyTopEditor.getText()).toBe('');
                expect(dlg._bodyBottomEditor.getText()).toBe('');
                expect(dlg._$shipIt.prop('checked')).toBe(false);
                expect(dlg._bodyBottomEditor.$el.is(':visible')).toBe(false);
                expect(dlg._$spinner).toBe(null);
            });

            describe('With existing review', function() {
                var bodyTopText = 'My body top',
                    bodyBottomText = 'My body bottom',
                    shipIt = true,
                    fileAttachmentCommentsPayload,
                    diffCommentsPayload,
                    screenshotCommentsPayload,
                    commentView;

                beforeEach(function() {
                    review.set({
                        bodyTop: bodyTopText,
                        bodyBottom: bodyBottomText,
                        shipIt: shipIt,
                        loaded: true,
                        id: 42,
                        links: {
                            diff_comments: {
                                href: '/diff-comments/'
                            },
                            file_attachment_comments: {
                                href: '/file-attachment-comments/'
                            },
                            screenshot_comments: {
                                href: '/screenshot-comments/'
                            }
                        }
                    });

                    diffCommentsPayload =
                        _.clone(emptyDiffCommentsPayload);
                    screenshotCommentsPayload =
                        _.clone(emptyScreenshotCommentsPayload);
                    fileAttachmentCommentsPayload =
                        _.clone(emptyFileAttachmentCommentsPayload);

                    spyOn($, 'ajax').andCallFake(function(options) {
                        if (options.url === '/file-attachment-comments/') {
                            options.success(fileAttachmentCommentsPayload);
                        } else if (options.url === '/diff-comments/') {
                            options.success(diffCommentsPayload);
                        } else if (options.url === '/screenshot-comments/') {
                            options.success(screenshotCommentsPayload);
                        }
                    });
                });

                it('Review properties', function() {
                    dlg = RB.ReviewDialogView.create({
                        review: review,
                        container: $testsScratch,
                        reviewRequestEditor: reviewRequestEditor
                    });

                    expect(dlg._bodyTopEditor.getText()).toBe(bodyTopText);
                    expect(dlg._bodyBottomEditor.getText())
                        .toBe(bodyBottomText);
                    expect(dlg._$shipIt.prop('checked')).toBe(shipIt);
                    expect(dlg._bodyBottomEditor.$el.is(':visible'))
                        .toBe(false);
                    expect(dlg._$comments.children().length).toBe(0);
                    expect(dlg._$spinner).toBe(null);
                });

                it('Diff comments', function() {
                    var diffQueueProto = RB.DiffFragmentQueueView.prototype;

                    diffCommentsPayload.total_results = 1;
                    diffCommentsPayload.diff_comments = [diffCommentPayload];

                    dlg = RB.ReviewDialogView.create({
                        review: review,
                        container: $testsScratch,
                        reviewRequestEditor: reviewRequestEditor
                    });

                    expect($.ajax).toHaveBeenCalled();
                    expect(diffQueueProto.queueLoad.calls.length).toBe(1);
                    expect(diffQueueProto.loadFragments).toHaveBeenCalled();
                    expect(dlg._commentViews.length).toBe(1);

                    commentView = dlg._commentViews[0];
                    expect(commentView.textEditor.getText()).toBe(
                        diffCommentPayload.text);
                    expect(commentView.$issueOpened.prop('checked'))
                        .toBe(diffCommentPayload.issue_opened);

                    expect(dlg._bodyBottomEditor.$el.is(':visible')).toBe(true);
                    expect(dlg._$spinner).toBe(null);
                });

                it('File attachment comments', function() {
                    fileAttachmentCommentsPayload.total_results = 1;
                    fileAttachmentCommentsPayload.file_attachment_comments = [
                        fileAttachmentCommentPayload
                    ];

                    dlg = RB.ReviewDialogView.create({
                        review: review,
                        container: $testsScratch,
                        reviewRequestEditor: reviewRequestEditor
                    });

                    expect($.ajax).toHaveBeenCalled();
                    expect(dlg._commentViews.length).toBe(1);

                    commentView = dlg._commentViews[0];
                    expect(commentView.textEditor.getText()).toBe(
                        fileAttachmentCommentPayload.text);
                    expect(commentView.$issueOpened.prop('checked')).toBe(
                        fileAttachmentCommentPayload.issue_opened);
                    expect(commentView.$('img').attr('src')).toBe(
                        fileAttachmentCommentPayload.file_attachment.icon_url);
                    expect(commentView.$('.filename a').attr('href')).toBe(
                        fileAttachmentCommentPayload.review_url);
                    expect(commentView.$('.filename a').text()).toBe(
                        fileAttachmentCommentPayload.link_text);
                    expect(commentView.$('.thumbnail').html()).toBe(
                        fileAttachmentCommentPayload.thumbnail_html);

                    expect(dlg._bodyBottomEditor.$el.is(':visible')).toBe(true);
                    expect(dlg._$spinner).toBe(null);
                });

                it('Screenshot comments', function() {
                    var $img,
                        $filenameA;

                    screenshotCommentsPayload.total_results = 1;
                    screenshotCommentsPayload.screenshot_comments = [
                        screenshotCommentPayload
                    ];

                    dlg = createCommentDialog();

                    expect($.ajax).toHaveBeenCalled();
                    expect(dlg._commentViews.length).toBe(1);

                    commentView = dlg._commentViews[0];
                    expect(commentView.textEditor.getText()).toBe(
                        screenshotCommentPayload.text);
                    expect(commentView.$issueOpened.prop('checked')).toBe(
                        screenshotCommentPayload.issue_opened);

                    $img = commentView.$('img');
                    expect($img.attr('src')).toBe(
                        screenshotCommentPayload.thumbnail_url);
                    expect($img.attr('width')).toBe(
                        screenshotCommentPayload.w.toString());
                    expect($img.attr('height')).toBe(
                        screenshotCommentPayload.h.toString());
                    expect($img.attr('alt')).toBe(
                        screenshotCommentPayload.screenshot.caption);

                    $filenameA = commentView.$('.filename a');
                    expect($filenameA.attr('href')).toBe(
                        screenshotCommentPayload.screenshot.review_url);
                    expect($filenameA.text()).toBe(
                        screenshotCommentPayload.screenshot.caption);

                    expect(dlg._bodyBottomEditor.$el.is(':visible')).toBe(true);
                    expect(dlg._$spinner).toBe(null);
                });
            });
        });

        describe('Saving', function() {
            var fileAttachmentCommentsPayload,
                diffCommentsPayload,
                screenshotCommentsPayload,
                commentView,
                comment;

            function testSaveComment() {
                var newCommentText = 'New commet text',
                    newIssueOpened = false;

                dlg = createCommentDialog();

                expect(dlg._commentViews.length).toBe(1);

                commentView = dlg._commentViews[0];
                comment = commentView.model;

                /* Set some new state for the comment. */
                commentView.textEditor.setText(newCommentText);
                commentView.$issueOpened.prop('checked', newIssueOpened);

                spyOn(comment, 'save');

                dlg._saveReview();

                expect(comment.save).toHaveBeenCalled();
                expect(comment.get('text')).toBe(newCommentText);
                expect(comment.get('issueOpened')).toBe(newIssueOpened);
            }

            beforeEach(function() {
                review.set({
                    loaded: true,
                    id: 42,
                    links: {
                        diff_comments: {
                            href: '/diff-comments/'
                        },
                        file_attachment_comments: {
                            href: '/file-attachment-comments/'
                        },
                        screenshot_comments: {
                            href: '/screenshot-comments/'
                        }
                    }
                });

                diffCommentsPayload =
                    _.clone(emptyDiffCommentsPayload);
                screenshotCommentsPayload =
                    _.clone(emptyScreenshotCommentsPayload);
                fileAttachmentCommentsPayload =
                    _.clone(emptyFileAttachmentCommentsPayload);

                spyOn(review, 'save').andCallFake(
                    function(options, context) {
                        options.success.call(context);
                    });

                spyOn($, 'ajax').andCallFake(function(options) {
                    if (options.url === '/file-attachment-comments/') {
                        options.success(fileAttachmentCommentsPayload);
                    } else if (options.url === '/diff-comments/') {
                        options.success(diffCommentsPayload);
                    } else if (options.url === '/screenshot-comments/') {
                        options.success(screenshotCommentsPayload);
                    }
                });
            });

            it('Review properties', function() {
                var bodyTopText = 'My new body top',
                    bodyBottomText = 'My new body bottom',
                    shipIt = true;

                dlg = createCommentDialog();

                dlg._bodyTopEditor.setText(bodyTopText);
                dlg._bodyBottomEditor.setText(bodyBottomText);
                dlg._$shipIt.prop('checked', shipIt);
                dlg._saveReview();

                expect(dlg._bodyTopEditor.getText()).toBe(bodyTopText);
                expect(dlg._bodyBottomEditor.getText()).toBe(bodyBottomText);
                expect(dlg._$shipIt.prop('checked')).toBe(shipIt);
                expect(review.save).toHaveBeenCalled();
            });

            it('Diff comments', function() {
                diffCommentsPayload.total_results = 1;
                diffCommentsPayload.diff_comments = [diffCommentPayload];

                testSaveComment();
            });

            it('File attachment comments', function() {
                fileAttachmentCommentsPayload.total_results = 1;
                fileAttachmentCommentsPayload.file_attachment_comments = [
                    fileAttachmentCommentPayload
                ];

                testSaveComment();
            });

            it('Screenshot comments', function() {
                screenshotCommentsPayload.total_results = 1;
                screenshotCommentsPayload.screenshot_comments = [
                    screenshotCommentPayload
                ];

                testSaveComment();
            });
        });
    });
});
