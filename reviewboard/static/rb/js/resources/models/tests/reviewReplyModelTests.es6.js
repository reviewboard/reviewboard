suite('rb/resources/models/ReviewReply', function() {
    let parentObject;
    let model;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            'public': true,
            links: {
                replies: {
                    href: '/api/foos/replies/',
                },
            },
        });

        model = new RB.ReviewReply({
            parentObject: parentObject,
        });
    });

    describe('destroy', function() {
        let callbacks;

        beforeEach(function() {
            spyOn(Backbone.Model.prototype, 'destroy')
                .and.callFake(options => options.success());
            spyOn(model, '_retrieveDraft').and.callThrough();
            spyOn(parentObject, 'ready').and.resolveTo();
        });

        it('With isNew=true', async function() {
            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            spyOn(Backbone.Model.prototype, 'fetch')
                .and.callFake(options => {
                    if (options && _.isFunction(options.success)) {
                        options.error(model, {
                            status: 404,
                        });
                    }
                });

            await model.destroy();

            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            expect(Backbone.Model.prototype.destroy).toHaveBeenCalled();
        });

        it('With isNew=false', async function() {
            model.set({
                id: 123,
                loaded: true,
            });

            spyOn(Backbone.Model.prototype, 'fetch');

            await model.destroy();

            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).not.toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).not.toHaveBeenCalled();
            expect(Backbone.Model.prototype.destroy).toHaveBeenCalled();
        });
    });

    describe('discardIfEmpty', function() {
        beforeEach(function() {
            spyOn(model, 'destroy').and.resolveTo();
            spyOn(parentObject, 'ready').and.resolveTo();
            spyOn(model, 'ready').and.resolveTo();
        });

        it('With isNew=true', async function() {
            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            const discarded = await model.discardIfEmpty();

            expect(model.destroy).not.toHaveBeenCalled();
            expect(discarded).toBe(false);
        });

        describe('With isNew=false', function() {
            let commentsData;

            beforeEach(function() {
                commentsData = {};
                model.set({
                    id: 123,
                    loaded: true,
                    links: {
                        self: {
                            href: '/api/foos/replies/123/',
                        },
                        diff_comments: {
                            href: '/api/diff-comments/',
                        },
                        screenshot_comments: {
                            href: '/api/screenshot-comments/',
                        },
                        file_attachment_comments: {
                            href: '/api/file-attachment-comments/',
                        },
                        general_comments: {
                            href: '/api/general-comments/',
                        },
                    },
                });

                spyOn(RB, 'apiCall').and.callFake(options => {
                    const links = model.get('links');
                    const data = {};
                    const key = _.find(
                        RB.ReviewReply.prototype.COMMENT_LINK_NAMES,
                        name => (options.url === links[name].href));

                    if (key) {
                        data[key] = commentsData[key] || [];
                        options.success(data);
                    } else {
                        options.error({
                            status: 404,
                        });
                    }
                });
                spyOn(Backbone.Model.prototype, 'fetch')
                    .and.callFake(options => {
                        if (options && _.isFunction(options.success)) {
                            options.success();
                        }
                    });
            });

            it('With no comments or body replies', async function() {
                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(true);
                expect(model.destroy).toHaveBeenCalled();
            });

            it('With bodyTop', async function() {
                model.set({
                    bodyTop: 'hi',
                });

                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With bodyBottom', async function() {
                model.set({
                    bodyBottom: 'hi',
                });
                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With diff comment', async function() {
                commentsData.diff_comments = [{
                    id: 1,
                }];

                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With screenshot comment', async function() {
                commentsData.screenshot_comments = [{
                    id: 1,
                }];

                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With file attachment comment', async function() {
                commentsData.file_attachment_comments = [{
                    id: 1,
                }];

                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With general comment', async function() {
                commentsData.general_comments = [{
                    id: 1,
                }];

                const discarded = await model.discardIfEmpty();
                expect(discarded).toBe(false);
                expect(model.destroy).not.toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                spyOn(console, 'warn');

                model.discardIfEmpty({
                    success: discarded => {
                        expect(discarded).toBe(true);
                        expect(model.destroy).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                });
            });
        });
    });

    describe('ready', function() {
        beforeEach(function() {
            spyOn(parentObject, 'ready').and.resolveTo();
        });

        it('With isNew=true', async function() {
            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            spyOn(Backbone.Model.prototype, 'fetch').and.resolveTo();
            spyOn(model, '_retrieveDraft').and.resolveTo();

            await model.ready();

            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).toHaveBeenCalled();
        });

        it('With isNew=false', async function() {
            model.set({
                id: 123,
            });

            spyOn(Backbone.Model.prototype, 'fetch')
                .and.callFake(options => {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });
            spyOn(model, '_retrieveDraft').and.resolveTo();

            await model.ready();
            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).not.toHaveBeenCalled();
        });

        it('After destruction', async function() {
            spyOn(model, '_retrieveDraft').and.callThrough();

            spyOn(Backbone.Model.prototype, 'fetch').and.callFake(options => {
                model.set({
                    id: 123,
                    links: {
                        self: {
                            href: '/api/foos/replies/123/',
                        },
                    },
                    loaded: true,
                });

                options.success();
            });

            spyOn(Backbone.Model.prototype, 'destroy').and.callFake(
                options => options.success());

            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);
            expect(model._needDraft).toBe(undefined);

            /* Make our initial ready call. */
            await model.ready();

            expect(parentObject.ready).toHaveBeenCalled();
            expect(model._retrieveDraft).toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            expect(model.isNew()).toBe(false);
            expect(model.get('loaded')).toBe(true);
            expect(model._needDraft).toBe(false);

            /* We have a loaded object. Reset it. */
            await model.destroy();

            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);
            expect(model._needDraft).toBe(true);

            parentObject.ready.calls.reset();
            model._retrieveDraft.calls.reset();

            /* Now that it's destroyed, try to fetch it again. */
            await model.ready();

            expect(model._retrieveDraft).toHaveBeenCalled();
            expect(Backbone.Model.prototype.fetch).toHaveBeenCalled();
            expect(model._needDraft).toBe(false);
        });

        it('With callbacks', function(done) {
            expect(model.isNew()).toBe(true);
            expect(model.get('loaded')).toBe(false);

            spyOn(Backbone.Model.prototype, 'fetch')
                .and.callFake(options => {
                    if (options && _.isFunction(options.success)) {
                        options.success();
                    }
                });
            spyOn(model, '_retrieveDraft').and.resolveTo();
            spyOn(console, 'warn');

            model.ready({
                success: () => {
                    expect(parentObject.ready).toHaveBeenCalled();
                    expect(model._retrieveDraft).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
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
                    body_bottom_text_type: 'plain',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('foo');
            expect(data.bodyBottom).toBe('bar');
            expect(data.public).toBe(false);
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);
        });
    });

    describe('toJSON', function() {
        describe('bodyTop field', function() {
            it('With value', function() {
                model.set('bodyTop', 'foo');
                const data = model.toJSON();
                expect(data.body_top).toBe('foo');
            });
        });

        describe('bodyBottom field', function() {
            it('With value', function() {
                model.set('bodyBottom', 'foo');
                const data = model.toJSON();
                expect(data.body_bottom).toBe('foo');
            });
        });

        describe('bodyTopRichText field', function() {
            it('With true', function() {
                model.set('bodyTopRichText', true);
                const data = model.toJSON();
                expect(data.body_top_text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('bodyTopRichText', false);
                const data = model.toJSON();
                expect(data.body_top_text_type).toBe('plain');
            });
        });

        describe('bodyBottomRichText field', function() {
            it('With true', function() {
                model.set('bodyBottomRichText', true);
                const data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('bodyBottomRichText', false);
                const data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('plain');
            });
        });

        describe('force_text_type field', function() {
            it('With value', function() {
                model.set('forceTextType', 'html');
                const data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();
                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                model.set('includeTextTypes', 'html');
                const data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();
                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('public field', function() {
            it('With value', function() {
                model.set('public', true);
                const data = model.toJSON();
                expect(data.public).toBe(true);
            });
        });
    });
});
