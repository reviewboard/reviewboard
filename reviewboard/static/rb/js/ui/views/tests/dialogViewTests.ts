import { suite } from '@beanbag/jasmine-suites';
import {
    describe,
    expect,
    it,
} from 'jasmine-core';

import { DialogView } from 'reviewboard/ui';


suite('rb/ui/views/DialogView', function() {
    describe('Buttons', function() {
        describe('Settings', function() {
            it('Default', function() {
                const dialogView = new DialogView({
                    buttons: [
                        {
                            id: 'testid',
                            label: 'Test',
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.text()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('-is-primary')).toBe(false);
                expect(button.hasClass('-is-danger')).toBe(false);
            });

            it('Primary', function() {
                const dialogView = new DialogView({
                    buttons: [
                        {
                            id: 'testid',
                            label: 'Test',
                            primary: true,
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.text()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('-is-primary')).toBe(true);
                expect(button.hasClass('-is-danger')).toBe(false);
            });

            it('Disabled', function() {
                const dialogView = new DialogView({
                    buttons: [
                        {
                            disabled: true,
                            id: 'testid',
                            label: 'Test',
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.text()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(true);
                expect(button.hasClass('-is-primary')).toBe(false);
                expect(button.hasClass('-is-danger')).toBe(false);
            });

            it('Danger', function() {
                const dialogView = new DialogView({
                    buttons: [
                        {
                            danger: true,
                            id: 'testid',
                            label: 'Test',
                        },
                    ],
                });
                dialogView._makeButtons();

                const buttons = dialogView.$buttonsMap;
                const button = buttons.testid;

                expect(Object.keys(buttons).length).toBe(1);
                expect(button.text()).toBe('Test');
                expect(button.prop('id')).toBe('testid');
                expect(button.prop('disabled')).toBe(false);
                expect(button.hasClass('-is-primary')).toBe(false);
                expect(button.hasClass('-is-danger')).toBe(true);
            });
        });

        describe('Events', function() {
            describe('Click', function() {
                it('When function', function() {
                    const myFunc = jasmine.createSpy('cb');
                    const dialogView = new DialogView({
                        buttons: [
                            {
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc,
                            },
                        ],
                    });
                    dialogView._makeButtons();

                    const buttons = dialogView.$buttonsMap;
                    const button = buttons.testid;

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.text()).toBe('Test');
                    button.click();
                    expect(myFunc).toHaveBeenCalled();
                });

                it('When string on subclass', function() {
                    const MyDialogView = DialogView.extend({
                        buttons: [
                            {
                                id: 'testid',
                                label: 'Test',
                                onClick: '_onClicked',
                            },
                        ],

                        _onClicked: jasmine.createSpy('cb'),
                    });
                    const dialogView = new MyDialogView();
                    dialogView._makeButtons();

                    const buttons = dialogView.$buttonsMap;
                    const button = buttons['testid'];

                    expect(Object.keys(buttons).length).toBe(1);
                    expect(button.text()).toBe('Test');
                    button.click();
                    expect(dialogView._onClicked).toHaveBeenCalled();
                });

                describe('Keydown', function() {
                    it('Esc key', function() {
                        const dialogView = new DialogView({
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
                        expect(buttons.testid.text()).toBe('Test');

                        const event = new KeyboardEvent('keydown', {
                            bubbles: true,
                            key: 'Escape',
                        });
                        dialogView.el.dispatchEvent(event);

                        expect(myFunc).toHaveBeenCalled();

                        dialogView.remove();
                    });
                });

                describe('Submit', function() {
                    it('with primary button enabled', function() {
                        const myFunc = jasmine.createSpy('cb');
                        const dialogView = new DialogView({
                            body: _.template(dedent`
                                <form>
                                 <input value="test">
                                </form>
                            `),
                            buttons: [{
                                disabled: false,
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc,
                                primary: true,
                            }],
                        });

                        dialogView.show();

                        const buttons = dialogView.$buttonsMap;
                        const button = buttons.testid;
                        const form = dialogView.$el.find('form');

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.text()).toBe('Test');
                        expect(button.prop('disabled')).toBe(false);
                        expect(button.hasClass('-is-primary')).toBe(true);

                        form.trigger($.Event('submit'));
                        expect(myFunc).toHaveBeenCalled();

                        dialogView.remove();
                    });

                    it('with primary button disabled', function() {
                        const myFunc = jasmine.createSpy('cb');
                        const dialogView = new DialogView({
                            body: _.template(dedent`
                                <form>
                                 <input value="test">
                                </form>
                            `),
                            buttons: [{
                                disabled: true,
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc,
                                primary: true,
                            }],
                        });

                        dialogView.show();

                        const buttons = dialogView.$buttonsMap;
                        const button = buttons.testid;
                        const form = dialogView.$el.find('form');

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.text()).toBe('Test');
                        expect(button.prop('disabled')).toBe(true);
                        expect(button.hasClass('-is-primary')).toBe(true);

                        form.trigger($.Event('submit'));
                        expect(myFunc).not.toHaveBeenCalled();

                        dialogView.remove();
                    });

                    it('with explicit action', function() {
                        const myFunc1 = jasmine.createSpy('cb1');
                        const myFunc2 = jasmine.createSpy('cb2')
                            .and.returnValue(false);
                        const dialogView = new DialogView({
                            buttons: [{
                                disabled: false,
                                id: 'testid',
                                label: 'Test',
                                onClick: myFunc1,
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
                        form.on('submit', myFunc2);

                        expect(Object.keys(buttons).length).toBe(1);
                        expect(button.text()).toBe('Test');
                        expect(button.prop('disabled')).toBe(false);
                        expect(button.hasClass('-is-primary')).toBe(true);

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
