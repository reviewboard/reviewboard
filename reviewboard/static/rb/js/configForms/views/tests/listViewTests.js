describe('configForms/views/ListView', function() {
    describe('Manages items', function() {
        var collection,
            list,
            listView;

        beforeEach(function() {
            collection = new Backbone.Collection(
                [
                    {text: 'Item 1'},
                    {text: 'Item 2'},
                    {text: 'Item 3'}
                ], {
                    model: RB.Config.ListItem
                });

            list = new RB.Config.List({}, {
                collection: collection
            });

            listView = new RB.Config.ListView({
                model: list
            });
        });

        it('On render', function() {
            var $items;

            listView.render();

            $items = listView.$('li');
            expect($items.length).toBe(3);
            expect($items.eq(0).text().strip()).toBe('Item 1');
            expect($items.eq(1).text().strip()).toBe('Item 2');
            expect($items.eq(2).text().strip()).toBe('Item 3');
        });

        it('On add', function() {
            var $items;

            listView.render();

            collection.add({
                text: 'Item 4'
            });

            $items = listView.$('li');
            expect($items.length).toBe(4);
            expect($items.eq(3).text().strip()).toBe('Item 4');
        });

        it('On remove', function() {
            var $items;

            listView.render();

            collection.remove(collection.at(0));

            $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().strip()).toBe('Item 2');
        });

        it('On reset', function() {
            var $items;

            listView.render();

            collection.reset([
                {text: 'Foo'},
                {text: 'Bar'}
            ]);

            $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().strip()).toBe('Foo');
            expect($items.eq(1).text().strip()).toBe('Bar');
        });
    });
});
