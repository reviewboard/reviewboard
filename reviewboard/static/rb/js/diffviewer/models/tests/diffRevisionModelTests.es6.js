suite('rb/diffviewer/models/DiffRevision', function() {
    describe('parse', function() {
        it('API payloads', function() {
            const data = RB.DiffRevision.prototype.parse.call(undefined, {
                revision: 2,
                latest_revision: 3,
                interdiff_revision: 4,
                is_interdiff: true,
                is_draft_diff: true,
            });

            expect(data).not.toBe(undefined);
            expect(data.revision).toBe(2);
            expect(data.latestRevision).toBe(3);
            expect(data.interdiffRevision).toBe(4);
            expect(data.isInterdiff).toBe(true);
            expect(data.isDraftDiff).toBe(true);
        });
    });
});
