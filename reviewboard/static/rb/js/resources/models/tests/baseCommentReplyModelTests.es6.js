suite('rb/resources/models/BaseCommentReply', function() {
    let parentObject;
    let model;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            'public': true,
        });

        model = new RB.BaseCommentReply({
            parentObject: parentObject,
        });

        expect(model.validate(model.attributes)).toBe(undefined);
    });

    describe('destroyIfEmpty', function() {
        beforeEach(function() {
            spyOn(model, 'destroy');
        });

        it('Destroying when text is empty', function() {
            model.set('text', '');
            model.destroyIfEmpty();
            expect(model.destroy).toHaveBeenCalled();
        });

        it('Not destroying when text is not empty', function() {
            model.set('text', 'foo');
            model.destroyIfEmpty();
            expect(model.destroy).not.toHaveBeenCalled();
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_comment';
        });

        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                my_comment: {
                    id: 42,
                    text: 'foo',
                    text_type: 'markdown',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.text).toBe('foo');
            expect(data.richText).toBe(true);
        });
    });

    describe('toJSON', function() {
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

        describe('reply_to_id field', function() {
            it('When loaded', function() {
                model.set({
                    replyToID: 10,
                    loaded: true,
                });
                const data = model.toJSON();
                expect(data.reply_to_id).toBe(undefined);
            });

            it('When not loaded', function() {
                model.set({
                    replyToID: 10,
                    loaded: false,
                });
                const data = model.toJSON();
                expect(data.reply_to_id).toBe(10);
            });
        });

        describe('richText field', function() {
            it('With true', function() {
                model.set('richText', true);
                const data = model.toJSON();
                expect(data.text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('richText', false);
                const data = model.toJSON();
                expect(data.text_type).toBe('plain');
            });
        });

        describe('text field', function() {
            it('With value', function() {
                model.set('text', 'foo');
                const data = model.toJSON();
                expect(data.text).toBe('foo');
            });
        });
    });

    describe('validate', function() {
        describe('parentObject', function() {
            it('With value', function() {
                expect(model.validate({
                    parentObject: parentObject,
                })).toBe(undefined);
            });

            it('Unset', function() {
                expect(model.validate({
                    parentObject: null,
                })).toBe(RB.BaseResource.strings.UNSET_PARENT_OBJECT);
            });
        });
    });
});
