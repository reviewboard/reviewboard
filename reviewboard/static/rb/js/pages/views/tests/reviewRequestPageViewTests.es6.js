suite('rb/pages/views/ReviewRequestPageView', () => {
    let page;
    let box1;
    let box2;

    const template = [
        '<a id="collapse-all"></a>',
        '<a id="expand-all"></a>',
        '<div>',
        ' <div class="review review-request-page-entry" id="review123">',
        '  <div class="review-request-page-entry-contents">',
        '   <div class="body">',
        '    <pre class="body_top">Body Top</pre>',
        '    <div class="comment-section" data-context-type="body_top">',
        '    </div>',
        '    <div class="comment-section" data-context-id="123" ',
        '         data-context-type="diff_comments">',
        '    </div>',
        '    <pre class="body_bottom">Body Bottom</pre>',
        '    <div class="comment-section" data-context-type="body_bottom">',
        '    </div>',
        '   </div>',
        ' </div>',
        ' <div class="review review-request-page-entry" id="review124">',
        '  <div class="review-request-page-entry-contents">',
        '   <div class="body">',
        '    <pre class="body_top">Body Top</pre>',
        '    <div class="comment-section" data-context-type="body_top">',
        '    </div>',
        '    <pre class="body_bottom">Body Bottom</pre>',
        '    <div class="comment-section" data-context-type="body_bottom">',
        '    </div>',
        '   </div>',
        '  </div>',
        ' </div>',
        '</div>',
    ].join('');

    beforeEach(() => {
        const $el = $('<div/>')
            .html(template)
            .appendTo($testsScratch);

        RB.DnDUploader.instance = null;
        page = new RB.ReviewRequestPageView({
            el: $el,
            reviewRequestData: {
            },
            editorData: {
                fileAttachments: [],
                mutableByUser: true,
                showSendEmail: false,
            },
        });

        // Stub this out.
        spyOn(page.reviewRequest, '_checkForUpdates');

        page.addBox(new RB.ReviewBoxView({
            model: page.reviewRequest.createReview(123, {
                shipIt: true,
                public: true,
                bodyTop: 'Body Top',
                bodyBottom: 'Body Bottom',
            }),
            el: $el.find('#review123'),
            reviewRequestEditor: page.reviewRequestEditor,
        }));

        page.addBox(new RB.ReviewBoxView({
            model: page.reviewRequest.createReview(124, {
                shipIt: false,
                public: true,
                bodyTop: 'Body Top',
                bodyBottom: 'Body Bottom',
            }),
            el: $el.find('#review124'),
            reviewRequestEditor: page.reviewRequestEditor,
        }));

        page.render();

        expect(page._boxes.length).toBe(2);
        box1 = page._boxes[0];
        box2 = page._boxes[1];
    });

    describe('Actions', () => {
        it('Collapse all', () => {
            const $el1 = box1.$el.find('.review-request-page-entry-contents');
            const $el2 = box2.$el.find('.review-request-page-entry-contents');

            expect($el1.hasClass('collapsed')).toBe(false);
            expect($el2.hasClass('collapsed')).toBe(false);

            page.$('#collapse-all').click();

            expect($el1.hasClass('collapsed')).toBe(true);
            expect($el2.hasClass('collapsed')).toBe(true);
        });

        it('Expand all', () => {
            const $el1 = box1.$el.find('.review-request-page-entry-contents');
            const $el2 = box2.$el.find('.review-request-page-entry-contents');

            $el1.addClass('collapsed');
            $el2.addClass('collapsed');

            page.$('#expand-all').click();

            expect($el1.hasClass('collapsed')).toBe(false);
            expect($el2.hasClass('collapsed')).toBe(false);
        });
    });

    describe('Methods', () => {
        describe('openCommentEditor', () => {
            beforeEach(() => {
                spyOn(RB.ReviewReplyEditorView.prototype, 'openCommentEditor');
                spyOn(box1, 'getReviewReplyEditorView').and.callThrough();
                spyOn(box2, 'getReviewReplyEditorView').and.callThrough();
            });

            it('With body_top', () => {
                page.openCommentEditor('body_top');

                expect(box1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewReplyEditorView.prototype.openCommentEditor)
                    .toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(box2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });

            it('With body_bottom', () => {
                page.openCommentEditor('body_bottom');

                expect(box1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewReplyEditorView.prototype.openCommentEditor)
                    .toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(box2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });

            it('With comments', () => {
                page.openCommentEditor('diff_comments', 123);

                expect(box1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewReplyEditorView.prototype.openCommentEditor)
                    .toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(box2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });
        });
    });
});
