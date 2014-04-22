suite('rb/resources/models/FileDiff', function() {
    var model;

    beforeEach(function() {
        model = new RB.FileDiff({
            destFilename: 'dest-file',
            sourceFilename: 'source-file',
            sourceRevision: 'source-revision'
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                filediff: {
                    id: 42,
                    dest_file: 'my-dest-file',
                    source_file: 'my-source-file',
                    source_revision: 'my-source-revision'
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.destFilename).toBe('my-dest-file');
            expect(data.sourceFilename).toBe('my-source-file');
            expect(data.sourceRevision).toBe('my-source-revision');
        });
    });
});
