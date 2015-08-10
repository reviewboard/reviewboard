suite('djblets/configForms/views/ListItemView', function() {
    describe('Rendering', function() {
        describe('Item display', function() {
            it('With editURL', function() {
                var item = new Djblets.Config.ListItem({
                        editURL: 'http://example.com/',
                        text: 'Label'
                    }),
                    itemView = new Djblets.Config.ListItemView({
                        model: item
                    });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe(
                    '<span class="config-forms-list-item-actions"></span>' +
                    '<a href="http://example.com/">Label</a>');
            });

            it('Without editURL', function() {
                var item = new Djblets.Config.ListItem({
                        text: 'Label'
                    }),
                    itemView = new Djblets.Config.ListItemView({
                        model: item
                    });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe(
                    '<span class="config-forms-list-item-actions"></span>' +
                    'Label');
            });
        });

        describe('Actions', function() {
            describe('Buttons', function() {
                it('Simple', function() {
                    var item = new Djblets.Config.ListItem({
                            text: 'Label',
                            actions: [
                                {
                                    id: 'mybutton',
                                    label: 'Button'
                                }
                            ]
                        }),
                        itemView = new Djblets.Config.ListItemView({
                            model: item
                        }),
                        $button;

                    itemView.render();

                    $button = itemView.$('.btn');
                    expect($button.length).toBe(1);
                    expect($button.text()).toBe('Button');
                    expect($button.hasClass(
                        'config-forms-list-action-mybutton')).toBe(true);
                    expect($button.hasClass('rb-icon')).toBe(false);
                    expect($button.hasClass('danger')).toBe(false);
                });

                it('Danger', function() {
                    var item = new Djblets.Config.ListItem({
                            text: 'Label',
                            actions: [
                                {
                                    id: 'mybutton',
                                    label: 'Button',
                                    danger: true
                                }
                            ]
                        }),
                        itemView = new Djblets.Config.ListItemView({
                            model: item
                        }),
                        $button;

                    itemView.render();

                    $button = itemView.$('.btn');
                    expect($button.length).toBe(1);
                    expect($button.text()).toBe('Button');
                    expect($button.hasClass(
                        'config-forms-list-action-mybutton')).toBe(true);
                    expect($button.hasClass('rb-icon')).toBe(false);
                    expect($button.hasClass('danger')).toBe(true);
                });

                it('Icon names', function() {
                    var item = new Djblets.Config.ListItem({
                            text: 'Label',
                            actions: [
                                {
                                    id: 'mybutton',
                                    label: 'Button',
                                    danger: false,
                                    iconName: 'foo'
                                }
                            ]
                        }),
                        itemView = new Djblets.Config.ListItemView({
                            model: item
                        }),
                        $button,
                        $span;

                    itemView.render();

                    $button = itemView.$('.btn');
                    expect($button.length).toBe(1);
                    expect($button.text()).toBe('Button');
                    expect($button.hasClass(
                        'config-forms-list-action-mybutton')).toBe(true);
                    expect($button.hasClass('danger')).toBe(false);

                    $span = $button.find('span');
                    expect($span.length).toBe(1);
                    expect($span.hasClass('djblets-icon')).toBe(true);
                    expect($span.hasClass('djblets-icon-foo')).toBe(true);
                });
            });

            it('Checkboxes', function() {
                var item = new Djblets.Config.ListItem({
                        text: 'Label',
                        checkboxAttr: false,
                        actions: [
                            {
                                id: 'mycheckbox',
                                type: 'checkbox',
                                label: 'Checkbox',
                                propName: 'checkboxAttr'
                            }
                        ]
                    }),
                    itemView = new Djblets.Config.ListItemView({
                        model: item
                    });

                itemView.render();

                expect(itemView.$('input[type=checkbox]').length).toBe(1);
                expect(itemView.$('label').length).toBe(1);
            });

            it('Menus', function() {
                var item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mymenu',
                                label: 'Menu',
                                children: [
                                    {
                                        id: 'mymenuitem',
                                        label: 'My menu item'
                                    }
                                ]
                            }
                        ]
                    }),
                    itemView = new Djblets.Config.ListItemView({
                        model: item
                    }),
                    $button;

                itemView.render();

                $button = itemView.$('.btn');
                expect($button.length).toBe(1);
                expect($button.text()).toBe('Menu ▾');
            });
        });
    });

    describe('Action handlers', function() {
        it('Buttons', function() {
            var item = new Djblets.Config.ListItem({
                    text: 'Label',
                    actions: [
                        {
                            id: 'mybutton',
                            label: 'Button'
                        }
                    ]
                }),
                itemView = new Djblets.Config.ListItemView({
                    model: item
                }),
                $button;

            itemView.actionHandlers = {
                mybutton: '_onMyButtonClick'
            };
            itemView._onMyButtonClick = function() {};
            spyOn(itemView, '_onMyButtonClick');

            itemView.render();

            $button = itemView.$('.btn');
            expect($button.length).toBe(1);
            $button.click();

            expect(itemView._onMyButtonClick).toHaveBeenCalled();
        });

        it('Checkboxes', function() {
            var item = new Djblets.Config.ListItem({
                    text: 'Label',
                    checkboxAttr: false,
                    actions: [
                        {
                            id: 'mycheckbox',
                            type: 'checkbox',
                            label: 'Checkbox',
                            propName: 'checkboxAttr'
                        }
                    ]
                }),
                itemView = new Djblets.Config.ListItemView({
                    model: item
                }),
                $checkbox;

            itemView.actionHandlers = {
                mybutton: '_onMyButtonClick'
            };
            itemView._onMyButtonClick = function() {};
            spyOn(itemView, '_onMyButtonClick');

            itemView.render();

            $checkbox = itemView.$('input[type=checkbox]');
            expect($checkbox.length).toBe(1);
            expect($checkbox.prop('checked')).toBe(false);
            $checkbox
                .prop('checked', true)
                .triggerHandler('change');

            expect(item.get('checkboxAttr')).toBe(true);
        });
    });
});
