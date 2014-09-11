suite('rb/ui/views/DialogView', function() {
    describe('Buttons', function() {
        describe('Settings', function() {
            it('Default', function() {
                var dialogView = new RB.DialogView({
                        buttons: [{label: 'Test'}]
                    }),
                    buttons = dialogView._getButtons();

                expect(buttons.length).toBe(1);
                expect(buttons[0].val()).toBe('Test');
                expect(buttons[0].hasClass('primary')).toBe(false);
                expect(buttons[0].hasClass('danger')).toBe(false);
            });

            it('Primary', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                primary: true
                            }
                        ]
                    }),
                    buttons = dialogView._getButtons();

                expect(buttons.length).toBe(1);
                expect(buttons[0].val()).toBe('Test');
                expect(buttons[0].hasClass('primary')).toBe(true);
                expect(buttons[0].hasClass('danger')).toBe(false);
            });

            it('Danger', function() {
                var dialogView = new RB.DialogView({
                        buttons: [
                            {
                                label: 'Test',
                                danger: true
                            }
                        ]
                    }),
                    buttons = dialogView._getButtons();

                expect(buttons.length).toBe(1);
                expect(buttons[0].val()).toBe('Test');
                expect(buttons[0].hasClass('primary')).toBe(false);
                expect(buttons[0].hasClass('danger')).toBe(true);
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
                                    onClick: myFunc
                                }
                            ]
                        }),
                        buttons = dialogView._getButtons();

                    expect(buttons.length).toBe(1);
                    expect(buttons[0].val()).toBe('Test');
                    buttons[0].click();
                    expect(myFunc).toHaveBeenCalled();
                });

                it('When string on subclass', function() {
                    var MyDialogView = RB.DialogView.extend({
                            buttons: [
                                {
                                    label: 'Test',
                                    onClick: '_onClicked'
                                }
                            ],

                            _onClicked: jasmine.createSpy('cb')
                        }),
                        dialogView = new MyDialogView(),
                        buttons = dialogView._getButtons();

                    expect(buttons.length).toBe(1);
                    expect(buttons[0].val()).toBe('Test');
                    buttons[0].click();
                    expect(dialogView._onClicked).toHaveBeenCalled();
                });
            });
        });
    });
});
