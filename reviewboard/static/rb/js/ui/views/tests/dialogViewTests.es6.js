suite('rb/ui/views/DialogView', function() {
    describe('Buttons', function() {
        describe('Settings', function() {
            it('Default', function() {
                const dialogView = new RB.DialogView({
                    buttons: [
                        {
                            label: 'Test',
                            id: 'testid',
                        }
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('primary')).toBe(false);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Primary', function() {
                const dialogView = new RB.DialogView({
                    buttons: [
                        {
                            label: 'Test',
                            id: 'testid',
                            primary: true,
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('primary')).toBe(true);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Disabled', function() {
                const dialogView = new RB.DialogView({
                    buttons: [
                        {
                            label: 'Test',
                            id: 'testid',
                            disabled: true,
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.val()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(true);
                expect(button.hasClass('primary')).toBe(false);
                expect(button.hasClass('danger')).toBe(false);
            });

            it('Danger', function() {
                const dialogView = new RB.DialogView({
                    buttons: [
                        {
                            label: 'Test',
                            id: 'testid',
                            danger: true,
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

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
                    const myFunc = jasmine.createSpy('cb');
                    const dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid',
                                onClick: myFunc,
                            },
                        ],
                    });
                    dialogView._makeButtons();

                    const buttons = dialogView.$buttonsMap;
                    const button = buttons.testid;

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.val()).toBe('Test');
                    button.click();
                    expect(myFunc).toHaveBeenCalled();
                });

                it('When string on subclass', function() {
                    const MyDialogView = RB.DialogView.extend({
                        buttons: [
                            {
                                label: 'Test',
                                id: 'testid',
                                onClick: '_onClicked',
                            },
                        ],

                        _onClicked: jasmine.createSpy('cb'),
                    });
                    const dialogView = new MyDialogView();
                    dialogView._makeButtons();

                    const buttons = dialogView.$buttonsMap;
                    const button = buttons.testid;

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.val()).toBe('Test');
                    button.click();
                    expect(dialogView._onClicked).toHaveBeenCalled();
                });
            });
        });
    });
});
