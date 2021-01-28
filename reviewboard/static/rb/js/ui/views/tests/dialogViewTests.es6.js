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

                describe('Keydown', function() {
                    it('Esc key', function() {
                        const dialogView = new RB.DialogView({
                            buttons: [{
                                id: 'testid',
                                label: 'Test',
                            }],
                        });

                        dialogView.show();

                        const myFunc = jasmine.createSpy('hide');
                        dialogView.hide = myFunc;

                        const buttons = dialogView.$buttonsMap;
                        expect(Object.keys(buttons).length).toBe(1);
                        expect(buttons.testid.val()).toBe('Test');

                        dialogView.$el.trigger(
                            $.Event('keydown', { which: $.ui.keyCode.ESCAPE }));

                        expect(myFunc).toHaveBeenCalled();

                        dialogView.remove();
                    });
                });

                describe('Submit', function() {
                    it('with primary button enabled', function() {
                        const myFunc = jasmine.createSpy('cb');
                        const dialogView = new RB.DialogView({
                            buttons: [{
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc,
                                disabled: false,
                                primary: true,
                            }],
                            body: _.template(dedent`
                                <form>
                                 <input value="test">
                                </form>
                            `),
                        });

                        dialogView.show();

                        const buttons = dialogView.$buttonsMap;
                        const button = buttons.testid;
                        const form = dialogView.$el.find('form');

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.val()).toBe('Test');
                        expect(button.prop('disabled')).toBe(false);
                        expect(button.hasClass('primary')).toBe(true);

                        form.trigger($.Event('submit'));
                        expect(myFunc).toHaveBeenCalled();

                        dialogView.remove();
                    });

                    it('with primary button disabled', function() {
                        const myFunc = jasmine.createSpy('cb');
                        const dialogView = new RB.DialogView({
                            buttons: [{
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc,
                                disabled: true,
                                primary: true,
                            }],
                            body: _.template(dedent`
                                <form>
                                 <input value="test">
                                </form>
                            `),
                        });

                        dialogView.show();

                        const buttons = dialogView.$buttonsMap;
                        const button = buttons.testid;
                        const form = dialogView.$el.find('form');

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.val()).toBe('Test')
                        expect(button.prop('disabled')).toBe(true);
                        expect(button.hasClass('primary')).toBe(true);

                        form.trigger($.Event('submit'));
                        expect(myFunc).not.toHaveBeenCalled();

                        dialogView.remove();
                    });

                    it('with explicit action', function() {
                        const myFunc1 = jasmine.createSpy('cb1');
                        const myFunc2 = jasmine.createSpy('cb2')
                            .and.returnValue(false);
                        const dialogView = new RB.DialogView({
                            buttons: [{
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc1,
                                disabled: false,
                                primary: true,
                            }],
                            body: _.template(dedent`
                                <form action=".">
                                 <input value="test">
                                </form>
                            `),
                        });

                        dialogView.show();

                        const buttons = dialogView.$buttonsMap;
                        const button = buttons.testid;
                        const form = dialogView.$el.find('form');
                        form.submit(myFunc2);

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.val()).toBe('Test');
                        expect(button.prop('disabled')).toBe(false);
                        expect(button.hasClass('primary')).toBe(true);

                        form.trigger($.Event('submit'));
                        expect(myFunc1).not.toHaveBeenCalled();
                        expect(myFunc2).toHaveBeenCalled();

                        dialogView.remove();
                    });
                });
            });
        });
    });
});
