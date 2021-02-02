suite('rb/resources/models/DraftReview', function() {
    let model;
    let parentObject;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            links: {
                reviews: {
                    href: '/api/foos/'
                },
            },
        });

        model = new RB.DraftReview({
            parentObject: parentObject,
        });
        model.rspNamespace = 'foo';
    });

    describe('Methods', function() {
        describe('ready', function() {
            let callbacks;

            beforeEach(function() {
                callbacks = {
                    ready: function() {},
                    success: function() {},
                    error: function() {},
                };

                spyOn(callbacks, 'ready');
                spyOn(callbacks, 'success');
                spyOn(callbacks, 'error');

                spyOn(Backbone.Model.prototype, 'fetch')
                    .and.callFake(options => {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(parentObject, 'ready')
                    .and.callFake((options, context) => {
                        if (options && _.isFunction(options.ready)) {
                            options.ready.call(context);
                        }
                    });
                spyOn(model, '_retrieveDraft')
                    .and.callFake((options, context) => {
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
                        id: 123,
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
                spyOn(model, 'save').and.resolveTo();
                spyOn(model, 'ready').and.callFake((options, context) => {
                    options.ready.call(context);
                });
            });

            it('Triggers "publishing" event before publish', async function() {
                spyOn(model, 'trigger');

                await model.publish();
                expect(model.trigger).toHaveBeenCalledWith('publishing');
            });

            it('Triggers "published" event after publish', async function() {
                spyOn(model, 'trigger');

                await model.publish();
                expect(model.trigger).toHaveBeenCalledWith('published');
            });

            it('Sets "public" to true', async function() {
                expect(model.get('public')).toBe(false);

                await model.publish();
                expect(model.get('public')).toBe(true);
            });
        });
    });
});
