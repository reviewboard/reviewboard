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
            expect(data.baseCommitID).toBe(null);
            expect(data.tipCommitID).toBe(null);
        });

        it('API payloads with base/tip commit IDs', function() {
            const data = RB.DiffRevision.prototype.parse.call(undefined, {
                revision: 4,
                latest_revision: 7,
                interdiff_revision: null,
                is_interdiff: false,
                is_draft_diff: false,
                base_commit_id: 3,
                tip_commit_id: 4,
            });

            expect(data).not.toBe(undefined);
            expect(data.revision).toBe(4);
            expect(data.latestRevision).toBe(7);
            expect(data.interdiffRevision).toBe(null);
            expect(data.isInterdiff).toBe(false);
            expect(data.isDraftDiff).toBe(false);
            expect(data.baseCommitID).toBe(3);
            expect(data.tipCommitID).toBe(4);
        });
    });
});
