suite('rb/resources/collections/RepositoryBranches', function() {
    var collection;

    beforeEach(function() {
        collection = new RB.RepositoryBranches();
        collection.url = '/api/repositories/123/branches/';
    });

    describe('Methods', function() {
        it('fetch', function() {
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.url)
                    .toBe('/api/repositories/123/branches/');
                expect(request.type).toBe('GET');

                request.success({
                    stat: 'ok',
                    branches: [
                        {
                            name: 'master',
                            commit: '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                            'default': true
                        },
                        {
                            name: 'release-1.7.x',
                            commit: '92463764015ef463b4b6d1a1825fee7aeec8cb15',
                            'default': false
                        },
                        {
                            name: 'release-1.6.x',
                            commit: 'a15d0e635064a2e1929ce1bf3bc8d4aa65738b64',
                            'default': false
                        }
                    ]
                });
            });

            collection.fetch();

            expect($.ajax).toHaveBeenCalled();
            expect(collection.length).toBe(3);
            expect(collection.at(0).get('name')).toBe('master');
            expect(collection.at(1).get('commit'))
                .toBe('92463764015ef463b4b6d1a1825fee7aeec8cb15');
            expect(collection.at(2).get('isDefault')).toBe(false);

            expect(collection.reduce(function(memo, item) {
                return memo + item.get('isDefault') ? 1 : 0;
            }, 0)).toBe(1);
        });
    });
});
