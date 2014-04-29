suite('rb/resources/models/RepositoryBranch', function() {
    var model;

    beforeEach(function() {
        model = new RB.RepositoryBranch();
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                name: 'master',
                commit: 'c8ffef025488802a77f499d7f0d24579d858b07e',
                'default': true
            });

            expect(data).not.toBe(undefined);
            expect(data.name).toBe('master');
            expect(data.commit)
                .toBe('c8ffef025488802a77f499d7f0d24579d858b07e');
            expect(data.isDefault).toBe(true);
        });
    });
});
