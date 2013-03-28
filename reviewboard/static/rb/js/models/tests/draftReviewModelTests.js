describe('models/DraftReview', function() {
    var model,
        parentObject;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            links: {
                reviews: {
                    href: '/api/foos/'
                }
            }
        });

        model = new RB.DraftReview({
            parentObject: parentObject
        });
        model.rspNamespace = 'foo';
    });

    describe('ready', function() {
        var callbacks;

        beforeEach(function() {
            callbacks = {
                ready: function() {},
                error: function() {}
            };

            spyOn(Backbone.Model.prototype, 'fetch')
                .andCallFake(function(options) {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });
            spyOn(parentObject, 'ready')
                .andCallFake(function(options, context) {
                    if (options && _.isFunction(options.ready)) {
                        options.ready.call(context);
                    }
                });
            spyOn(model, '_retrieveDraft')
                .andCallFake(function(options, context) {
                    if (options && _.isFunction(options.ready)) {
                        options.ready.call(context);
                    }
                });
            spyOn(callbacks, 'ready');
            spyOn(callbacks, 'error');
        });

        describe('With isNew=true', function() {
            beforeEach(function() {
                expect(model.isNew()).toBe(true);
                expect(model.get('loaded')).toBe(false);
            });

            it('With callbacks', function() {
                model.ready(callbacks);

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).toHaveBeenCalled();
                expect(callbacks.ready).toHaveBeenCalled();
            });;
        });

        describe('With isNew=false', function() {
            beforeEach(function() {
                model.set({
                    id: 123
                });
            });

            it('With callbacks', function() {
                model.ready(callbacks);

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).not.toHaveBeenCalled();
                expect(callbacks.ready).toHaveBeenCalled();
            });
        });
    });
});
