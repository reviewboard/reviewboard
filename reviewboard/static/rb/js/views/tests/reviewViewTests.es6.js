suite('rb/views/ReviewView', function() {
    let view;
    let reviewReply;
    const template = _.template([
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
        const reviewRequest = new RB.ReviewRequest();
        const editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });
        const review = reviewRequest.createReview({
            loaded: true,
            links: {
                replies: {
                    href: '/api/review/123/replies/',
                },
            },
        });
        const $el = $(template()).appendTo($testsScratch);

        reviewReply = review.createReply();

        view = new RB.ReviewView({
            el: $el,
            model: review,
            reviewRequestEditor: editor,
        });

        view._setupNewReply(reviewReply);

        spyOn(view, 'trigger').and.callThrough();

        view.render();
    });

    describe('Reply editors', function() {
        it('Views created', function() {
            expect(view._replyEditorViews.length).toBe(3);
        });

        it('Initial state populated', function() {
            let model = view._replyEditorViews[0].model;

            expect(model.get('contextID')).toBe(null);
            expect(model.get('contextType')).toBe('body_top');

            model = view._replyEditorViews[1].model;
            expect(model.get('contextID')).toBe(123);
            expect(model.get('contextType')).toBe('diff_comments');

            model = view._replyEditorViews[2].model;
            expect(model.get('contextID')).toBe(null);
            expect(model.get('contextType')).toBe('body_bottom');
        });

        it('Draft banner when draft comment exists', function() {
            expect(view.trigger)
                .toHaveBeenCalledWith('showReplyDraftBanner');
        });

        describe('reviewReply changes on', function() {
            it('Discard', function() {
                spyOn(view, '_setupNewReply');

                spyOn(reviewReply, 'discardIfEmpty').and.callFake(
                    (options, context) => options.success.call(context));

                reviewReply.trigger('destroyed');

                expect(view._setupNewReply).toHaveBeenCalled();
            });

            it('Publish', function() {
                spyOn(view, '_setupNewReply');

                /*
                 * Don't let these do their thing. Otherwise they'll try to
                 * discard and it'll end up performing ajax operations.
                 */
                view._replyEditors.forEach(
                    editor => spyOn(editor, '_resetState'));

                reviewReply.trigger('published');

                expect(view._setupNewReply).toHaveBeenCalled();
            });
        });

        describe('When reviewReply changes', function() {
            it('Signals connected', function() {
                spyOn(view, 'listenTo').and.callThrough();

                view._setupNewReply(new RB.ReviewReply());

                expect(view.listenTo.calls.argsFor(0)[1])
                    .toBe('destroyed published');
            });

            it('Signals disconnected from old reviewReply', function() {
                spyOn(view, 'stopListening').and.callThrough();

                view._setupNewReply();

                expect(view.stopListening).toHaveBeenCalledWith(reviewReply);
            });

            it('Hide draft banner signal emitted', function() {
                view._setupNewReply();
                expect(view.trigger).toHaveBeenCalledWith('hideReplyDraftBanner');
            });

            it('Editors updated', function() {
                view._setupNewReply();

                view._replyEditors.forEach(editor =>
                    expect(editor.get('reviewReply')).toBe(view._reviewReply));
            });
        });
    });
});
