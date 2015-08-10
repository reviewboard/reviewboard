suite('djblets/configForms/views/TableItemView', function() {
    describe('Rendering', function() {
        describe('Item display', function() {
            it('With editURL', function() {
                var item = new Djblets.Config.ListItem({
                        editURL: 'http://example.com/',
                        text: 'Label'
                    }),
                    itemView = new Djblets.Config.TableItemView({
                        model: item
                    });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe(
                    '<td>' +
                    '<span class="config-forms-list-item-actions"></span>' +
                    '<a href="http://example.com/">Label</a>' +
                    '</td>');
            });

            it('Without editURL', function() {
                var item = new Djblets.Config.ListItem({
                        text: 'Label'
                    }),
                    itemView = new Djblets.Config.TableItemView({
                        model: item
                    });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe(
                    '<td>' +
                    '<span class="config-forms-list-item-actions"></span>' +
                    'Label' +
                    '</td>');
            });
        });

        describe('Action placement', function() {
            it('Default template', function() {
                var item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button'
                            }
                        ]
                    }),
                    itemView = new Djblets.Config.TableItemView({
                        model: item
                    }),
                    $button;

                itemView.render();

                $button = itemView.$('td:last .btn');
                expect($button.length).toBe(1);
                expect($button.text()).toBe('Button');
            });

            it('Custom template', function() {
                var CustomTableItemView = Djblets.Config.TableItemView.extend({
                        template: _.template([
                            '<td></td>',
                            '<td></td>'
                        ].join(''))
                    }),
                    item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button'
                            }
                        ]
                    }),
                    itemView = new CustomTableItemView({
                        model: item
                    }),
                    $button;

                itemView.render();

                $button = itemView.$('td:last .btn');
                expect($button.length).toBe(1);
                expect($button.text()).toBe('Button');
            });
        });
    });
});
