suite('rb/views/ReviewBoxView', function() {
    var view,
        reviewView,
        reviewReply,
        template = _.template([
            '<div class="review review-request-page-entry">',
            ' <div class="review-request-page-entry-contents">',
            '  <div class="collapse-button"></div>',
            '  <div class="banners">',
            '   <input type="button" value="Publish" />',
            '   <input type="button" value="Discard" />',
            '  </div>',
            '  <div class="comment-section" data-context-type="body_top">',
            '   <a class="add_comment_link"></a>',
            '   <ul class="reply-comments">',
            '    <li class="draft" data-comment-id="456">',
            '     <pre class="reviewtext"></pre>',
            '    </li>',
            '   </ul>',
            '  </div>',
            '  <div class="comment-section" data-context-id="123" ',
            '       data-context-type="diff_comments">',
            '   <a class="add_comment_link"></a>',
            '   <ul class="reply-comments"></ul>',
            '  </div>',
            '  <div class="comment-section" data-context-type="body_bottom">',
            '   <a class="add_comment_link"></a>',
            '   <ul class="reply-comments"></ul>',
            '  </div>',
            ' </div>',
            '</div>'
        ].join(''));

    beforeEach(function() {
        var reviewRequest = new RB.ReviewRequest(),
            editor = new RB.ReviewRequestEditor({
                reviewRequest: reviewRequest
            }),
            review = reviewRequest.createReview({
                loaded: true,
                links: {
                    replies: {
                        href: '/api/review/123/replies/'
                    }
                }
            }),
            $el = $(template())
                .appendTo($testsScratch);

        reviewReply = review.createReply();

        view = new RB.ReviewBoxView({
            el: $el,
            model: review,
            reviewRequestEditor: editor,
        });

        reviewView = view._reviewView;

        reviewView._setupNewReply(reviewReply);

        /* Don't allow the draft banner to show. */
        spyOn(view, '_showReplyDraftBanner');
        spyOn(reviewView, 'trigger').and.callThrough();

        view.render();
    });

    describe('Actions', function() {
        it('Toggle collapse', function() {
            var $box = view.$('.review-request-page-entry-contents'),
                $collapseButton = view.$('.collapse-button');

            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(true);
            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(false);
        });
    });

    describe('Draft banner', function() {
        describe('Visibility', function() {
            it('Shown on hasDraft', function() {
                var editor = reviewView._replyEditorViews[1].model;

                view._showReplyDraftBanner.calls.reset();

                expect(editor.get('hasDraft')).toBe(false);
                expect(view._showReplyDraftBanner).not.toHaveBeenCalled();

                editor.set('hasDraft', true);
                expect(view._showReplyDraftBanner).toHaveBeenCalled();
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
            var $box = view.$('.review-request-page-entry-contents');

            $box.addClass('collapsed');
            view.expand();
            expect($box.hasClass('collapsed')).toBe(false);
        });

        describe('getReviewReplyEditorView', function() {
            it('With body_top', function() {
                var editorView = view.getReviewReplyEditorView('body_top');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[0]);
            });

            it('With body_bottom', function() {
                var editorView = view.getReviewReplyEditorView('body_bottom');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[2]);
            });

            it('With comments', function() {
                var editorView = view.getReviewReplyEditorView('diff_comments',
                                                               123);

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(reviewView._replyEditorViews[1]);
            });
        });
    });
});
