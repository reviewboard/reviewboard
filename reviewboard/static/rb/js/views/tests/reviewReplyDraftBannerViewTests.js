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

    describe('Publish', function() {
        beforeEach(function() {
            spyOn(reviewReply, 'ensureCreated')
                .andCallFake(function(options, context) {
                    options.success.call(context);
                });

            spyOn(reviewReply, 'publish');
        });

        describe('With Send E-Mail shown', function() {
            beforeEach(function() {
                view.remove();
                view = new RB.ReviewReplyDraftBannerView({
                    model: reviewReply,
                    $floatContainer: $testsScratch,
                    showSendEmail: true
                });
                view.render().$el.appendTo($testsScratch);
            });

            it('Send E-Mail true', function() {
                $('.send-email').prop('checked', true);

                $('.publish-button').click();

                expect(reviewReply.publish).toHaveBeenCalled();
                expect(reviewReply.publish.calls[0].args[0].trivial)
                    .toBe(false);
            });

            it('Send E-Mail false', function() {
                $('.send-email').prop('checked', false);

                $('.publish-button').click();

                expect(reviewReply.publish).toHaveBeenCalled();
                expect(reviewReply.publish.calls[0].args[0].trivial)
                    .toBe(true);
            });
        });

        it('Without Send E-Mail shown', function() {
            $('.publish-button').click();

            expect($('.send-email').length).toEqual(0);
            expect(reviewReply.publish).toHaveBeenCalled();
            expect(reviewReply.publish.calls[0].args[0].trivial).toBe(false);
        });
    });
});
