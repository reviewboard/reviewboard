suite('rb/resources/models/ValidateDiffModel', function() {
    let model;

    beforeEach(function() {
        model = new RB.ValidateDiffModel();
    });

    describe('methods', function() {
        describe('url', function() {
            it('Without local site', function() {
                expect(_.result(model, 'url')).toBe('/api/validation/diffs/');
            });

            it('With local site', function() {
                model.set('localSitePrefix', 's/test-site/');
                expect(_.result(model, 'url')).toBe('/s/test-site/api/validation/diffs/');
            });
        });
    });

    describe('toJSON', function() {
        it('repository field', function() {
            model.set('repository', 123);
            const data = model.toJSON();
            expect(data.repository).toBe(123);
        });
    });
});
