suite('rb/views/DraftReviewBannerView', function() {
    const template = dedent`
        <div id="review-banner" hidden class="hidden">
         <div class="banner">
          <h1>You have a pending review.</h1>
          <input id="review-banner-edit" type="button"
                 value="Edit Review" />
          <input id="review-banner-publish-container" type="button"
                 value="Publish" />
          <input id="review-banner-discard" type="button"
                 value="Discard" />
         </div>
        </div>'
    `;
    let model;
    let view;

    beforeEach(function() {
        model = new RB.DraftReview();
        view = new RB.DraftReviewBannerView({
            el: $(template).appendTo($testsScratch),
            model: model,
        });

        view.render();
    });

    afterEach(function() {
        view.remove();
    });

    describe('Button states', function() {
        let $buttons;

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
            expect(RB.ReviewDialogView.create.calls.argsFor(0)[0].review)
                .toBe(model);
        });

        it('Publish', function() {
            spyOn(model, 'publish');

            view.$('#review-banner-publish').click();

            expect(model.publish).toHaveBeenCalled();
        });

        it('Publish to Submitter Only', function() {
            spyOn(model, 'publish');

            /*
             * The alternative buttons from the split button are added to the
             * <body>.
             */
            $('#review-banner-publish-submitter-only').click();

            expect(model.publish).toHaveBeenCalled();
        });

        it('Publish and Archive', function() {
            spyOn(model, 'publish');
            spyOn(view, '_onPublishClicked').and.callThrough();

            /*
             * The alternative buttons from the split button are added to the
             * <body>.
             */
            $('#review-banner-publish-and-archive').click();

            expect(model.publish).toHaveBeenCalled();
            expect(view._onPublishClicked).toHaveBeenCalledWith({
                publishAndArchive: true
            });
        });

        it('Discard', function() {
            let $buttons = $();

            spyOn(model, 'destroy');
            spyOn($.fn, 'modalBox').and.callFake(options => {
                options.buttons.forEach($btn => {
                    $buttons = $buttons.add($btn);
                });

                /* Simulate the modalBox API for what we need. */
                return {
                    modalBox: cmd => {
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
            expect(view.$el.hasClass('hidden')).toBe(true);
            expect(view.$el.prop('hidden')).toBe(true);

            view.show();
            expect(view.$el.hasClass('hidden')).toBe(false);
            expect(view.$el.prop('hidden')).toBe(false);
        });

        it('hide', function() {
            view.$el
                .addClass('hidden')
                .prop('hidden', true);

            view.hide();
            expect(view.$el.hasClass('hidden')).toBe(true);
            expect(view.$el.prop('hidden')).toBe(true);
        });
    });
});
