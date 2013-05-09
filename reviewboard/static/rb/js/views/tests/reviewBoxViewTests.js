describe('views/ReviewBoxView', function() {
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
            '  <div class="comment-section" data-context-id="123"',
            '       data-context-type="body_top">',
            '   <a class="add_comment_link"></a>',
            '   <ul class="reply-comments">',
            '    <li id="yourcomment_foo" data-comment-id="456">',
            '     <pre class="reviewtext"></pre>',
            '    </li>',
            '   </ul>',
            '  </div>',
            '  <div class="comment-section" data-context-id="124"',
            '       data-context-type="body_bottom">',
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
            expect(view._replyEditors.length).toBe(2);
        });

        it('Initial state populated', function() {
            var model = view._replyEditors[0].model;

            expect(model.get('contextID')).toBe(123);
            expect(model.get('contextType')).toBe('body_top');

            model = view._replyEditors[1].model;
            expect(model.get('contextID')).toBe(124);
            expect(model.get('contextType')).toBe('body_bottom');
        });

        it('Draft banner when draft comment exists', function() {
            expect(view._showReplyDraftBanner).toHaveBeenCalled();
        });
    });

    describe('Draft banner', function() {
        describe('Buttons', function() {
            var $buttons;

            beforeEach(function() {
                $buttons = view._$bannerButtons;
            });

            describe('Disabled', function() {
                it('When saving', function() {
                    expect($buttons.prop('disabled')).toBe(false);
                    reviewReply.trigger('saving');
                    expect($buttons.prop('disabled')).toBe(true);
                });

                it('When destroying', function() {
                    expect($buttons.prop('disabled')).toBe(false);
                    reviewReply.trigger('destroying');
                    expect($buttons.prop('disabled')).toBe(true);
                });
            });

            describe('Enabled', function() {
                it('When destroying', function() {
                    $buttons.prop('disabled', true);
                    reviewReply.trigger('saved');
                    expect($buttons.prop('disabled')).toBe(false);
                });
            });
        });

        describe('Visibility', function() {
            it('Shown on hasDraft', function() {
                var editor = view._replyEditors[1].model;

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
    });
});
