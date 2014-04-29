suite('rb/views/DraftReviewBannerView', function() {
    var model,
        view,
        template = _.template([
            '<div id="review-banner" style="display: none;">',
            ' <div class="banner">',
            '  <h1>You have a pending review.</h1>',
            '  <input id="review-banner-edit" type="button" ',
            '         value="Edit Review" />',
            '  <input id="review-banner-publish" type="button" ',
            '         value="Publish" />',
            '  <input id="review-banner-discard" type="button" ',
            '         value="Discard" />',
            ' </div>',
            '</div>'
        ].join(''));

    beforeEach(function() {
        var $el = $(template()).appendTo($testsScratch);

        model = new RB.DraftReview();
        view = new RB.DraftReviewBannerView({
            el: $el,
            model: model
        });

        view.render();
    });

    describe('Button states', function() {
        var $buttons;

        beforeEach(function() {
            $buttons = view.$('input');
        });

        describe('Enabled', function() {
            it('Default', function() {
                expect($buttons.prop('disabled')).toBe(false);
            });

            it('When saved', function() {
                $buttons.prop('disabled', true);
                model.trigger('saved');
                expect($buttons.prop('disabled')).toBe(false);
            });

            it('When destroyed', function() {
                $buttons.prop('disabled', true);
                model.trigger('destroyed');
                expect($buttons.prop('disabled')).toBe(false);
            });
        });

        describe('Disabled', function() {
            it('When saving', function() {
                model.trigger('saving');
                expect($buttons.prop('disabled')).toBe(true);
            });

            it('When destroying', function() {
                model.trigger('destroying');
                expect($buttons.prop('disabled')).toBe(true);
            });
        });
    });

    describe('Button events', function() {
        it('Edit Review', function() {
            spyOn(RB.ReviewDialogView, 'create');

            view.$('#review-banner-edit').click();

            expect(RB.ReviewDialogView.create).toHaveBeenCalled();
            expect(RB.ReviewDialogView.create.calls[0].args[0].review)
                .toBe(model);
        });

        it('Publish', function() {
            spyOn(model, 'publish');

            view.$('#review-banner-publish').click();

            expect(model.publish).toHaveBeenCalled();
        });

        it('Discard', function() {
            var $buttons = $();

            spyOn(model, 'destroy');
            spyOn($.fn, 'modalBox').andCallFake(function(options) {
                _.each(options.buttons, function($btn) {
                    $buttons = $buttons.add($btn);
                });

                /* Simulate the modalBox API for what we need. */
                return {
                    modalBox: function(cmd) {
                        expect(cmd).toBe('buttons');

                        return $buttons;
                    }
                };
            });

            view.$('#review-banner-discard').click();
            expect($.fn.modalBox).toHaveBeenCalled();

            $buttons.filter('input[value="Discard"]').click();
            expect(model.destroy).toHaveBeenCalled();
        });
    });

    describe('Methods', function() {
        it('show', function() {
            expect(view.$el.is(':visible')).toBe(false);

            view.show();
            expect(view.$el.is(':visible')).toBe(true);
        });

        it('hide', function() {
            view.$el.show();
            expect(view.$el.is(':visible')).toBe(true);

            view.hide();
            expect(view.$el.is(':visible')).toBe(false);
        });
    });
});
