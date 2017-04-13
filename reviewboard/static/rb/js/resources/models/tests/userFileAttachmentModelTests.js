suite('rb/resources/models/UserFileAttachment', function() {
    beforeEach(function() {
        model = new RB.UserFileAttachment();
    });

    describe('toJSON', function() {
        describe('caption field', function() {
            it('With value', function() {
                var data;

                model.set('caption', 'foo');
                data = model.toJSON();
                expect(data.caption).toBe('foo');
            });
        });

        describe('file field', function() {
            it('With no file attachment', function() {
                var data;

                model.id = 123;
                expect(model.isNew()).toBe(false);

                data = model.toJSON();
                expect(data.path).toBe(undefined);
            });

            it('With file attachment', function() {
                var data;

                model.id = 123;
                expect(model.isNew()).toBe(false);

                model.set('file', 'abc');
                data = model.toJSON();
                expect(data.path).toBe('abc');
            });
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                user_file_attachment: {
                    id: 42,
                    caption: 'caption',
                    absolute_url: 'downloadURL',
                    filename: 'filename'
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.caption).toBe('caption');
            expect(data.downloadURL).toBe('downloadURL');
            expect(data.filename).toBe('filename');
        });
    });
});
