suite('rb/views/ScreenshotThumbnail', function() {
    var model,
        view,
        template = _.template([
            '<div>',
             '<a class="edit"></a>',
             '<a class="delete">X</a>',
            '</div>'
        ].join(''));

    beforeEach(function() {
        var $el = $(template()).appendTo($testsScratch);

        model = new RB.Screenshot();
        model.url = '/screenshots/123/';
        model.id = 123;
        model.set('loaded', true);

        view = new RB.ScreenshotThumbnail({
            el: $el,
            model: model
        });
        view.render();

        spyOn(model, 'trigger').andCallThrough();
        spyOn(view, 'trigger').andCallThrough();
    });

    describe('Actions', function() {
        it('Begin caption editing', function() {
            view.$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');
        });

        it('Cancel caption editing', function() {
            view.$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view.$caption.inlineEditor('cancel');
            expect(view.trigger).toHaveBeenCalledWith('endEdit');
        });

        it('Save caption', function() {
            spyOn(model, 'save');

            view.$caption.inlineEditor('startEdit');
            expect(view.trigger).toHaveBeenCalledWith('beginEdit');

            view.$el.find('input')
                .val('Foo')
                .triggerHandler('keyup');
            view.$caption.inlineEditor('submit');

            expect(view.trigger).toHaveBeenCalledWith('endEdit');
            expect(model.get('caption')).toBe('Foo');
            expect(model.save).toHaveBeenCalled();
        });

        it('Delete', function() {
            spyOn(model, 'destroy').andCallThrough();
            spyOn($, 'ajax').andCallFake(function(options) {
                options.success();
            });
            spyOn(view.$el, 'fadeOut').andCallFake(function(done) {
                done();
            });

            spyOn(view, 'remove');

            view.$el.find('a.delete').click();

            expect($.ajax).toHaveBeenCalled();
            expect(model.destroy).toHaveBeenCalled();
            expect(model.trigger.calls[0].args[0]).toBe('destroying');
            expect(view.$el.fadeOut).toHaveBeenCalled();
            expect(view.remove).toHaveBeenCalled();
        });
    });
});
