suite('rb/resources/models/DraftReview', function() {
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

    describe('Methods', function() {
        var callbacks;

        beforeEach(function() {
            callbacks = {
                ready: function() {},
                success: function() {},
                error: function() {}
            };

            spyOn(callbacks, 'ready');
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
        });

        describe('ready', function() {
            beforeEach(function() {
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
                });
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

        describe('publish', function() {
            beforeEach(function() {
                spyOn(model, 'save').andCallFake(function(options, context) {
                    options.success.call(context);
                });
            });

            it('Triggers "publishing" event before publish', function() {
                spyOn(model, 'trigger');
                spyOn(model, 'ready');

                model.publish();

                expect(model.trigger).toHaveBeenCalledWith('publishing');
            });

            it('Triggers "published" event after publish', function() {
                spyOn(model, 'trigger');

                spyOn(model, 'ready').andCallFake(function(options, context) {
                    options.ready.call(context);
                });

                model.publish(callbacks);

                expect(callbacks.success).toHaveBeenCalled();
                expect(model.trigger).toHaveBeenCalledWith('published');
            });

            it('Sets "public" to true', function() {
                spyOn(model, 'ready').andCallFake(function(options, context) {
                    options.ready.call(context);
                });

                expect(model.get('public')).toBe(false);

                model.publish(callbacks);

                expect(callbacks.success).toHaveBeenCalled();
                expect(model.get('public')).toBe(true);
            });
        });
    });
});
