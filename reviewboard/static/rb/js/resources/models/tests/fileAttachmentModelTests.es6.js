suite('rb/resources/models/FileAttachment', function() {
    let model;

    beforeEach(function() {
        model = new RB.FileAttachment({
            parentObject: new RB.BaseResource({
                'public': true,
            }),
        });
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
            it('With new file attachment', function() {
                expect(model.isNew()).toBe(true);

                model.set('file', 'abc');
                const data = model.toJSON();
                expect(data.path).toBe('abc');
            });

            it('With existing file attachment', function() {
                model.id = 123;
                model.attributes.id = 123;
                expect(model.isNew()).toBe(false);

                model.set('file', 'abc');
                const data = model.toJSON();
                expect(data.path).toBe(undefined);
            });
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                file_attachment: {
                    id: 42,
                    caption: 'caption',
                    url: 'downloadURL',
                    filename: 'filename',
                    review_url: 'reviewURL',
                    revision: 123,
                    thumbnail: 'thumbnailHTML',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.caption).toBe('caption');
            expect(data.downloadURL).toBe('downloadURL');
            expect(data.filename).toBe('filename');
            expect(data.reviewURL).toBe('reviewURL');
            expect(data.revision).toBe(123);
            expect(data.thumbnailHTML).toBe('thumbnailHTML');
        });
    });
});
