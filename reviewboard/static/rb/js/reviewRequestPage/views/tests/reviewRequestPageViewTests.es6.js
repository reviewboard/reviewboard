suite('rb/reviewRequestPage/views/PageView', () => {
    let page;
    let entry1;
    let entry2;

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
        page = new RB.ReviewRequestPage.ReviewRequestPageView({
            el: $el,
            reviewRequestData: {
            },
            editorData: {
                fileAttachments: [],
                mutableByUser: true,
                showSendEmail: false,
            },
        });

        // Stub these out.
        spyOn(page.reviewRequest, '_checkForUpdates');
        spyOn(RB.ReviewRequestPage.IssueSummaryTableView.prototype,
              'render');

        page.addEntryView(new RB.ReviewRequestPage.ReviewEntryView({
            model: new RB.ReviewRequestPage.ReviewEntry({
                review: page.reviewRequest.createReview(123, {
                    shipIt: true,
                    public: true,
                    bodyTop: 'Body Top',
                    bodyBottom: 'Body Bottom',
                }),
                reviewRequestEditor: page.reviewRequestEditor,
            }),
            el: $el.find('#review123'),
        }));

        page.addEntryView(new RB.ReviewRequestPage.ReviewEntryView({
            model: new RB.ReviewRequestPage.ReviewEntry({
                review: page.reviewRequest.createReview(124, {
                    shipIt: false,
                    public: true,
                    bodyTop: 'Body Top',
                    bodyBottom: 'Body Bottom',
                }),
                reviewRequestEditor: page.reviewRequestEditor,
            }),
            el: $el.find('#review124'),
        }));

        page.render();

        expect(page._entryViews.length).toBe(2);
        entry1 = page._entryViews[0];
        entry2 = page._entryViews[1];
    });

    describe('Actions', () => {
        it('Collapse all', () => {
            const $el1 = entry1.$el.find('.review-request-page-entry-contents');
            const $el2 = entry2.$el.find('.review-request-page-entry-contents');

            expect($el1.hasClass('collapsed')).toBe(false);
            expect($el2.hasClass('collapsed')).toBe(false);

            page.$('#collapse-all').click();

            expect($el1.hasClass('collapsed')).toBe(true);
            expect($el2.hasClass('collapsed')).toBe(true);
        });

        it('Expand all', () => {
            const $el1 = entry1.$el.find('.review-request-page-entry-contents');
            const $el2 = entry2.$el.find('.review-request-page-entry-contents');

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
                spyOn(RB.ReviewRequestPage.ReviewReplyEditorView.prototype,
                      'openCommentEditor');
                spyOn(entry1, 'getReviewReplyEditorView').and.callThrough();
                spyOn(entry2, 'getReviewReplyEditorView').and.callThrough();
            });

            it('With body_top', () => {
                page.openCommentEditor('body_top');

                expect(entry1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewRequestPage.ReviewReplyEditorView
                       .prototype.openCommentEditor).toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(entry2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });

            it('With body_bottom', () => {
                page.openCommentEditor('body_bottom');

                expect(entry1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewRequestPage.ReviewReplyEditorView
                       .prototype.openCommentEditor).toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(entry2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });

            it('With comments', () => {
                page.openCommentEditor('diff_comments', 123);

                expect(entry1.getReviewReplyEditorView).toHaveBeenCalled();
                expect(RB.ReviewRequestPage.ReviewReplyEditorView
                       .prototype.openCommentEditor).toHaveBeenCalled();

                /* We should have matched the first one. */
                expect(entry2.getReviewReplyEditorView).not.toHaveBeenCalled();
            });
        });
    });
});
