describe('views/ReviewReplyEditorView', function() {
    var reviewReply,
        editor,
        view;

    beforeEach(function() {
        var $container = $('<div/>').appendTo($testsScratch);

        reviewReply = new RB.ReviewReply();

        /* Some tests will invoke this, so just pretend it works. */
        spyOn(reviewReply, 'discardIfEmpty')
            .andCallFake(function(options, context) {
                options.success.call(context);
            });

        editor = new RB.ReviewReplyEditor({
            review: new RB.Review({
                id: 42
            }),
            reviewReply: reviewReply,
            contextType: 'rcbt',
            contextID: '100'
        });

        view = new RB.ReviewReplyEditorView({
            model: editor,
            el: $testsScratch
        });

        /* Necessary to do pre-render so we can use makeCommentElement. */
        view._$commentsList = $('<ul class="reply-comments"/>');

        $container
            .append(view._$commentsList)
            .append($('<a href="#" class="add_comment_link">New Comment</a>'));
    });

    describe('Construction', function() {
        it('Populate from draft comment', function() {
            var commentText = 'Test comment',
                now = moment(),
                $el = view._makeCommentElement({
                    commentID: 16,
                    now: now,
                    text: commentText
                });

            view.render();

            expect(editor.get('commentID')).toBe(16);
            expect(editor.get('text')).toBe(commentText);
            expect(editor.get('hasDraft')).toBe(true);
            expect(editor.get('timestamp').valueOf())
                .toBe(now.milliseconds(0).valueOf());
            expect(view._$draftComment[0]).toBe($el[0]);
            expect(view._$addCommentLink.is(':visible')).toBe(false);
        });
    });

    describe('Actions', function() {
        it('Add comment link', function() {
            view.render();

            expect(view._$addCommentLink.is(':visible')).toBe(true);
            view._$addCommentLink.click();

            expect(view._$addCommentLink.is(':visible')).toBe(false);
            expect(view._$draftComment).not.toBe(null);
            expect(view._$draftComment.hasClass('draft')).toBe(true);
        });
    });

    describe('Event handling', function() {
        it('Comment discarded', function() {
            var commentText = 'Test comment',
                $el;

            view._makeCommentElement({
                commentText: commentText
            });

            view.render();

            $el = view.$('.reply-comments li');
            expect($el.length).toBe(1);

            reviewReply.trigger('destroy');

            $el = view.$('.reply-comments li');
            expect($el.length).toBe(0);
            expect(view._$draftComment).toBe(null);
        });

        it('Comment published', function() {
            var commentText = 'Test comment',
                $draftEl = view._makeCommentElement({
                    commentID: 16,
                    commentText: commentText
                }),
                $el;

            spyOn($.fn, 'user_infobox').andCallThrough();
            spyOn($.fn, 'timesince').andCallThrough();

            view.render();
            reviewReply.trigger('published');

            $el = view.$('.reply-comments li');

            expect($el.length).toBe(1);
            expect($draftEl).not.toBe($el);
            expect($el.hasClass('draft')).toBe(false);
            expect($el.data('comment-id')).toBe(16);
            expect(view._$draftComment).toBe(null);
            expect($.fn.user_infobox).toHaveBeenCalled();
            expect($.fn.timesince).toHaveBeenCalled();
        });
    });

    describe('Methods', function() {
        it('openCommentEditor', function() {
            view.render();

            expect(view._$addCommentLink.is(':visible')).toBe(true);
            expect(view._$draftComment).toBe(null);

            view.openCommentEditor();

            expect(view._$addCommentLink.is(':visible')).toBe(false);
            expect(view._$draftComment).not.toBe(null);
            expect(view._$draftComment.hasClass('draft')).toBe(true);
        });
    });
});
