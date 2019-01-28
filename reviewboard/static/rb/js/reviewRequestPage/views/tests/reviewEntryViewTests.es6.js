suite('rb/reviewRequestPage/views/ReviewEntryView', function() {
    const template = dedent`
        <div class="review review-request-page-entry">
         <div class="review-request-page-entry-contents">
          <div class="collapse-button"></div>
          <div class="banners">
           <input type="button" value="Publish" />
           <input type="button" value="Discard" />
          </div>
          <div class="comment-section" data-context-type="body_top">
           <a class="add_comment_link"></a>
           <ul class="reply-comments">
            <li class="draft" data-comment-id="456">
             <pre class="reviewtext"></pre>
            </li>
           </ul>
          </div>
          <div class="comment-section" data-context-id="123"
               data-context-type="diff_comments">
           <a class="add_comment_link"></a>
           <ul class="reply-comments"></ul>
          </div>
          <div class="comment-section" data-context-type="body_bottom">
           <a class="add_comment_link"></a>
           <ul class="reply-comments"></ul>
          </div>
         </div>
        </div>
    `;
    let view;
    let reviewView;
    let reviewReply;

    beforeEach(function() {
        const reviewRequest = new RB.ReviewRequest();
        const editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest
        });
        const review = reviewRequest.createReview({
            loaded: true,
            links: {
                replies: {
                    href: '/api/review/123/replies/',
                },
            },
        });
        const model = new RB.ReviewRequestPage.ReviewEntry({
            review: review,
            reviewRequest: reviewRequest,
            reviewRequestEditor: editor,
        });
        const $el = $(template).appendTo($testsScratch);

        reviewReply = review.createReply();

        view = new RB.ReviewRequestPage.ReviewEntryView({
            el: $el,
            model: model,
        });

        view.render();

        reviewView = view._reviewView;

        /* Don't allow the draft banner to show. */
        spyOn(reviewView, '_showReplyDraftBanner');
        spyOn(reviewView, 'trigger').and.callThrough();

        reviewView._setupNewReply(reviewReply);
    });

    describe('Actions', function() {
        it('Toggle collapse', function() {
            const $box = view.$('.review-request-page-entry-contents');
            const $collapseButton = view.$('.collapse-button');

            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(true);
            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(false);
        });
    });

    describe('Draft banner', function() {
        describe('Visibility', function() {
            it('Shown on hasDraft', function() {
                const editor = reviewView._replyEditorViews[1].model;

                reviewView._showReplyDraftBanner.calls.reset();

                expect(editor.get('hasDraft')).toBe(false);
                expect(reviewView._showReplyDraftBanner).not.toHaveBeenCalled();

                editor.set('hasDraft', true);
                expect(reviewView._showReplyDraftBanner).toHaveBeenCalled();
            });
        });
    });

    describe('Methods', function() {
        it('collapse', function() {
            view.collapse();
            expect(
                view.$('.review-request-page-entry-contents')
                    .hasClass('collapsed'))
                .toBe(true);
        });

        it('expand', function() {
            const $box = view.$('.review-request-page-entry-contents')
                .addClass('collapsed');
            view.expand();
            expect($box.hasClass('collapsed')).toBe(false);
        });

        describe('getReviewReplyEditorView', function() {
            it('With body_top', function() {
                const editorView = view.getReviewReplyEditorView('body_top');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[0]);
            });

            it('With body_bottom', function() {
                const editorView = view.getReviewReplyEditorView('body_bottom');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[2]);
            });

            it('With comments', function() {
                const editorView = view.getReviewReplyEditorView('diff_comments',
                                                                 123);

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[1]);
            });
        });
    });
});
