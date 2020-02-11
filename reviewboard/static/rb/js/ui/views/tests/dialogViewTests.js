suite('rb/ui/views/DialogView', function() {
    describe('Buttons', function() {
        describe('Settings', function() {
            it('Default', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid'
                            }
                        ]
                    });
                dialogView._makeButtons();
                var buttons = dialogView.$buttonsMap,
                    button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('primary')).toBe(false);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Primary', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid',
                                primary: true
                            }
                        ]
                    });
                dialogView._makeButtons();
                var buttons = dialogView.$buttonsMap,
                    button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('primary')).toBe(true);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Disabled', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid',
                                disabled: true
                            }
                        ]
                    });
                dialogView._makeButtons();
                var buttons = dialogView.$buttonsMap,
                    button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(true);
                expect(button.hasClass('primary')).toBe(false);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Danger', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid',
                                danger: true
                            }
                        ]
                    });
                dialogView._makeButtons();
                var buttons = dialogView.$buttonsMap,
                    button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('primary')).toBe(false);
                expect(button.hasClass('danger')).toBe(true);
            });
        });

        describe('Events', function() {
            describe('Click', function() {
                it('When function', function() {
                    var myFunc = jasmine.createSpy('cb'),
                        dialogView = new RB.DialogView({
                            buttons: [
                                {
                                    label: 'Test',
                                    id: 'testid',
                                    onClick: myFunc
                                }
                            ]
                        });
                    dialogView._makeButtons();
                    var buttons = dialogView.$buttonsMap,
                        button = buttons.testid;

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.val()).toBe('Test');
                    button.click();
                    expect(myFunc).toHaveBeenCalled();
                });

                it('When string on subclass', function() {
                    var MyDialogView = RB.DialogView.extend({
                            buttons: [
                                {
                                    label: 'Test',
                                    id: 'testid',
                                    onClick: '_onClicked'
                                }
                            ],

                            _onClicked: jasmine.createSpy('cb')
                        }),
                        dialogView = new MyDialogView();

                    dialogView._makeButtons();
                    var buttons = dialogView.$buttonsMap,
                        button = buttons.testid;

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.val()).toBe('Test');
                    button.click();
                    expect(dialogView._onClicked).toHaveBeenCalled();
                });
            });
        });
    });
});
