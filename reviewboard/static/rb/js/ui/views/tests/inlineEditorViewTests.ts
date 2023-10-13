import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    fail,
    it,
    spyOn,
} from 'jasmine-core';

import { InlineEditorView } from 'reviewboard/ui';


declare const $testsScratch: JQuery;


suite('rb/ui/views/InlineEditorView', () => {
    let view;
    let $container;

    beforeEach(() => {
        $container = $('<div>').appendTo($testsScratch);
    });

    describe('Construction', () => {
        it('Default', () => {
            view = new InlineEditorView({
                el: $container,
            });
            view.render();

            expect(view.options.showEditIcon).toBe(true);

            expect(view.$buttons.length).toBe(1);
            expect(view.$field.length).toBe(1);
        });

        it('With options', () => {
            view = new InlineEditorView({
                el: $container,
                formClass: 'test-form',
                showEditIcon: false,
            });
            view.render();

            expect(view.options.showEditIcon).toBe(false);

            expect(view.$buttons.length).toBe(1);
            expect(view.$field.length).toBe(1);

            const field = view.$field[0];
            expect(field.form.classList.contains('test-form'))
                .toBe(true);
            expect(field.outerHTML).toBe('<input type="text">');
        });
    });

    describe('Operations', () => {
        afterEach(() => {
            view.hideEditor();
        });

        describe('startEdit', () => {
            it('With an initial value', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'test',
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.tagName).toBe('INPUT');
                expect(field.value).toBe('test');
            });

            it('With no initial value', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.tagName).toBe('INPUT');
                expect(field.value).toBe('');
            });
        });

        describe('save', () => {
            it('With a new value', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                let gotComplete = false;

                view.once('complete', (value, initialValue) => {
                    expect(value).toBe('test');
                    expect(initialValue).toBe('initial');

                    gotComplete = true;
                });
                view.once('cancel', () => {
                    fail();
                });

                view.setValue('test');
                view.save();

                expect(gotComplete).toBe(true);
            });

            it('With an empty value', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                let gotComplete = false;

                view.once('complete', (value, initialValue) => {
                    expect(value).toBe('');
                    expect(initialValue).toBe('initial');

                    gotComplete = true;
                });
                view.once('cancel', () => {
                    fail();
                });

                view.setValue('');
                view.save();

                expect(gotComplete).toBe(true);
            });

            it('Without any changes made', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                let gotCancel = false;

                view.once('complete', () => {
                    fail();
                });
                view.once('cancel', initialValue => {
                    expect(initialValue).toBe('initial');

                    gotCancel = true;
                });

                view.save();

                expect(gotCancel).toBe(true);
            });

            it('With notifyUnchangedCompletion', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    notifyUnchangedCompletion: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                let gotComplete = false;

                view.once('complete', (value, initialValue) => {
                    expect(value).toBe('initial');
                    expect(initialValue).toBe('initial');

                    gotComplete = true;
                });
                view.once('cancel', () => {
                    fail();
                });

                view.save();

                expect(gotComplete).toBe(true);
            });

            it('With preventEvents', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                view.once('complete', () => {
                    fail();
                });

                view.setValue('value');
                const value = view.save({
                    preventEvents: true,
                });

                expect(value).toBe('value');
            });

            it('With preventEvents and no change', () => {
                view = new InlineEditorView({
                    el: $container,
                    hasRawValue: true,
                    rawValue: 'initial',
                });
                view.render();
                view.startEdit();

                view.once('complete', () => {
                    fail();
                });

                const value = view.save({
                    preventEvents: true,
                });

                expect(value).toBe(undefined);
            });
        });
    });

    describe('Events', () => {
        it('On keydown enter', () => {
            view = new InlineEditorView({
                el: $container,
            });

            spyOn(view, 'submit');

            view.render();

            view.$field[0].dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter',
            }));

            expect(view.submit).toHaveBeenCalled();
        });

        it('On keydown enter with multiline', () => {
            view = new InlineEditorView({
                el: $container,
                multiline: true,
            });

            spyOn(view, 'submit');

            view.render();

            view.$field[0].dispatchEvent(new KeyboardEvent('keydown', {
                key: 'Enter',
            }));

            expect(view.submit).not.toHaveBeenCalled();
        });

        it('On keydown ctrl+enter with multiline', () => {
            view = new InlineEditorView({
                el: $container,
                multiline: true,
            });

            spyOn(view, 'submit');

            view.render();

            view.$field[0].dispatchEvent(new KeyboardEvent('keydown', {
                ctrlKey: true,
                key: 'Enter',
            }));

            expect(view.submit).toHaveBeenCalled();
        });

        it('On keyup', () => {
            view = new InlineEditorView({
                el: $container,
            });

            spyOn(view, '_scheduleUpdateDirtyState');

            view.render();

            view.$field[0].dispatchEvent(new KeyboardEvent('keyup', {
                key: 'A',
            }));

            expect(view._scheduleUpdateDirtyState).toHaveBeenCalled();
        });

        it('On cut', () => {
            view = new InlineEditorView({
                el: $container,
            });

            spyOn(view, '_scheduleUpdateDirtyState');

            view.render();

            view.$field[0].dispatchEvent(new ClipboardEvent('cut'));

            expect(view._scheduleUpdateDirtyState).toHaveBeenCalled();
        });

        it('On paste', () => {
            view = new InlineEditorView({
                el: $container,
            });

            spyOn(view, '_scheduleUpdateDirtyState');

            view.render();

            view.$field[0].dispatchEvent(new ClipboardEvent('paste'));

            expect(view._scheduleUpdateDirtyState).toHaveBeenCalled();
        });
    });
});
