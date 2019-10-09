suite('rb/views/CollectionView', function() {
    let collection;
    let view;

    const TestModel = Backbone.Model.extend({
        defaults: _.defaults({
            data: '',
        }),
    });

    const TestCollection = Backbone.Collection.extend({
        model: TestModel,
    });

    const TestModelView = Backbone.View.extend({
        className: 'test-class',
        render() {
            this.$el.text(this.model.get('data'));
            return this;
        },
    });

    const TestCollectionView = RB.CollectionView.extend({
        itemViewType: TestModelView,
    });

    beforeEach(function() {
        collection = new TestCollection();
        view = new TestCollectionView({
            collection: collection,
        });
    });

    describe('Rendering', function() {
        it('When empty', function() {
            view.render();
            expect(view.$el.children().length).toBe(0);
        });

        it('With items', function() {
            collection.add([
                { data: 'Item 1' },
                { data: 'Item 2' },
            ]);

            view.render();
            const $children = view.$el.children();
            expect($children.length).toBe(2);
            expect($children[0].innerHTML).toBe('Item 1');
            expect($children[1].innerHTML).toBe('Item 2');
        });

        it('Item model type', function() {
            collection.add([
                { data: 'Item 1' },
            ]);

            view.render();
            expect(view.$el.children().hasClass('test-class')).toBe(true);
        });

        it('With custom element container', function() {
            const $container = $('<div class="rb-test-main-container"/>')
                .appendTo(view.$el);

            view.$container = $container;

            collection.add([
                { data: 'Item 1' },
                { data: 'Item 2' },
            ]);

            view.render();

            const $viewChildren = view.$el.children();
            expect($viewChildren.length).toBe(1);
            expect($viewChildren[0].className).toBe('rb-test-main-container');

            const $containerChildren = $viewChildren.eq(0).children();
            expect($containerChildren.length).toBe(2);
            expect($containerChildren[0].innerHTML).toBe('Item 1');
            expect($containerChildren[1].innerHTML).toBe('Item 2');
        });
    });

    describe('Live updating', function() {
        it('Adding items after rendering', function() {
            collection.add([
                { data: 'Item 1' },
            ]);

            view.render();

            expect(view.$el.children().length).toBe(1);

            collection.add([
                { data: 'Item 2' },
                { data: 'Item 3' },
            ]);

            const $children = view.$el.children();
            expect($children.length).toBe(3);
            expect($children[2].innerHTML).toBe('Item 3');
        });

        it('Removing items after rendering', function() {
            const model1 = new TestModel({ data: 'Item 1' });
            const model2 = new TestModel({ data: 'Item 2' });
            const model3 = new TestModel({ data: 'Item 3' });
            collection.add([model1, model2, model3]);

            view.render();

            expect(view.$el.children().length).toBe(3);

            collection.remove([model1, model3]);

            const $children = view.$el.children();
            expect($children.length).toBe(1);
            expect($children[0].innerHTML).toBe('Item 2');
        });

        it('Changing sort order', function() {
            collection.add([
                { data: 'Item 2' },
                { data: 'Item 3' },
                { data: 'Item 1' },
            ]);

            view.render();

            let $children = view.$el.children();
            expect($children.length).toBe(3);
            expect($children[0].innerHTML).toBe('Item 2');
            expect($children[1].innerHTML).toBe('Item 3');
            expect($children[2].innerHTML).toBe('Item 1');

            collection.comparator = 'data';
            collection.sort();

            $children = view.$el.children();
            expect($children[0].innerHTML).toBe('Item 1');
            expect($children[1].innerHTML).toBe('Item 2');
            expect($children[2].innerHTML).toBe('Item 3');
        });

        it('When reset', function() {
            collection.add([
                { data: 'Item 1' },
                { data: 'Item 2' },
            ]);

            view.render();

            let $children = view.$el.children();
            expect($children.length).toBe(2);
            expect($children[0].innerHTML).toBe('Item 1');
            expect($children[1].innerHTML).toBe('Item 2');

            collection.reset([
                { data: 'Item 3' },
                { data: 'Item 4' },
                { data: 'Item 5' },
            ]);

            $children = view.$el.children();
            expect($children.length).toBe(3);
            expect($children[0].innerHTML).toBe('Item 3');
            expect($children[1].innerHTML).toBe('Item 4');
            expect($children[2].innerHTML).toBe('Item 5');
        });
    });
});
