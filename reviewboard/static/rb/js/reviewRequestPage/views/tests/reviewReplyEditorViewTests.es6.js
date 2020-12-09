suite('rb/reviewRequestPage/views/ReviewReplyEditorView', function() {
    let reviewReply;
    let editor;
    let view;

    beforeEach(function() {
        const $container = $('<div/>').appendTo($testsScratch);

        reviewReply = new RB.ReviewReply({
            id: 121
        });

        /* Some tests will invoke this, so just pretend it works. */
        spyOn(reviewReply, 'discardIfEmpty').and.callFake(
            (options, context) => options.success.call(context));

        editor = new RB.ReviewRequestPage.ReviewReplyEditor({
            anchorPrefix: 'header-reply',
            replyObject: reviewReply,
            review: new RB.Review({
                id: 42,
                parentObject: new RB.ReviewRequest(),
            }),
            reviewReply: reviewReply,
            contextType: 'rcbt',
            contextID: '100',
        });

        view = new RB.ReviewRequestPage.ReviewReplyEditorView({
            model: editor,
            el: $testsScratch,
        });

        /* Necessary to do pre-render so we can use makeCommentElement. */
        view._$commentsList = $('<ul class="reply-comments"/>');

        $container
            .append(view._$commentsList)
            .append($('<a href="#" class="add_comment_link">New Comment</a>'));
    });

    describe('Construction', function() {
        it('Populate from draft comment', function() {
            const commentText = 'Test comment';
            const now = moment();
            const $el = view._makeCommentElement({
                commentID: 16,
                now: now,
                text: commentText,
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
            view._makeCommentElement({
                text: 'Test comment',
            });

            view.render();

            let $el = view.$('.reply-comments li');
            expect($el.length).toBe(1);

            reviewReply.trigger('destroyed');

            $el = view.$('.reply-comments li');
            expect($el.length).toBe(0);
            expect(view._$draftComment).toBe(null);
        });

        it('Comment published', function() {
            const $draftEl = view._makeCommentElement({
                commentID: 16,
            });

            spyOn($.fn, 'user_infobox').and.callThrough();
            spyOn($.fn, 'timesince').and.callThrough();

            view.render();
            editor.set('text', 'Test **comment**');
            reviewReply.trigger('published');

            const $el = view.$('.reply-comments li');

            expect($el.length).toBe(1);
            expect($draftEl).not.toBe($el);
            expect($el.hasClass('draft')).toBe(false);
            expect($el.data('comment-id')).toBe(16);
            expect(view._$draftComment).toBe(null);
            expect($.fn.user_infobox).toHaveBeenCalled();
            expect($.fn.timesince).toHaveBeenCalled();

            const $anchor = $el.children('.comment-anchor');
            expect($anchor.length).toBe(1);
            expect($anchor.attr('name')).toBe('header-reply121');

            const $floatingAnchor = $el.find('> .floating-anchor > a');
            expect($floatingAnchor.length).toBe(1);
            expect($floatingAnchor.attr('href')).toBe('#header-reply121');
            expect($floatingAnchor.hasClass('fa fa-link fa-flip-horizontal'))
                .toBe(true);
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

    describe('Text rendering', function() {
        function testRendering(richText, expectedHTML) {
            view.render();

            const $comment = view._makeCommentElement({
                text: '<p><strong>Test</strong> &amp;lt;</p>',
                richText: richText,
            });

            const $reviewText = $comment.find('.reviewtext');
            expect($reviewText.length).toBe(1);
            expect($reviewText.hasClass('rich-text')).toBe(richText);
            expect($reviewText.html()).toBe(expectedHTML);
        }

        it('richText=true', function() {
            testRendering(true, '<p><strong>Test</strong> &amp;lt;</p>');
        });

        it('richText=false', function() {
            testRendering(false,
                          '&lt;p&gt;&lt;strong&gt;Test&lt;/strong&gt; ' +
                          '&amp;amp;lt;&lt;/p&gt;');
        });
    });
});
