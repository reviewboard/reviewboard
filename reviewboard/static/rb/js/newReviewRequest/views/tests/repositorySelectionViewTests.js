suite('rb/newReviewRequest/views/RepositorySelectionView', function() {
    var collection,
        view;

    beforeEach(function() {
        collection = new Backbone.Collection([
            { name: 'Repo 1' },
            { name: 'Repo 2' },
            { name: 'Repo 3' }
        ], {
            model: RB.Repository
        });

        view = new RB.RepositorySelectionView({
            collection: collection
        });
    });

    describe('Rendering', function() {
        it('With items', function() {
            var children,
                i,
                count,
                name;

            view.render();
            children = view.$el.children('.repository');
            count = children.length;

            expect(count).toBe(collection.models.length);

            for (i = 0; i < count; i++) {
                name = collection.models[i].get('name');
                expect($(children[i]).text()).toBe(name);
            }
        });
    });

    describe('Selected event', function() {
        it('When clicked', function() {
            var children;

            view.render();
            view.on('selected', function(repository) {
                expect(repository.get('name')).toBe('Repo 2');
            });

            children = view.$el.children('.repository');
            $(children[1]).click();
        });
    });
});
