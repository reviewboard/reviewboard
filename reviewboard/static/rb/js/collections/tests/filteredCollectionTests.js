suite('rb/collections/FilteredCollection', function() {
    var mainCollection,
        filteredCollection;

    beforeEach(function() {
        mainCollection = new Backbone.Collection([
            {
                id: 1,
                label: 'One',
                bool: true
            },
            {
                id: 2,
                label: 'Two',
                bool: false
            },
            {
                id: 3,
                label: 'Three',
                bool: true
            }
        ]);
    });

    describe('Initialization', function() {
        it('Defaults to full contents', function() {
            filteredCollection = new RB.FilteredCollection(null, {
                collection: mainCollection
            });

            expect(filteredCollection.length).toBe(mainCollection.length);
        });

        it('Respects provided filter', function() {
            filteredCollection = new RB.FilteredCollection(null, {
                collection: mainCollection,
                filters: {
                    label: 'T'
                }
            });

            expect(filteredCollection.length).toBe(2);
            expect(filteredCollection.at(0).id).toBe(2);
            expect(filteredCollection.at(1).id).toBe(3);
        });
    });

    describe('Methods', function() {
        beforeEach(function() {
            filteredCollection = new RB.FilteredCollection(null, {
                collection: mainCollection,
                filters: {
                    label: 'T'
                }
            });

            expect(filteredCollection.length).toBe(2);
        });

        describe('setFilters', function() {
            it('With new filter', function() {
                filteredCollection.setFilters({
                    label: 'O'
                });

                expect(filteredCollection.length).toBe(1);
                expect(filteredCollection.at(0).id).toBe(1);
            });

            it('With multiple filters', function() {
                filteredCollection.setFilters({
                    label: 'T',
                    bool: false
                });

                expect(filteredCollection.length).toBe(1);
                expect(filteredCollection.at(0).id).toBe(2);
            });

            it('{}', function() {
                filteredCollection.setFilters({});

                expect(filteredCollection.length).toBe(3);
            });

            it('null', function() {
                filteredCollection.setFilters(null);

                expect(filteredCollection.length).toBe(3);
            });

            it('undefined', function() {
                filteredCollection.setFilters();

                expect(filteredCollection.length).toBe(3);
            });
        });
    });

    describe('Main collection events', function() {
        describe('With filters', function() {
            beforeEach(function() {
                filteredCollection = new RB.FilteredCollection(null, {
                    collection: mainCollection,
                    filters: {
                        label: 'T'
                    }
                });

                expect(filteredCollection.length).toBe(2);
            });

            it('reset', function() {
                mainCollection.reset([
                    {
                        id: 10,
                        label: 'Monday'
                    },
                    {
                        id: 11,
                        label: 'Tuesday'
                    }
                ]);

                expect(filteredCollection.length).toBe(1);
                expect(filteredCollection.at(0).id).toBe(11);
            });

            describe('add', function() {
                it('Matching filter', function() {
                    mainCollection.add({
                        id: 4,
                        label: 'Test'
                    });

                    expect(filteredCollection.length).toBe(3);
                    expect(filteredCollection.at(2).id).toBe(4);
                });

                it('Not matching filter', function() {
                    mainCollection.add({
                        id: 4,
                        label: 'Four'
                    });

                    expect(filteredCollection.length).toBe(2);
                });
            });

            describe('remove', function() {
                it('Matching filter', function() {
                    mainCollection.remove(mainCollection.get(2));

                    expect(filteredCollection.length).toBe(1);
                });

                it('Not matching filter', function() {
                    mainCollection.remove(mainCollection.get(0));

                    expect(filteredCollection.length).toBe(2);
                });
            });
        });

        describe('Without filters', function() {
            beforeEach(function() {
                filteredCollection = new RB.FilteredCollection(null, {
                    collection: mainCollection
                });

                expect(filteredCollection.length).toBe(3);
            });

            it('reset', function() {
                mainCollection.reset([
                    {
                        id: 10,
                        label: 'Monday'
                    },
                    {
                        id: 11,
                        label: 'Tuesday'
                    }
                ]);

                expect(filteredCollection.length).toBe(2);
            });

            it('add', function() {
                mainCollection.add({
                    id: 4,
                    label: 'Four'
                });

                expect(filteredCollection.length).toBe(4);
                expect(filteredCollection.at(3).id).toBe(4);
            });

            it('remove', function() {
                mainCollection.remove(mainCollection.get(1));
                expect(filteredCollection.length).toBe(2);
            });
        });
    });
});
