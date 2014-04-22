suite('rb/views/ReviewReplyDraftBannerView', function() {
    var reviewReply,
        view;

    beforeEach(function() {
        reviewReply = new RB.ReviewReply();
        view = new RB.ReviewReplyDraftBannerView({
            model: reviewReply,
            $floatContainer: $testsScratch
        });
        view.render().$el.appendTo($testsScratch);
    });

    describe('Actions', function() {
        it('Discard', function() {
            spyOn(reviewReply, 'destroy');
            view.$('.discard-button').click();
            expect(reviewReply.destroy).toHaveBeenCalled();
        });

        it('Publish', function() {
            spyOn(reviewReply, 'publish');
            view.$('.publish-button').click();
            expect(reviewReply.publish).toHaveBeenCalled();
        });
    });

    describe('Event Handling', function() {
        describe('Buttons', function() {
            var $buttons;

            beforeEach(function() {
                $buttons = view.$('input');
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
                it('When saved', function() {
                    $buttons.prop('disabled', true);
                    reviewReply.trigger('saved');
                    expect($buttons.prop('disabled')).toBe(false);
                });
            });
        });
    });
});
