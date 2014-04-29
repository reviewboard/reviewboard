suite('rb/views/CollectionView', function() {
    var TestModel,
        TestCollection,
        TestModelView,
        TestCollectionView,
        collection,
        view;

    TestModel = Backbone.Model.extend({
        defaults: _.defaults({
            data: ''
        })
    });

    TestCollection = Backbone.Collection.extend({
        model: TestModel
    });

    TestModelView = Backbone.View.extend({
        className: 'test-class',
        render: function() {
            this.$el.text(this.model.get('data'));
            return this;
        }
    });

    TestCollectionView = RB.CollectionView.extend({
        itemViewType: TestModelView
    });

    beforeEach(function() {
        collection = new TestCollection();
        view = new TestCollectionView({
            collection: collection
        });
    });

    describe('Rendering', function() {
        it('When empty', function() {
            view.render();
            expect(view.$el.children().length).toBe(0);
        });

        it('With items', function() {
            var $children;

            collection.add([
                { data: 'Item 1' },
                { data: 'Item 2' }
            ]);

            view.render();
            $children = view.$el.children();
            expect($children.length).toBe(2);
            expect($children[0].innerHTML).toBe('Item 1');
            expect($children[1].innerHTML).toBe('Item 2');
        });

        it('Item model type', function() {
            collection.add([
                { data: 'Item 1' }
            ]);

            view.render();
            expect(view.$el.children().hasClass('test-class')).toBe(true);
        });
    });

    describe('Live updating', function() {
        it('Adding items after rendering', function() {
            var $children;

            collection.add([
                { data: 'Item 1' }
            ]);

            view.render();

            expect(view.$el.children().length).toBe(1);

            collection.add([
                { data: 'Item 2' },
                { data: 'Item 3' }
            ]);

            $children = view.$el.children();
            expect($children.length).toBe(3);
            expect($children[2].innerHTML).toBe('Item 3');
        });

        it('Removing items after rendering', function() {
            var model1 = new TestModel({ data: 'Item 1' }),
                model2 = new TestModel({ data: 'Item 2' }),
                model3 = new TestModel({ data: 'Item 3' }),
                $children;

            collection.add([model1, model2, model3]);

            view.render();

            expect(view.$el.children().length).toBe(3);

            collection.remove([model1, model3]);

            $children = view.$el.children();
            expect($children.length).toBe(1);
            expect($children[0].innerHTML).toBe('Item 2');
        });
    });
});
