suite('rb/diffviewer/models/DiffFile', function() {
    var model;

    beforeEach(function() {
        model = new RB.DiffFile();
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                binary: false,
                comment_counts: [1],
                deleted: true,
                depot_filename: 'foo',
                dest_filename: 'bar',
                filediff: {
                    id: 38,
                    revision: 2
                },
                id: 28,
                index: 3,
                interfilediff: {
                    id: 23,
                    revision: 4
                },
                newfile: true,
                revision: 3
            });

            expect(data).not.toBe(undefined);
            expect(data.binary).toBe(false);
            expect(data.commentCounts).toEqual([1]);
            expect(data.deleted).toBe(true);
            expect(data.depotFilename).toBe('foo');
            expect(data.destFilename).toBe('bar');
            expect(data.filediff).not.toBe(undefined);
            expect(data.filediff.id).toBe(38);
            expect(data.filediff.revision).toBe(2);
            expect(data.id).toBe(28);
            expect(data.index).toBe(3);
            expect(data.interfilediff).not.toBe(undefined);
            expect(data.interfilediff.id).toBe(23);
            expect(data.interfilediff.revision).toBe(4);
            expect(data.newfile).toBe(true);
            expect(data.revision).toBe(3);
        });
    });
});
