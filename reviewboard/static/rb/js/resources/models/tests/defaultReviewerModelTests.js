suite('rb/resources/models/DefaultReviewer', function() {
    var model;

    beforeEach(function() {
        model = new RB.DefaultReviewer();
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                default_reviewer: {
                    id: 42,
                    name: 'my-default-reviewer',
                    file_regex: '/foo/.*'
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.name).toBe('my-default-reviewer');
            expect(data.fileRegex).toBe('/foo/.*');
        });
    });

    describe('toJSON', function() {
        describe('name field', function() {
            it('With value', function() {
                var data;

                model.set('name', 'foo');
                data = model.toJSON();
                expect(data.name).toBe('foo');
            });
        });

        describe('fileRegex field', function() {
            it('With value', function() {
                var data;

                model.set('fileRegex', '/foo/.*');
                data = model.toJSON();
                expect(data.file_regex).toBe('/foo/.*');
            });
        });
    });
});
