suite('rb/views/ReviewDialogView', function() {
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

    function createReviewDialog() {
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
                dlg = createReviewDialog();

                expect(dlg).toBeTruthy();
                expect(RB.ReviewDialogView._instance).toBe(dlg);

                /* One for the dialog, one for the background box. */
                expect($testsScratch.children().length).toBe(2);
            });

            it('With existing instance', function() {
                dlg = createReviewDialog();

                expect(createReviewDialog).toThrow();

                expect(RB.ReviewDialogView._instance).toBe(dlg);
                expect($testsScratch.children().length).toBe(2);
            });
        });
    });

    describe('Instances', function() {
        describe('Methods', function() {
            it('close', function() {
                dlg = createReviewDialog();
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

                expect(dlg._bodyTopView.$editor.text()).toBe('');
                expect(dlg._bodyBottomView.$editor.text()).toBe('');
                expect(dlg._bodyBottomView.$el.is(':visible')).toBe(false);
                expect(dlg._$shipIt.prop('checked')).toBe(false);
                expect(dlg._$spinner).toBe(null);
            });

            describe('With body and top text', function() {
                var bodyTopText = 'My body top',
                    bodyBottomText = 'My body bottom';

                beforeEach(function() {
                    review.set({
                        bodyTop: bodyTopText,
                        bodyBottom: bodyBottomText,
                        loaded: true
                    });
                });

                it('Clearing body bottom hides footer', function() {
                    dlg = RB.ReviewDialogView.create({
                        review: review,
                        container: $testsScratch,
                        reviewRequestEditor: reviewRequestEditor
                    });

                    expect(dlg._bodyBottomView.$editor.text())
                        .toBe(bodyBottomText);
                    expect(dlg._bodyBottomView.$el.is(':visible')).toBe(true);

                    review.set('bodyBottom', '');

                    expect(dlg._bodyBottomView.$el.is(':visible')).toBe(false);
                });
            });

            describe('With existing review', function() {
                var bodyTopText = 'My body top',
                    bodyBottomText = 'My body bottom',
                    shipIt = true,
                    fileAttachmentCommentsPayload,
                    diffCommentsPayload,
                    screenshotCommentsPayload,
                    commentView,
                    ajaxData;

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

                describe('Review properties', function() {
                    function testLoadReview() {
                        dlg = RB.ReviewDialogView.create({
                            review: review,
                            container: $testsScratch,
                            reviewRequestEditor: reviewRequestEditor
                        });

                        expect(dlg._bodyTopView.$editor.text())
                            .toBe(bodyTopText);
                        expect(dlg._bodyBottomView.$editor.text())
                            .toBe(bodyBottomText);
                        expect(dlg._bodyBottomView.$el.is(':visible'))
                            .toBe(true);
                        expect(dlg._$shipIt.prop('checked')).toBe(shipIt);
                        expect(dlg._$comments.children().length).toBe(0);
                        expect(dlg._$spinner).toBe(null);
                    }

                    it('With defaultUseRichText=true', function() {
                        RB.UserSession.instance.set('defaultUseRichText', true);

                        testLoadReview();

                        expect(review.ready.calls[0].args[0].data).toEqual({
                            'force-text-type': 'html',
                            'include-text-types': 'raw,markdown'
                        });
                    });

                    it('With defaultUseRichText=false', function() {
                        RB.UserSession.instance.set('defaultUseRichText',
                                                    false);

                        testLoadReview();

                        expect(review.ready.calls[0].args[0].data)
                            .toEqual({
                                'force-text-type': 'html',
                                'include-text-types': 'raw'
                            });
                    });
                });

                describe('Diff comments', function() {
                    function testLoadDiffComments() {
                        var diffQueueProto = RB.DiffFragmentQueueView.prototype;

                        diffCommentsPayload.total_results = 1;
                        diffCommentsPayload.diff_comments =
                            [diffCommentPayload];

                        dlg = RB.ReviewDialogView.create({
                            review: review,
                            container: $testsScratch,
                            reviewRequestEditor: reviewRequestEditor
                        });

                        expect($.ajax).toHaveBeenCalled();
                        expect($.ajax.calls[2].args[0].url).toBe(
                            '/diff-comments/');
                        ajaxData = $.ajax.calls[2].args[0].data;

                        expect(diffQueueProto.queueLoad.calls.length).toBe(1);
                        expect(diffQueueProto.loadFragments).toHaveBeenCalled();
                        expect(dlg._commentViews.length).toBe(1);

                        commentView = dlg._commentViews[0];
                        expect(commentView.$editor.text())
                            .toBe(diffCommentPayload.text);
                        expect(commentView.$issueOpened.prop('checked'))
                            .toBe(diffCommentPayload.issue_opened);

                        expect(dlg._bodyBottomView.$el.is(':visible'))
                            .toBe(true);
                        expect(dlg._$spinner).toBe(null);
                    }

                    it('With defaultUseRichText=true', function() {
                        RB.UserSession.instance.set('defaultUseRichText', true);

                        testLoadDiffComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'filediff,interfilediff',
                            'order-by': 'filediff,first_line',
                            'force-text-type': 'html',
                            'include-text-types': 'raw,markdown'
                        });
                    });

                    it('With defaultUseRichText=false', function() {
                        RB.UserSession.instance.set('defaultUseRichText',
                                                    false);

                        testLoadDiffComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'filediff,interfilediff',
                            'order-by': 'filediff,first_line',
                            'force-text-type': 'html',
                            'include-text-types': 'raw'
                        });
                    });
                });

                describe('File attachment comments', function() {
                    function testLoadFileAttachmentComments() {
                        fileAttachmentCommentsPayload.total_results = 1;
                        fileAttachmentCommentsPayload.file_attachment_comments =
                            [fileAttachmentCommentPayload];

                        dlg = RB.ReviewDialogView.create({
                            review: review,
                            container: $testsScratch,
                            reviewRequestEditor: reviewRequestEditor
                        });

                        expect($.ajax).toHaveBeenCalled();
                        expect($.ajax.calls[1].args[0].url).toBe(
                            '/file-attachment-comments/');
                        ajaxData = $.ajax.calls[1].args[0].data;

                        expect(dlg._commentViews.length).toBe(1);

                        commentView = dlg._commentViews[0];
                        expect(commentView.$editor.text())
                            .toBe(fileAttachmentCommentPayload.text);
                        expect(commentView.$issueOpened.prop('checked')).toBe(
                            fileAttachmentCommentPayload.issue_opened);
                        expect(commentView.$('.filename a').attr('href')).toBe(
                            fileAttachmentCommentPayload.review_url);
                        expect(commentView.$('.filename a').text()).toBe(
                            fileAttachmentCommentPayload.link_text);
                        expect(commentView.$('.thumbnail').html()).toBe(
                            fileAttachmentCommentPayload.thumbnail_html);

                        expect(dlg._bodyBottomView.$el.is(':visible'))
                            .toBe(true);
                        expect(dlg._$spinner).toBe(null);
                    }

                    it('With defaultUseRichText=true', function() {
                        RB.UserSession.instance.set('defaultUseRichText', true);

                        testLoadFileAttachmentComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'diff_against_file_attachment,' +
                                      'file_attachment',
                            'force-text-type': 'html',
                            'include-text-types': 'raw,markdown'
                        });
                    });

                    it('With defaultUseRichText=false', function() {
                        RB.UserSession.instance.set('defaultUseRichText',
                                                    false);

                        testLoadFileAttachmentComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'diff_against_file_attachment,' +
                                      'file_attachment',
                            'force-text-type': 'html',
                            'include-text-types': 'raw'
                        });
                    });
                });

                describe('Screenshot comments', function() {
                    function testLoadScreenshotComments() {
                        var $img,
                            $filenameA;

                        screenshotCommentsPayload.total_results = 1;
                        screenshotCommentsPayload.screenshot_comments = [
                            screenshotCommentPayload
                        ];

                        dlg = createReviewDialog();

                        expect($.ajax).toHaveBeenCalled();
                        expect($.ajax.calls[0].args[0].url).toBe(
                            '/screenshot-comments/');
                        ajaxData = $.ajax.calls[0].args[0].data;

                        expect(dlg._commentViews.length).toBe(1);

                        commentView = dlg._commentViews[0];
                        expect(commentView.$editor.text())
                            .toBe(screenshotCommentPayload.text);
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

                        expect(dlg._bodyBottomView.$el.is(':visible'))
                            .toBe(true);
                        expect(dlg._$spinner).toBe(null);
                    }

                    it('With defaultUseRichText=true', function() {
                        RB.UserSession.instance.set('defaultUseRichText', true);

                        testLoadScreenshotComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'screenshot',
                            'force-text-type': 'html',
                            'include-text-types': 'raw,markdown'
                        });
                    });

                    it('With defaultUseRichText=false', function() {
                        RB.UserSession.instance.set('defaultUseRichText',
                                                    false);

                        testLoadScreenshotComments();

                        expect(ajaxData).toEqual({
                            'api_format': 'json',
                            'max-results': 50,
                            'expand': 'screenshot',
                            'force-text-type': 'html',
                            'include-text-types': 'raw'
                        });
                    });
                });
            });
        });

        describe('Saving', function() {
            var fileAttachmentCommentsPayload,
                diffCommentsPayload,
                screenshotCommentsPayload,
                commentView,
                comment;

            function testSaveComment(richText) {
                var newCommentText = 'New comment text';

                dlg = createReviewDialog();

                expect(dlg._commentViews.length).toBe(1);

                commentView = dlg._commentViews[0];
                comment = commentView.model;

                spyOn(comment, 'save');

                /* Set some new state for the comment. */
                commentView.$editor
                    .inlineEditor('startEdit')
                    .inlineEditor('setValue', newCommentText);
                commentView.textEditor.setRichText(richText);
                commentView.save();

                expect(comment.save).toHaveBeenCalled();
                expect(comment.get('text')).toBe(newCommentText);
                expect(comment.get('richText')).toBe(richText);
            }

            function testSaveCommentPreventsXSS(richText) {
                var newCommentText =
                    '"><script>window.rbTestFoundXSS = true;</script>';

                delete window.rbTestFoundXSS;

                dlg = createReviewDialog();

                expect(dlg._commentViews.length).toBe(1);

                commentView = dlg._commentViews[0];
                comment = commentView.model;

                spyOn(comment, 'save');

                /* Set some new state for the comment. */
                commentView.$editor
                    .inlineEditor('startEdit')
                    .inlineEditor('setValue', newCommentText);
                commentView.textEditor.setRichText(true);
                commentView.save();

                expect(comment.save).toHaveBeenCalled();
                expect(comment.get('text')).toBe(newCommentText);
                expect(window.rbTestFoundXSS).toBe(undefined);
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
                        if (options && options.success) {
                            options.success.call(context);
                        }
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

            describe('Review properties', function() {
                function testSelfXSS(bodyView, attrName) {
                    var text = '"><script>window.rbTestFoundXSS = true;' +
                               '</script>',
                        editor = bodyView.textEditor;

                    delete window.rbTestFoundXSS;

                    bodyView.openEditor();
                    editor.setText(text);
                    editor.setRichText(true);
                    bodyView.save();

                    expect(editor.getText()).toBe(text);
                    expect(review.save).toHaveBeenCalled();
                    expect(review.get(attrName)).toBe(text);
                    expect(window.rbTestFoundXSS).toBe(undefined);
                }

                beforeEach(function() {
                    dlg = createReviewDialog();
                });

                describe('Body Top', function() {
                    function runTest(richText) {
                        var text = 'My new text',
                            bodyTopEditor = dlg._bodyTopView.textEditor;

                        dlg._bodyTopView.openEditor();
                        bodyTopEditor.setText(text);
                        bodyTopEditor.setRichText(richText);
                        dlg._bodyTopView.save();

                        expect(bodyTopEditor.getText()).toBe(text);
                        expect(review.save).toHaveBeenCalled();
                        expect(review.get('bodyTop')).toBe(text);
                        expect(review.get('bodyTopRichText')).toBe(richText);
                    }

                    it('For Markdown', function() {
                        runTest(true);
                    });

                    it('For plain text', function() {
                        runTest(false);
                    });

                    it('Prevents Self-XSS', function() {
                        testSelfXSS(dlg._bodyTopView, 'bodyTop');
                    });
                });

                describe('Body Bottom', function() {
                    function runTest(richText) {
                        var text = 'My new text',
                            bodyBottomEditor = dlg._bodyBottomView.textEditor;

                        dlg._bodyBottomView.openEditor();
                        bodyBottomEditor.setText(text);
                        bodyBottomEditor.setRichText(richText);
                        dlg._bodyBottomView.save();

                        expect(bodyBottomEditor.getText()).toBe(text);
                        expect(review.save).toHaveBeenCalled();
                        expect(review.get('bodyBottom')).toBe(text);
                        expect(review.get('bodyBottomRichText')).toBe(richText);
                    }

                    it('For Markdown', function() {
                        runTest(true);
                    });

                    it('For plain text', function() {
                        runTest(false);
                    });

                    it('Prevents Self-XSS', function() {
                        testSelfXSS(dlg._bodyBottomView, 'bodyBottom');
                    });
                });

                describe('Ship It', function() {
                    function runTest(shipIt) {
                        dlg._$shipIt.prop('checked', shipIt);
                        dlg._saveReview();

                        expect(dlg._$shipIt.prop('checked')).toBe(shipIt);
                    }

                    it('Checked', function() {
                        runTest(true);
                    });

                    it('Unchecked', function() {
                        runTest(false);
                    });
                });
            });

            describe('Diff comments', function() {
                beforeEach(function() {
                    diffCommentsPayload.total_results = 1;
                    diffCommentsPayload.diff_comments = [diffCommentPayload];
                });

                it('For Markdown', function() {
                    testSaveComment(true);
                });

                it('For plain text', function() {
                    testSaveComment(false);
                });

                it('Prevents Self-XSS', function() {
                    testSaveCommentPreventsXSS();
                });
            });

            describe('File attachment comments', function() {
                beforeEach(function() {
                    fileAttachmentCommentsPayload.total_results = 1;
                    fileAttachmentCommentsPayload.file_attachment_comments = [
                        fileAttachmentCommentPayload
                    ];
                });

                it('For Markdown', function() {
                    testSaveComment(true);
                });

                it('For plain text', function() {
                    testSaveComment(false);
                });

                it('Prevents Self-XSS', function() {
                    testSaveCommentPreventsXSS();
                });
            });

            describe('Screenshot comments', function() {
                beforeEach(function() {
                    screenshotCommentsPayload.total_results = 1;
                    screenshotCommentsPayload.screenshot_comments = [
                        screenshotCommentPayload
                    ];
                });

                it('For Markdown', function() {
                    testSaveComment(true);
                });

                it('For plain text', function() {
                    testSaveComment(false);
                });

                it('Prevents Self-XSS', function() {
                    testSaveCommentPreventsXSS();
                });
            });
        });
    });
});
