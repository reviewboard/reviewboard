suite('rb/resources/models/UserFileAttachment', function() {
    let model;

    beforeEach(function() {
        model = new RB.UserFileAttachment();
    });

    describe('toJSON', function() {
        describe('caption field', function() {
            it('With value', function() {
                model.set('caption', 'foo');
                const data = model.toJSON();
                expect(data.caption).toBe('foo');
            });
        });

        describe('file field', function() {
            it('With no file attachment', function() {
                model.id = 123;
                model.attributes.id = 123;
                expect(model.isNew()).toBe(false);

                const data = model.toJSON();
                expect(data.path).toBe(undefined);
            });

            it('With file attachment', function() {
                model.id = 123;
                model.attributes.id = 123;
                expect(model.isNew()).toBe(false);

                model.set('file', 'abc');
                const data = model.toJSON();
                expect(data.path).toBe('abc');
            });
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                user_file_attachment: {
                    id: 42,
                    caption: 'caption',
                    absolute_url: 'downloadURL',
                    filename: 'filename',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.caption).toBe('caption');
            expect(data.downloadURL).toBe('downloadURL');
            expect(data.filename).toBe('filename');
        });
    });
});
