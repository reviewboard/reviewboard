suite('rb/resources/models/BaseResource', function() {
    let model;
    let parentObject;

    beforeEach(function() {
        model = new RB.BaseResource();
        model.rspNamespace = 'foo';

        parentObject = new RB.BaseResource({
            links: {
                foos: {
                    href: '/api/foos/',
                },
            },
        });
    });

    describe('ensureCreated', function() {
        beforeEach(function() {
            spyOn(model, 'save').and.resolveTo();
            spyOn(model, 'fetch').and.resolveTo();
            spyOn(model, 'ready').and.callThrough();
        });

        it('With loaded=true', async function() {
            model.set('loaded', true);

            await model.ensureCreated();

            expect(model.ready).toHaveBeenCalled();
            expect(model.fetch).not.toHaveBeenCalled();
            expect(model.save).not.toHaveBeenCalled();
        });

        it('With loaded=false, isNew=true', async function() {
            model.set('loaded', false);

            await model.ensureCreated();

            expect(model.ready).toHaveBeenCalled();
            expect(model.fetch).not.toHaveBeenCalled();
            expect(model.save).toHaveBeenCalled();
        });

        it('With loaded=false, isNew=false', async function() {
            model.set({
                loaded: false,
                id: 1,
            });

            await model.ensureCreated();

            expect(model.ready).toHaveBeenCalled();
            expect(model.fetch).toHaveBeenCalled();
            expect(model.save).toHaveBeenCalled();
        });

        it('With callbacks', function(done) {
            model.set({
                loaded: false,
                id: 1,
            });
            spyOn(console, 'warn');

            model.ensureCreated({
                success: () => {
                    expect(model.ready).toHaveBeenCalled();
                    expect(model.fetch).toHaveBeenCalled();
                    expect(model.save).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });
    });

    describe('fetch', function() {
        describe('Basic functionality', function() {
            beforeEach(function() {
                spyOn(Backbone.Model.prototype, 'fetch')
                    .and.callFake(options => {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
            });

            it('With isNew=true', async function() {
                expect(model.isNew()).toBe(true);

                await expectAsync(model.fetch()).toBeRejectedWith(Error(
                    'fetch cannot be used on a resource without an ID'));
                expect(Backbone.Model.prototype.fetch)
                    .not.toHaveBeenCalled();
            });

            it('With isNew=false and no parentObject', async function() {
                model.set('id', 123);

                await model.fetch();
                expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            });

            it('With isNew=false and parentObject', async function() {
                model.set({
                    parentObject: parentObject,
                    id: 123,
                });

                spyOn(parentObject, 'ready').and.resolveTo();

                await model.fetch();

                expect(parentObject.ready).toHaveBeenCalled();
                expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            });

            it('With isNew=false and parentObject with error', async function() {
                model.set({
                    parentObject: parentObject,
                    id: 123,
                });

                spyOn(parentObject, 'ready').and.rejectWith(new BackboneError(
                    parentObject,
                    { errorText: 'Oh nosers.' },
                    {}));

                await expectAsync(model.fetch()).toBeRejectedWith(
                    Error('Oh nosers.'));
                expect(parentObject.ready).toHaveBeenCalled();
                expect(Backbone.Model.prototype.fetch)
                    .not.toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                model.set({
                    parentObject: parentObject,
                    id: 123,
                });

                spyOn(parentObject, 'ready').and.resolveTo();
                spyOn(console, 'warn');

                model.fetch({
                    success: () => {
                        expect(parentObject.ready).toHaveBeenCalled();
                        expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                });
            });
        });

        describe('Response handling', function() {
            beforeEach(function() {
                model.set({
                    id: 123,
                    links: {
                        self: {
                            href: '/api/foo/',
                        },
                    },
                });
            });

            it('Custom response parsing', async function() {
                spyOn(model, 'parse').and.callFake(rsp => ({
                    a: rsp.a + 1,
                    b: rsp.b,
                    c: true,
                }));

                spyOn($, 'ajax').and.callFake(request => {
                    request.success({
                        a: 10,
                        b: 20,
                        d: 30,
                    });
                });

                await model.fetch();

                expect(model.get('a')).toBe(11);
                expect(model.get('b')).toBe(20);
                expect(model.get('c')).toBe(true);
                expect(model.get('d')).toBe(undefined);
            });

            it('Default response parsing', async function() {
                spyOn(model, 'parse').and.callThrough();

                spyOn($, 'ajax').and.callFake(request => {
                    request.success({
                        stat: 'ok',
                        foo: {
                            id: 42,
                            links: {
                                foo: {
                                    href: 'bar',
                                },
                            },
                            a: 20,
                        },
                    });
                });

                await model.fetch();

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
                            href: '/api/foo/',
                        },
                    },
                });
            });

            describe('GET', function() {
                it('No contentType sent', async function() {
                    spyOn(Backbone, 'sync')
                        .and.callFake((method, model, options) => {
                            expect(options.contentType).toBe(undefined);
                            options.success.call(model, {});
                        });

                    await model.fetch();

                    expect(Backbone.sync).toHaveBeenCalled();
                });

                it('No model data sent', async function() {
                    spyOn(Backbone, 'sync')
                        .and.callFake((method, model, options) => {
                            expect(_.isEmpty(options.data)).toBe(true);
                            options.success.call(model, {});
                        });

                    model.toJSON = () => ({
                        a: 1,
                        b: 2,
                    });

                    await model.fetch();

                    expect(Backbone.sync).toHaveBeenCalled();
                });

                it('Query attributes sent', async function() {
                    spyOn(Backbone, 'sync')
                        .and.callFake((method, model, options) => {
                            expect(_.isEmpty(options.data)).toBe(false);
                            expect(options.data.foo).toBe('bar');
                            options.success.call(model, {});
                        });

                    model.toJSON = () => ({
                        a: 1,
                        b: 2,
                    });

                    await model.fetch({
                        data: {
                            foo: 'bar',
                        },
                    });

                    expect(Backbone.sync).toHaveBeenCalled();
                });
            });
        });
    });

    describe('ready', function() {
        beforeEach(function() {
            spyOn(model, 'fetch').and.resolveTo();
        });

        it('With loaded=true', async function() {
            model.set('loaded', true);

            await model.ready();

            expect(model.fetch).not.toHaveBeenCalled();
        });

        it('With loaded=false and isNew=true', async function() {
            model.set('loaded', false);
            expect(model.isNew()).toBe(true);

            await model.ready();
            expect(model.fetch).not.toHaveBeenCalled();
        });

        it('With loaded=false and isNew=false', async function() {
            model.set({
                loaded: false,
                id: 123,
            });
            expect(model.isNew()).toBe(false);

            await model.ready();
            expect(model.fetch).toHaveBeenCalled();
        });

        it('With callbacks', function(done) {
            model.set({
                loaded: false,
                id: 123,
            });
            expect(model.isNew()).toBe(false);
            spyOn(console, 'warn');

            model.ready({
                success: () => {
                    expect(model.fetch).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });
    });

    describe('save', function() {
        beforeEach(function() {
            /* This is needed for any ready() calls. */
            spyOn(Backbone.Model.prototype, 'fetch')
                .and.callFake(options => {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });
            spyOn(model, 'trigger');
        });

        it('With isNew=true and parentObject', async function() {
            const responseData = {
                foo: {},
                stat: 'ok',
            };

            spyOn(parentObject, 'ensureCreated').and.resolveTo();
            spyOn(parentObject, 'ready').and.resolveTo();

            spyOn(Backbone.Model.prototype, 'save').and.callThrough();

            model.set('parentObject', parentObject);

            spyOn(RB, 'apiCall').and.callThrough();
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');

                request.success(responseData);
            });

            await model.save();

            expect(Backbone.Model.prototype.save).toHaveBeenCalled();
            expect(parentObject.ensureCreated).toHaveBeenCalled();
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();

            expect(model.trigger).toHaveBeenCalledWith('saved', {});
        });

        it('With isNew=true and no parentObject', async function() {
            spyOn(Backbone.Model.prototype, 'save').and.callThrough();
            spyOn(RB, 'apiCall').and.callThrough();
            spyOn($, 'ajax').and.callFake(function() {});

            try {
                await model.save();
                done.fail();
            } catch (err) {
                expect(Backbone.Model.prototype.save)
                    .not.toHaveBeenCalled();
                expect(RB.apiCall).not.toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();

                expect(err.message).toBe(
                    'The object must either be loaded from the server ' +
                    'or have a parent object before it can be saved');

                expect(model.trigger).not.toHaveBeenCalledWith('saved', {});
            }
        });

        it('With isNew=false and no parentObject', async function() {
            model.set('id', 123);
            model.url = '/api/foos/1/';

            spyOn(Backbone.Model.prototype, 'save')
                .and.callFake((attrs, options) => {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });

            await model.save();
            expect(Backbone.Model.prototype.save).toHaveBeenCalled();
            expect(model.trigger).toHaveBeenCalledWith('saved', {});
        });

        it('With isNew=false and parentObject', async function() {
            spyOn(parentObject, 'ensureCreated').and.resolveTo();
            spyOn(Backbone.Model.prototype, 'save').and.callThrough();

            model.set({
                parentObject: parentObject,
                id: 123,
            });

            spyOn(parentObject, 'ready').and.resolveTo();

            spyOn(RB, 'apiCall').and.callThrough();
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('PUT');

                request.success({
                    foo: {},
                    stat: 'ok',
                });
            });

            await model.save();

            expect(parentObject.ready).toHaveBeenCalled();
            expect(Backbone.Model.prototype.save).toHaveBeenCalled();
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(model.trigger).toHaveBeenCalledWith('saved', {});
        });

        it('With isNew=false and parentObject with error', async function() {
            model.set({
                parentObject: parentObject,
                id: 123,
            });

            spyOn(parentObject, 'ready').and.rejectWith(new BackboneError(
                parentObject,
                { errorText: 'Oh nosers.' },
                {}));

            spyOn(Backbone.Model.prototype, 'save')
                .and.callFake((attrs, options) => {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });

            await expectAsync(model.save()).toBeRejectedWith(
                Error('Oh nosers.'));

            expect(parentObject.ready).toHaveBeenCalled();
            expect(Backbone.Model.prototype.save)
                .not.toHaveBeenCalled();
            expect(model.trigger).not.toHaveBeenCalledWith('saved');
        });

        it('With callbacks', function(done) {
            const responseData = {
                foo: {},
                stat: 'ok',
            };

            spyOn(parentObject, 'ensureCreated').and.resolveTo();
            spyOn(parentObject, 'ready').and.resolveTo();

            spyOn(Backbone.Model.prototype, 'save').and.callThrough();

            model.set('parentObject', parentObject);

            spyOn(RB, 'apiCall').and.callThrough();
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');

                request.success(responseData);
            });
            spyOn(console, 'warn');

            model.save({
                success: () => {
                    expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                    expect(parentObject.ensureCreated).toHaveBeenCalled();
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();

                    expect(model.trigger).toHaveBeenCalledWith('saved', {});
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });

        describe('Request payload', function() {
            it('Saved data', async function() {
                model.set('id', 1);
                model.url = '/api/foos/';

                expect(model.isNew()).toBe(false);

                spyOn(model, 'toJSON').and.callFake(() => ({
                    a: 10,
                    b: 20,
                    c: 30,
                }));

                spyOn(model, 'ready').and.resolveTo();

                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
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
                            links: {},
                        },
                    });
                });

                await model.save();

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
                        myfield: 'myvalue',
                    };
                };

                spyOn(Backbone.Model.prototype, 'save').and.callThrough();
                spyOn(RB, 'apiCall').and.callThrough();
            });

            it('With file', async function() {
                const boundary = '-----multipartformboundary';
                const blob = new Blob(['Hello world!'], {
                    type: 'text/plain',
                });

                blob.name = 'myfile';

                spyOn($, 'ajax').and.callFake(request => {
                    const fileReader = new FileReader();

                    expect(request.type).toBe('POST');
                    expect(request.processData).toBe(false);
                    expect(request.contentType.indexOf(
                        'multipart/form-data; boundary=')).toBe(0);

                    fileReader.onload = function() {
                        const array = new Uint8Array(this.result);
                        const data = [];

                        for (let i = 0; i < array.length; i++) {
                            data.push(String.fromCharCode(array[i]));
                        }

                        expect(data.join('')).toBe(
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
                                id: 42,
                            },
                        });
                    };
                    fileReader.readAsArrayBuffer(request.data);
                });

                model.set('file', blob);
                await model.save({ boundary });

                expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With multiple files', async function() {
                const boundary = '-----multipartformboundary';

                const blob1 = new Blob(['Hello world!'], {
                    type: 'text/plain',
                });
                blob1.name = 'myfile1';

                const blob2 = new Blob(['Goodbye world!'], {
                    type: 'text/plain',
                });
                blob2.name = 'myfile2';

                model.payloadFileKeys = ['file1', 'file2'];
                model.toJSON = function() {
                    return {
                        file1: this.get('file1'),
                        file2: this.get('file2'),
                        myfield: 'myvalue',
                    };
                };

                spyOn($, 'ajax').and.callFake(request => {
                    const fileReader = new FileReader();

                    expect(request.type).toBe('POST');
                    expect(request.processData).toBe(false);
                    expect(request.contentType.indexOf(
                        'multipart/form-data; boundary=')).toBe(0);

                    fileReader.onload = function() {
                        const array = new Uint8Array(this.result);
                        const data = [];

                        for (let i = 0; i < array.length; i++) {
                            data.push(String.fromCharCode(array[i]));
                        }

                        expect(data.join('')).toBe(
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
                                id: 42,
                            },
                        });
                    };

                    fileReader.readAsArrayBuffer(request.data);
                });

                model.set('file1', blob1);
                model.set('file2', blob2);
                await model.save({ boundary });

                expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('Without file', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('POST');
                    expect(request.processData).toBe(true);
                    expect(request.contentType).toBe(
                        'application/x-www-form-urlencoded');

                    request.success({
                        stat: 'ok',
                        foo: {
                            id: 42,
                        },
                    });
                });

                await model.save();

                expect(Backbone.Model.prototype.save).toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });
        });

        describe('With form upload support', function() {
            beforeEach(function() {
                model.url = '/api/foos/';
            });

            it('Overriding toJSON attributes', async function() {
                const form = $('<form/>')
                    .append($('<input name="foo"/>'));

                model.toJSON = () => ({
                    myfield: 'myvalue',
                });

                spyOn(Backbone, 'sync').and.callThrough();
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax');
                spyOn(form, 'ajaxSubmit').and.callFake(
                    request => request.success({}));

                await model.save({ form: form });

                expect(RB.apiCall).toHaveBeenCalled();
                expect(form.ajaxSubmit).toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();
                expect(Backbone.sync.calls.argsFor(0)[2].data).toBe(null);
                expect(RB.apiCall.calls.argsFor(0)[0].data).toBe(null);
            });

            it('Overriding file attributes', async function() {
                const form = $('<form/>')
                    .append($('<input name="foo"/>'));

                model.payloadFileKey = 'file';
                    model.toJSON = function() {
                    return {
                        file: this.get('file'),
                    };
                };

                spyOn(model, '_saveWithFiles').and.callThrough();
                spyOn(Backbone, 'sync').and.callThrough();
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax');
                spyOn(form, 'ajaxSubmit').and.callFake(
                    request => request.success({}));

                await model.save({ form: form });

                expect(model._saveWithFiles).not.toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect(form.ajaxSubmit).toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();
                expect(Backbone.sync.calls.argsFor(0)[2].data).toBe(null);
                expect(RB.apiCall.calls.argsFor(0)[0].data).toBe(null);
            });
        });
    });

    describe('url', function() {
        it('With self link', function() {
            const url = '/api/base-resource/';

            model.set('links', {
                self: {
                    href: url,
                },
            });

            expect(model.url()).toBe(url);
        });

        it('With parentObject and model ID', function() {
            model.set({
                parentObject: parentObject,
                id: 123,
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
