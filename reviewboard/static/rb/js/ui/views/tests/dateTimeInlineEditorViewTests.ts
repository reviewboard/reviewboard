import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { DateTimeInlineEditorView } from 'reviewboard/ui';


declare const $testsScratch: JQuery;
declare const dedent: (string) => string;


suite('rb/ui/views/DateTimeInlineEditorView', function() {
    const initialDateTime = '2022-09-16T03:45';
    let view;
    let $container;

    beforeEach(function() {
        $container = $('<div/>').appendTo($testsScratch);
    });

    describe('Construction', function() {
        it('Default', function() {
            view = new DateTimeInlineEditorView({
                el: $container,
            });
            view.render();

            expect(view.$buttons.length).toBe(1);
            expect(view.$field.length).toBe(1);

            const field = view.$field[0];
            expect(field.children.length).toBe(1);
            expect(field.firstElementChild.outerHTML)
                .toBe('<input type="datetime-local">');

        });

        it('With options provided', function() {
            view = new DateTimeInlineEditorView({
                el: $container,
                maxDate: '2030-11-12T:06:30',
                minDate: '2020-10-10T15:20',
                rawValue: initialDateTime,
            });
            view.render();

            expect(view.options.minDate).toBe('2020-10-10T15:20');
            expect(view.options.maxDate).toBe('2030-11-12T:06:30');
            expect(view.options.rawValue).toBe(initialDateTime);

            expect(view.$buttons.length).toBe(1);
            expect(view.$field.length).toBe(1);

            const field = view.$field[0];
            expect(field.firstElementChild.outerHTML).toBe(dedent`
                <input type="datetime-local" max="2030-11-12T:06:30" \
                min="2020-10-10T15:20">
            `);

        });
    });

    describe('Operations', function() {
        afterEach(function() {
            view.hideEditor();
        });

        describe('startEdit', function() {
            it('With an initial date', function() {
                view = new DateTimeInlineEditorView({
                    el: $container,
                    rawValue: initialDateTime,
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.firstChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.value).toBe(initialDateTime);
            });

            it('With no initial date', function() {
                view = new DateTimeInlineEditorView({
                    el: $container,
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.firstChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.value).toBe('');
            });

            it('With a descriptor text', function() {
                view = new DateTimeInlineEditorView({
                    descriptorText: 'Test',
                    el: $container,
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.firstChild.tagName).toBe(undefined);
                expect(field.firstChild.textContent).toBe('Test');
                expect(field.firstElementChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.value).toBe('');
            });

            it('With a descriptor text and initial datetime', function() {
                view = new DateTimeInlineEditorView({
                    descriptorText: 'Test',
                    el: $container,
                    rawValue: initialDateTime,
                });
                view.render();
                view.startEdit();

                const field = view.$field[0];
                expect(field.firstChild.tagName).toBe(undefined);
                expect(field.firstChild.textContent).toBe('Test');
                expect(field.firstElementChild.tagName).toBe('INPUT');
                expect(field.firstElementChild.value).toBe(initialDateTime);
            });
        });

        describe('save', function() {
            it('With a new date', function() {
                view = new DateTimeInlineEditorView({
                    el: $container,
                });
                view.render();
                view.startEdit();

                view.setValue(initialDateTime);
                view.save();

                expect(view.options.rawValue).toBe(initialDateTime);
                expect(view.$el[0].innerHTML).toBe(initialDateTime);
            });

            it('With an empty value', function() {
                view = new DateTimeInlineEditorView({
                    el: $container,
                    rawValue: initialDateTime,
                });
                view.render();
                view.startEdit();

                view.setValue('');
                view.save();

                expect(view.options.rawValue).toBe('');
                expect(view.$el[0].innerHTML).toBe('');
            });

            it('Without any changes made', function() {
                view = new DateTimeInlineEditorView({
                    el: $container,
                    rawValue: initialDateTime,
                });
                view.render();
                view.startEdit();

                view.save();

                expect(view.options.rawValue).toBe(initialDateTime);
                expect(view.$el[0].innerHTML).toBe('');
            });
        });
    });

    describe('Events', function() {
        it('On change', function() {
            view = new DateTimeInlineEditorView({
                el: $container,
            });

            spyOn(view, '_scheduleUpdateDirtyState');

            view.render();
            view.$field.trigger('change');

            expect(view._scheduleUpdateDirtyState)
                .toHaveBeenCalled();
        });
    });
});
