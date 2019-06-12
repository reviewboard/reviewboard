suite('rb/newReviewRequest/views/BranchesView', function() {
    let collection;
    let view;

    beforeEach(function() {
        collection = new RB.RepositoryBranches([
            {
                name: 'master',
                commit: '8088295174d8d46af7700ddf4522e3a703724106',
                isDefault: true,
            },
            {
                name: 'release-1.7.x',
                commit: '5e6707050f7cb29ed50fafd3b92bffb1e15df19f',
                isDefault: false,
            },
            {
                name: 'release-1.6.x',
                commit: 'a15d0e635064a2e1929ce1bf3bc8d4aa65738b64',
                isDefault: false,
            }
        ]);

        view = new RB.BranchesView({
            collection: collection,
        });
    });

    describe('Rendering', function() {
        it('With items', function() {
            view.render();
            expect(view.$el.html()).toBe(
                '<option selected="selected">master</option>' +
                '<option>release-1.7.x</option>' +
                '<option>release-1.6.x</option>');
        });
    });

    describe('Selected event', function() {
        it('When clicked', function() {
            view.render();

            view.on('selected', branch => {
                expect(branch.get('name')).toBe('release-1.7.x');
            });

            const children = view.$el.children();

            $(children[0]).attr('selected', false);
            $(children[1]).attr('selected', true);
            view.$el.change();

            expect(view.$el.html()).toBe(
                '<option>master</option>' +
                '<option selected="selected">release-1.7.x</option>' +
                '<option>release-1.6.x</option>');
        });
    });
});
