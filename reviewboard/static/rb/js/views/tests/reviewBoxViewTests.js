suite('rb/views/ReviewBoxView', function() {
    var view,
        reviewReply,
        template = _.template([
            '<div>',
            ' <div class="box">',
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
            pageEditState: editor,
            reviewReply: reviewReply
        });

        /* Don't allow the draft banner to show. */
        spyOn(view, '_showReplyDraftBanner');

        view.render();
    });

    describe('Actions', function() {
        it('Toggle collapse', function() {
            var $box = view.$('.box'),
                $collapseButton = view.$('.collapse-button');

            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(true);
            $collapseButton.click();
            expect($box.hasClass('collapsed')).toBe(false);
        });
    });

    describe('Reply editors', function() {
        it('Views created', function() {
            expect(view._replyEditorViews.length).toBe(3);
        });

        it('Initial state populated', function() {
            var model = view._replyEditorViews[0].model;

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
            expect(view._showReplyDraftBanner).toHaveBeenCalled();
        });

        describe('reviewReply changes on', function() {
            it('Discard', function() {
                spyOn(view, '_setupNewReply');

                spyOn(reviewReply, 'discardIfEmpty')
                    .andCallFake(function(options, context) {
                        options.success.call(context);
                    });

                reviewReply.trigger('destroyed');
                expect(view._setupNewReply).toHaveBeenCalled();
            });

            it('Publish', function() {
                spyOn(view, '_setupNewReply');

                /*
                 * Don't let these do their thing. Otherwise they'll try to
                 * discard and it'll end up performing ajax operations.
                 */
                _.each(view._replyEditors, function(editor) {
                    spyOn(editor, '_resetState');
                });

                reviewReply.trigger('published');
                expect(view._setupNewReply).toHaveBeenCalled();
            });
        });

        describe('When reviewReply changes', function() {
            it('Signals connected', function() {
                var reviewReply = new RB.ReviewReply();

                spyOn(view, 'listenTo').andCallThrough();

                view._setupNewReply(reviewReply);

                expect(view.listenTo.calls[0].args[1])
                    .toBe('destroyed published');
            });

            it('Signals disconnected from old reviewReply', function() {
                spyOn(view, 'stopListening').andCallThrough();

                view._setupNewReply();

                expect(view.stopListening).toHaveBeenCalledWith(reviewReply);
            });

            it('Draft banner hidden', function() {
                spyOn(view, '_hideReplyDraftBanner');

                view._setupNewReply();

                expect(view._hideReplyDraftBanner).toHaveBeenCalled();
            });

            it('Editors updated', function() {
                spyOn(view, '_hideReplyDraftBanner');

                view._setupNewReply();

                _.each(view._replyEditors, function(editor) {
                    expect(editor.get('reviewReply')).toBe(view._reviewReply);
                });
            });
        });
    });

    describe('Draft banner', function() {
        describe('Visibility', function() {
            it('Shown on hasDraft', function() {
                var editor = view._replyEditorViews[1].model;

                view._showReplyDraftBanner.reset();

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
            expect(view.$('.box').hasClass('collapsed')).toBe(true);
        });

        it('expand', function() {
            var $box = view.$('.box');

            $box.addClass('collapsed');
            view.expand();
            expect($box.hasClass('collapsed')).toBe(false);
        });

        describe('getReviewReplyEditorView', function() {
            it('With body_top', function() {
                var editorView = view.getReviewReplyEditorView('body_top');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(view._replyEditorViews[0]);
            });

            it('With body_bottom', function() {
                var editorView = view.getReviewReplyEditorView('body_bottom');

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(view._replyEditorViews[2]);
            });

            it('With comments', function() {
                var editorView = view.getReviewReplyEditorView('diff_comments',
                                                               123);

                expect(editorView).not.toBe(undefined);
                expect(editorView).toBe(view._replyEditorViews[1]);
            });
        });
    });
});
