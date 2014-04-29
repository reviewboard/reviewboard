suite('rb/resources/models/BaseResource', function() {
    var model,
        parentObject;

    beforeEach(function() {
        model = new RB.BaseResource();
        model.rspNamespace = 'foo';

        parentObject = new RB.BaseResource({
            links: {
                foos: {
                    href: '/api/foos/'
                }
            }
        });
    });

    describe('ensureCreated', function() {
        var callbacks;

        describe('Callback handling', function() {
            beforeEach(function() {
                callbacks = {
                    success: function() {},
                    error: function() {}
                };

                spyOn(model, 'save')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(model, 'fetch').andCallFake(function(options, context) {
                    options.success.call(context);
                });
                spyOn(model, 'ready').andCallThrough();

                spyOn(callbacks, 'success');
                spyOn(callbacks, 'error');
            });

            describe('With loaded=true', function() {
                beforeEach(function() {
                    model.set('loaded', true);
                });

                it('With callbacks', function() {
                    model.ensureCreated(callbacks);

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).not.toHaveBeenCalled();
                    expect(model.save).not.toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.ensureCreated();

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).not.toHaveBeenCalled();
                    expect(model.save).not.toHaveBeenCalled();
                });
            });

            describe('With loaded=false, isNew=true', function() {
                beforeEach(function() {
                    model.set('loaded', false);
                });

                it('With callbacks', function() {
                    model.ensureCreated(callbacks);

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).not.toHaveBeenCalled();
                    expect(model.save).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.ensureCreated();

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).not.toHaveBeenCalled();
                    expect(model.save).toHaveBeenCalled();
                });
            });

            describe('With loaded=false, isNew=false', function() {
                beforeEach(function() {
                    model.set({
                        loaded: false,
                        id: 1
                    });
                });

                it('With callbacks', function() {
                    model.ensureCreated(callbacks);

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).toHaveBeenCalled();
                    expect(model.save).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.ensureCreated();

                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).toHaveBeenCalled();
                    expect(model.save).toHaveBeenCalled();
                });
            });
        });
    });

    describe('fetch', function() {
        var callbacks;

        describe('Callback handling', function() {
            beforeEach(function() {
                callbacks = {
                    success: function() {},
                    error: function() {}
                };

                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
                spyOn(callbacks, 'success');
                spyOn(callbacks, 'error');
            });

            describe('With isNew=true', function() {
                beforeEach(function() {
                    expect(model.isNew()).toBe(true);
                });

                it('With callbacks', function() {
                    model.fetch(callbacks);

                    expect(Backbone.Model.prototype.fetch)
                        .not.toHaveBeenCalled();
                    expect(callbacks.success).not.toHaveBeenCalled();
                    expect(callbacks.error).toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.fetch();
                    expect(Backbone.Model.prototype.fetch)
                        .not.toHaveBeenCalled();
                });
            });

            describe('With isNew=false and no parentObject', function() {
                beforeEach(function() {
                    model.set('id', 123);
                });

                it('With callbacks', function() {
                    model.fetch(callbacks);

                    expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                    expect(callbacks.error).not.toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.fetch();
                    expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                });
            });

            describe('With isNew=false and parentObject', function() {
                beforeEach(function() {
                    model.set({
                        parentObject: parentObject,
                        id: 123
                    });

                    spyOn(parentObject, 'ready')
                        .andCallFake(function(options, context) {
                            options.ready.call(context);
                        });
                });

                it('With callbacks', function() {
                    model.fetch(callbacks);

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                    expect(callbacks.error).not.toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.fetch();

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                });
            });

            describe('With isNew=false and parentObject with error',
                     function() {
                beforeEach(function() {
                    model.set({
                        parentObject: parentObject,
                        id: 123
                    });

                    spyOn(parentObject, 'ready')
                        .andCallFake(function(options, context) {
                            if (options && _.isFunction(options.error)) {
                                options.error.call(context, "Oh nosers.");
                            }
                        });
                });

                it('With callbacks', function() {
                    model.fetch(callbacks);

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.fetch)
                        .not.toHaveBeenCalled();
                    expect(callbacks.success).not.toHaveBeenCalled();
                    expect(callbacks.error).toHaveBeenCalled();
                });

                it('Without callbacks', function() {
                    model.fetch();

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.fetch)
                        .not.toHaveBeenCalled();
                });
            });
        });

        describe('Response handling', function() {
            beforeEach(function() {
                model.set({
                    id: 123,
                    links: {
                        self: {
                            href: '/api/foo/'
                        }
                    }
                });
            });

            it('Custom response parsing', function() {
                spyOn(model, 'parse').andCallFake(function(rsp) {
                    return {
                        a: rsp.a + 1,
                        b: rsp.b,
                        c: true
                    };
                });

                spyOn($, 'ajax').andCallFake(function(request) {
                    request.success({
                        a: 10,
                        b: 20,
                        d: 30
                    });
                });

                model.fetch();

                expect(model.get('a')).toBe(11);
                expect(model.get('b')).toBe(20);
                expect(model.get('c')).toBe(true);
                expect(model.get('d')).toBe(undefined);
            });

            it('Default response parsing', function() {
                spyOn(model, 'parse').andCallThrough();

                spyOn($, 'ajax').andCallFake(function(request) {
                    request.success({
                        stat: 'ok',
                        foo: {
                            id: 42,
                            links: {
                                foo: {
                                    href: 'bar'
                                }
                            },
                            a: 20
                        }
                    });
                });

                model.fetch();

                expect(model.get('a')).toBe(undefined);
                expect(model.id).toBe(42);
                expect(model.get('links').foo).not.toBe(undefined);
                expect(model.get('loaded')).toBe(true);
            });
        });

        describe('Request payload', function() {
            beforeEach(function() {
                model.set({
                    id: 123,
                    links: {
                        self: {
                            href: '/api/foo/'
                        }
                    }
                });
            });

            describe('GET', function() {
                it('No contentType sent', function() {
                    spyOn(Backbone, 'sync')
                        .andCallFake(function(method, model, options) {
                            expect(options.contentType).toBe(undefined);
                        });

                    model.fetch();

                    expect(Backbone.sync).toHaveBeenCalled();
                });

                it('No model data sent', function() {
                    spyOn(Backbone, 'sync')
                        .andCallFake(function(method, model, options) {
                            expect(_.isEmpty(options.data)).toBe(true);
                        });

                    model.toJSON = function() {
                        return {
                            a: 1,
                            b: 2
                        };
                    };

                    model.fetch();

                    expect(Backbone.sync).toHaveBeenCalled();
                });

                it('Query attributes sent', function() {
                    spyOn(Backbone, 'sync')
                        .andCallFake(function(method, model, options) {
                            expect(_.isEmpty(options.data)).toBe(false);
                            expect(options.data.foo).toBe('bar');
                        });

                    model.toJSON = function() {
                        return {
                            a: 1,
                            b: 2
                        };
                    };

                    model.fetch({
                        data: {
                            foo: 'bar'
                        }
                    });

                    expect(Backbone.sync).toHaveBeenCalled();
                });
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

            spyOn(model, 'fetch').andCallFake(function(options) {
                options.success();
            });
            spyOn(callbacks, 'ready');
            spyOn(callbacks, 'error');
        });

        it('With loaded=true', function() {
            model.set('loaded', true);
            model.ready(callbacks);

            expect(model.fetch).not.toHaveBeenCalled();
            expect(callbacks.ready).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With loaded=false and isNew=true', function() {
            model.set('loaded', false);
            expect(model.isNew()).toBe(true);
            model.ready(callbacks);

            expect(model.fetch).not.toHaveBeenCalled();
            expect(callbacks.ready).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With loaded=false and isNew=false', function() {
            model.set({
                loaded: false,
                id: 123
            });
            expect(model.isNew()).toBe(false);
            model.ready(callbacks);

            expect(model.fetch).toHaveBeenCalled();
            expect(callbacks.ready).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });

    describe('save', function() {
        var callbacks;

        describe('Callback handling', function() {
            beforeEach(function() {
                callbacks = {
                    success: function() {},
                    error: function() {}
                };

                /* This is needed for any ready() calls. */
                spyOn(Backbone.Model.prototype, 'fetch')
                    .andCallFake(function(options) {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });

                spyOn(callbacks, 'success');
                spyOn(callbacks, 'error');
                spyOn(model, 'trigger');
            });

            describe('With isNew=true and parentObject', function() {
                beforeEach(function() {
                    spyOn(parentObject, 'ensureCreated')
                        .andCallFake(function(options) {
                            if (options && _.isFunction(options.success)) {
                                options.success();
                            }
                        });
                    spyOn(parentObject, 'ready')
                        .andCallFake(function(options, context) {
                            options.ready.call(context);
                        });

                    spyOn(Backbone.Model.prototype, 'save').andCallThrough();

                    model.set('parentObject', parentObject);

                    spyOn(RB, 'apiCall').andCallThrough();
                    spyOn($, 'ajax').andCallFake(function(request) {
                        expect(request.type).toBe('POST');

                        request.success({
                            foo: {},
                            stat: 'ok'
                        });
                    });
                });

                it('With callbacks', function() {
                    model.save(callbacks);

                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(parentObject.ensureCreated).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                    expect(callbacks.error).not.toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });

                it('Without callbacks', function() {
                    model.save();

                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(parentObject.ensureCreated).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });
            });

            describe('With isNew=true and no parentObject', function() {
                beforeEach(function() {
                    spyOn(Backbone.Model.prototype, 'save').andCallThrough();
                    spyOn(RB, 'apiCall').andCallThrough();
                    spyOn($, 'ajax').andCallFake(function() {});
                });

                it('With callbacks', function() {
                    model.save(callbacks);

                    expect(Backbone.Model.prototype.save)
                        .not.toHaveBeenCalled();
                    expect(RB.apiCall).not.toHaveBeenCalled();
                    expect($.ajax).not.toHaveBeenCalled();
                    expect(callbacks.success).not.toHaveBeenCalled();
                    expect(callbacks.error).toHaveBeenCalled();
                    expect(model.trigger).not.toHaveBeenCalledWith('saved');
                });

                it('Without callbacks', function() {
                    model.save();

                    expect(Backbone.Model.prototype.save)
                        .not.toHaveBeenCalled();
                    expect(RB.apiCall).not.toHaveBeenCalled();
                    expect($.ajax).not.toHaveBeenCalled();
                    expect(model.trigger).not.toHaveBeenCalledWith('saved');
                });
            });

            describe('With isNew=false and no parentObject', function() {
                beforeEach(function() {
                    model.set('id', 123);
                    model.url = '/api/foos/1/';

                    spyOn(Backbone.Model.prototype, 'save')
                        .andCallFake(function(attrs, options) {
                            if (options && _.isFunction(options.success)) {
                                options.success();
                            }
                        });
                });

                it('With callbacks', function() {
                    model.save(callbacks);

                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                    expect(callbacks.error).not.toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });

                it('Without callbacks', function() {
                    model.save();
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });
            });

            describe('With isNew=false and parentObject', function() {
                beforeEach(function() {
                    spyOn(parentObject, 'ensureCreated')
                        .andCallFake(function(options) {
                            if (options && _.isFunction(options.success)) {
                                options.success();
                            }
                        });

                    spyOn(Backbone.Model.prototype, 'save').andCallThrough();

                    model.set({
                        parentObject: parentObject,
                        id: 123
                    });

                    spyOn(parentObject, 'ready')
                        .andCallFake(function(options, context) {
                            options.ready.call(context);
                        });

                    spyOn(RB, 'apiCall').andCallThrough();
                    spyOn($, 'ajax').andCallFake(function(request) {
                        expect(request.type).toBe('PUT');

                        request.success({
                            foo: {},
                            stat: 'ok'
                        });
                    });
                });

                it('With callbacks', function() {
                    model.save(callbacks);

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(callbacks.success).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(callbacks.error).not.toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });

                it('Without callbacks', function() {
                    model.save();

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(model.trigger).toHaveBeenCalledWith('saved');
                });
            });

            describe('With isNew=false and parentObject with error',
                     function() {
                beforeEach(function() {
                    model.set({
                        parentObject: parentObject,
                        id: 123
                    });

                    spyOn(parentObject, 'ready')
                        .andCallFake(function(options, context) {
                            if (options && _.isFunction(options.error)) {
                                options.error.call(context, "Oh nosers.");
                            }
                        });

                    spyOn(Backbone.Model.prototype, 'save')
                        .andCallFake(function(attrs, options) {
                            if (options && _.isFunction(options.success)) {
                                options.success();
                            }
                        });
                });

                it('With callbacks', function() {
                    model.save(callbacks);

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.save)
                        .not.toHaveBeenCalled();
                    expect(callbacks.success).not.toHaveBeenCalled();
                    expect(callbacks.error).toHaveBeenCalled();
                    expect(model.trigger).not.toHaveBeenCalledWith('saved');
                });

                it('Without callbacks', function() {
                    model.save();

                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(Backbone.Model.prototype.save)
                        .not.toHaveBeenCalled();
                    expect(model.trigger).not.toHaveBeenCalledWith('saved');
                });
            });
        });

        describe('Request payload', function() {
            it('Saved data', function() {
                model.set('id', 1);
                model.url = '/api/foos/';

                expect(model.isNew()).toBe(false);

                spyOn(model, 'toJSON').andCallFake(function() {
                    return {
                        a: 10,
                        b: 20,
                        c: 30
                    };
                });

                spyOn(model, 'ready').andCallFake(function(options,
                                                           context) {
                    options.ready.call(context);
                });

                spyOn(RB, 'apiCall').andCallThrough();
                spyOn($, 'ajax').andCallFake(function(request) {
                    expect(request.url).toBe(model.url);
                    expect(request.contentType)
                        .toBe('application/x-www-form-urlencoded');
                    expect(request.processData).toBe(true);

                    expect(request.data.a).toBe(10);
                    expect(request.data.b).toBe(20);
                    expect(request.data.c).toBe(30);

                    request.success({
                        stat: 'ok',
                        foo: {
                            id: 1,
                            a: 10,
                            b: 20,
                            c: 30,
                            links: {}
                        }
                    });
                });

                model.save();

                expect(model.toJSON).toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });
        });

        describe('With file upload support', function() {
            beforeEach(function() {
                model.payloadFileKeys = ['file'];
                model.url = '/api/foos/';
                model.toJSON = function() {
                    return {
                        file: this.get('file'),
                        myfield: 'myvalue'
                    };
                };

                spyOn(Backbone.Model.prototype, 'save').andCallThrough();
                spyOn(RB, 'apiCall').andCallThrough();
            });

            it('With file', function() {
                var seenComplete = false,
                    boundary = '-----multipartformboundary';

                runs(function() {
                    var blob = new Blob(['Hello world!'], {
                        type: 'text/plain'
                    });
                    blob.name = 'myfile';

                    spyOn($, 'ajax').andCallFake(function(request) {
                        expect(request.type).toBe('POST');
                        expect(request.processData).toBe(false);
                        expect(request.contentType.indexOf(
                            'multipart/form-data; boundary=')).toBe(0);
                        expect(request.data).toBe(
                            '--' + boundary + '\r\n' +
                            'Content-Disposition: form-data; name="file"' +
                            '; filename="myfile"\r\n' +
                            'Content-Type: text/plain\r\n\r\n' +
                            'Hello world!' +
                            '\r\n' +
                            '--' + boundary + '\r\n' +
                            'Content-Disposition: form-data; ' +
                            'name="myfield"\r\n\r\n' +
                            'myvalue\r\n' +
                            '--' + boundary + '--\r\n\r\n');

                        request.success({
                            stat: 'ok',
                            foo: {
                                id: 42
                            }
                        });
                    });

                    model.set('file', blob);
                    model.save({
                        success: function() {
                            seenComplete = true;
                        },
                        boundary: boundary
                    });
                });

                waitsFor(function() {
                    return seenComplete;
                });

                runs(function() {
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                });
            });

            it('With multiple files', function() {
                var seenComplete = false,
                    boundary = '-----multipartformboundary';

                runs(function() {
                    var blob1 = new Blob(['Hello world!'], {
                            type: 'text/plain'
                        }),
                        blob2 = new Blob(['Goodbye world!'], {
                            type: 'text/plain'
                        });

                    blob1.name = 'myfile1';
                    blob2.name = 'myfile2';

                    model.payloadFileKeys = ['file1', 'file2'];
                    model.toJSON = function() {
                        return {
                            file1: this.get('file1'),
                            file2: this.get('file2'),
                            myfield: 'myvalue'
                        };
                    };

                    spyOn($, 'ajax').andCallFake(function(request) {
                        expect(request.type).toBe('POST');
                        expect(request.processData).toBe(false);
                        expect(request.contentType.indexOf(
                            'multipart/form-data; boundary=')).toBe(0);
                        expect(request.data).toBe(
                            '--' + boundary + '\r\n' +
                            'Content-Disposition: form-data; name="file1"' +
                            '; filename="myfile1"\r\n' +
                            'Content-Type: text/plain\r\n\r\n' +
                            'Hello world!' +
                            '\r\n' +
                            '--' + boundary + '\r\n' +
                            'Content-Disposition: form-data; name="file2"' +
                            '; filename="myfile2"\r\n' +
                            'Content-Type: text/plain\r\n\r\n' +
                            'Goodbye world!' +
                            '\r\n' +
                            '--' + boundary + '\r\n' +
                            'Content-Disposition: form-data; ' +
                            'name="myfield"\r\n\r\n' +
                            'myvalue\r\n' +
                            '--' + boundary + '--\r\n\r\n');

                        request.success({
                            stat: 'ok',
                            foo: {
                                id: 42
                            }
                        });
                    });

                    model.set('file1', blob1);
                    model.set('file2', blob2);
                    model.save({
                        success: function() {
                            seenComplete = true;
                        },
                        boundary: boundary
                    });
                });

                waitsFor(function() {
                    return seenComplete;
                });

                runs(function() {
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                });
            });

            it('Without file', function() {
                runs(function() {
                    spyOn($, 'ajax').andCallFake(function(request) {
                        expect(request.type).toBe('POST');
                        expect(request.processData).toBe(true);
                        expect(request.contentType).toBe(
                            'application/x-www-form-urlencoded');

                        request.success({
                            stat: 'ok',
                            foo: {
                                id: 42
                            }
                        });
                    });

                    model.save({
                        success: function() {
                            seenComplete = true;
                        }
                    });
                });

                waitsFor(function() {
                    return seenComplete;
                });

                runs(function() {
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                });
            });
        });

        describe('With form upload support', function() {
            beforeEach(function() {
                model.url = '/api/foos/';
            });

            it('Overriding toJSON attributes', function() {
                var form = $('<form/>')
                    .append($('<input name="foo"/>'));

                model.toJSON = function() {
                    return {
                        myfield: 'myvalue'
                    };
                };

                spyOn(Backbone, 'sync').andCallThrough();
                spyOn(RB, 'apiCall').andCallThrough();
                spyOn($, 'ajax');
                spyOn(form, 'ajaxSubmit');

                model.save({
                    form: form
                });

                expect(RB.apiCall).toHaveBeenCalled();
                expect(form.ajaxSubmit).toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();
                expect(Backbone.sync.calls[0].args[2].data).toBe(null);
                expect(RB.apiCall.calls[0].args[0].data).toBe(null);
            });

            it('Overriding file attributes', function() {
                var form = $('<form/>')
                    .append($('<input name="foo"/>'));

                model.payloadFileKey = 'file';
                model.toJSON = function() {
                    return {
                        file: this.get('file')
                    };
                };

                spyOn(model, '_saveWithFiles').andCallThrough();
                spyOn(Backbone, 'sync').andCallThrough();
                spyOn(RB, 'apiCall').andCallThrough();
                spyOn($, 'ajax');
                spyOn(form, 'ajaxSubmit');

                model.save({
                    form: form
                });

                expect(model._saveWithFiles).not.toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect(form.ajaxSubmit).toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();
                expect(Backbone.sync.calls[0].args[2].data).toBe(null);
                expect(RB.apiCall.calls[0].args[0].data).toBe(null);
            });
        });
    });

    describe('url', function() {
        it('With self link', function() {
            var url = '/api/base-resource/';

            model.set('links', {
                self: {
                    href: url
                }
            });

            expect(model.url()).toBe(url);
        });

        it('With parentObject and model ID', function() {
            model.set({
                parentObject: parentObject,
                id: 123
            });

            expect(model.url()).toBe('/api/foos/123/');
        });

        it('With parentObject, no links', function() {
            model.set('parentObject', parentObject);

            expect(model.url()).toBe('/api/foos/');
        });

        it('With no parentObject, no links', function() {
            expect(model.url()).toBe(null);
        });
    });
});
