suite('rb/resources/models/ReviewReply', function() {
    var parentObject,
        model;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            'public': true,
            links: {
                replies: {
                    href: '/api/foos/replies/'
                }
            }
        });

        model = new RB.ReviewReply({
            parentObject: parentObject
        });
    });

    describe('destroy', function() {
        var callbacks;

        beforeEach(function() {
            callbacks = {
                ready: function() {},
                error: function() {}
            };

            spyOn(Backbone.Model.prototype, 'destroy')
                .andCallFake(function(options) {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });
            spyOn(model, '_retrieveDraft').andCallThrough();
            spyOn(parentObject, 'ready')
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

                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.error(model, {
                                status: 404
                            });
                        }
                    });
            });

            it('With callbacks', function() {
                model.destroy(callbacks);

                expect(model.isNew()).toBe(true);
                expect(model.get('loaded')).toBe(false);

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).toHaveBeenCalled();
                expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                expect(Backbone.Model.prototype.destroy).toHaveBeenCalled();
            });
        });

        describe('With isNew=false', function() {
            beforeEach(function() {
                model.set({
                    id: 123,
                    loaded: true
                });

                spyOn(Backbone.Model.prototype, 'fetch');
            });

            it('With callbacks', function() {
                model.destroy(callbacks);

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).not.toHaveBeenCalled();
                expect(Backbone.Model.prototype.fetch).not.toHaveBeenCalled();
                expect(Backbone.Model.prototype.destroy).toHaveBeenCalled();
            });
        });
    });

    describe('discardIfEmpty', function() {
        var callbacks;

        beforeEach(function() {
            callbacks = {
                success: function() {},
                error: function() {}
            };

            spyOn(model, 'destroy')
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
            spyOn(model, 'ready')
                .andCallFake(function(options, context) {
                    if (options && _.isFunction(options.ready)) {
                        options.ready.call(context);
                    }
                });
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
        });

        it('With isNew=true', function() {
            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            model.discardIfEmpty(callbacks);

            expect(model.destroy).not.toHaveBeenCalled();
        });

        describe('With isNew=false', function() {
            var commentsData = {};

            beforeEach(function() {
                model.set({
                    id: 123,
                    loaded: true,
                    links: {
                        self: {
                            href: '/api/foos/replies/123/'
                        },
                        diff_comments: {
                            href: '/api/diff-comments/'
                        },
                        screenshot_comments: {
                            href: '/api/screenshot-comments/'
                        },
                        file_attachment_comments: {
                            href: '/api/file-attachment-comments/'
                        }
                    }
                });

                spyOn(RB, 'apiCall').andCallFake(function(options) {
                    var links = model.get('links'),
                        data = {},
                        key = _.find(
                            RB.ReviewReply.prototype.COMMENT_LINK_NAMES,
                            function(name) {
                                return options.url === links[name].href;
                            });

                    if (key) {
                        data[key] = commentsData[key] || [];
                        options.success(data);
                    } else {
                        options.error({
                            status: 404
                        });
                    }
                });
                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
            });

            it('With no comments or body replies', function() {
                model.discardIfEmpty(callbacks);

                expect(model.destroy).toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(true);
            });

            it('With bodyTop', function() {
                model.set({
                    bodyTop: 'hi'
                });
                model.discardIfEmpty(callbacks);

                expect(model.destroy).not.toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(false);
            });

            it('With bodyBottom', function() {
                model.set({
                    bodyBottom: 'hi'
                });
                model.discardIfEmpty(callbacks);

                expect(model.destroy).not.toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(false);
            });

            it('With diff comment', function() {
                commentsData.diff_comments = [{
                    id: 1
                }];

                model.discardIfEmpty(callbacks);

                expect(model.destroy).not.toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(false);
            });

            it('With screenshot comment', function() {
                commentsData.screenshot_comments = [{
                    id: 1
                }];

                model.discardIfEmpty(callbacks);

                expect(model.destroy).not.toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(false);
            });

            it('With file attachment comment', function() {
                commentsData.file_attachment_comments = [{
                    id: 1
                }];

                model.discardIfEmpty(callbacks);

                expect(model.destroy).not.toHaveBeenCalled();
                expect(callbacks.success).toHaveBeenCalledWith(false);
            });
        });
    });

    describe('ready', function() {
        var callbacks;

        beforeEach(function() {
            callbacks = {
                ready: function() {},
                error: function() {}
            };

            spyOn(parentObject, 'ready')
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

                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(model, '_retrieveDraft')
                    .andCallFake(function(options, context) {
                        if (options && _.isFunction(options.ready)) {
                            options.ready.call(context);
                        }
                    });
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

                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(model, '_retrieveDraft')
                    .andCallFake(function(options, context) {
                        if (options && _.isFunction(options.ready)) {
                            options.ready.call(context);
                        }
                    });
            });

            it('With callbacks', function() {
                model.ready(callbacks);

                expect(parentObject.ready).toHaveBeenCalled();
                expect(model._retrieveDraft).not.toHaveBeenCalled();
                expect(callbacks.ready).toHaveBeenCalled();
            });
        });

        it('After destruction', function() {
            spyOn(model, '_retrieveDraft').andCallThrough();

            spyOn(Backbone.Model.prototype, 'fetch').andCallFake(
                function(options) {
                    model.set({
                        id: 123,
                        links: {
                            self: {
                                href: '/api/foos/replies/123/'
                            }
                        },
                        loaded: true
                    });

                    options.success();
                });

            spyOn(Backbone.Model.prototype, 'destroy').andCallFake(
                function(options) {
                    options.success();
                });

            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);
            expect(model._needDraft).toBe(undefined);

            /* Make our initial ready call. */
            model.ready(callbacks);

            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            expect(callbacks.ready).toHaveBeenCalled();
            expect(model.isNew()).toBe(false);
            expect(model.get('loaded')).toBe(true);
            expect(model._needDraft).toBe(false);

            /* We have a loaded object. Reset it. */
            model.destroy(callbacks);

            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);
            expect(model._needDraft).toBe(true);

            parentObject.ready.reset();
            model._retrieveDraft.reset();
            callbacks.ready.reset();

            /* Now that it's destroyed, try to fetch it again. */
            model.ready(callbacks);

            expect(model._retrieveDraft).toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            expect(callbacks.ready).toHaveBeenCalled();
            expect(model._needDraft).toBe(false);
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_reply';
        });

        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                my_reply: {
                    id: 42,
                    body_top: 'foo',
                    body_bottom: 'bar',
                    'public': false,
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain'
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('foo');
            expect(data.bodyBottom).toBe('bar');
            expect(data['public']).toBe(false);
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);
        });
    });

    describe('toJSON', function() {
        describe('bodyTop field', function() {
            it('With value', function() {
                var data;

                model.set('bodyTop', 'foo');
                data = model.toJSON();
                expect(data.body_top).toBe('foo');
            });
        });

        describe('bodyBottom field', function() {
            it('With value', function() {
                var data;

                model.set('bodyBottom', 'foo');
                data = model.toJSON();
                expect(data.body_bottom).toBe('foo');
            });
        });

        describe('bodyTopRichText field', function() {
            it('With true', function() {
                var data;

                model.set('bodyTopRichText', true);
                data = model.toJSON();
                expect(data.body_top_text_type).toBe('markdown');
            });

            it('With false', function() {
                var data;

                model.set('bodyTopRichText', false);
                data = model.toJSON();
                expect(data.body_top_text_type).toBe('plain');
            });
        });

        describe('bodyBottomRichText field', function() {
            it('With true', function() {
                var data;

                model.set('bodyBottomRichText', true);
                data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('markdown');
            });

            it('With false', function() {
                var data;

                model.set('bodyBottomRichText', false);
                data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('plain');
            });
        });

        describe('force_text_type field', function() {
            it('With value', function() {
                var data;

                model.set('forceTextType', 'html');
                data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                var data;

                model.set('includeTextTypes', 'html');
                data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('public field', function() {
            it('With value', function() {
                var data;

                model.set('public', true);
                data = model.toJSON();
                expect(data['public']).toBe(true);
            });
        });
    });
});
