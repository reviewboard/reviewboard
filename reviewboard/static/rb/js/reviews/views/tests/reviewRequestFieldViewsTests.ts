import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { ReviewRequest } from 'reviewboard/common';
import {
    ReviewRequestEditor,
    ReviewRequestEditorView,
    ReviewRequestFields,
} from 'reviewboard/reviews';


const {
    BaseFieldView,
    MultilineTextFieldView,
    TextFieldView,
    TrackedBugsFieldView,
    TrackedBugsTableFieldView,
} = ReviewRequestFields;


suite('rb/views/reviewRequestFieldViews', function() {
    let reviewRequest;
    let draft;
    let extraData;
    let rawTextFields;
    let editor;
    let editorView;
    let field;

    beforeEach(function() {
        reviewRequest = new ReviewRequest({
            id: 1,
        });

        draft = reviewRequest.draft;
        extraData = draft.get('extraData');

        rawTextFields = {
            extra_data: {},
        };
        draft.set('rawTextFields', rawTextFields);

        editor = new ReviewRequestEditor({
            reviewRequest: reviewRequest,
        });

        editorView = new ReviewRequestEditorView({
            model: editor,
        });

        spyOn(draft, 'save').and.resolveTo();
        spyOn(draft, 'ready').and.resolveTo();
    });

    describe('BaseFieldView', function() {
        beforeEach(function() {
            field = new BaseFieldView({
                fieldID: 'my_field',
                model: editor,
            });
        });

        describe('Initialization', function() {
            it('Default behavior', function() {
                expect(field.$el.data('field-id')).toBe('my_field');
                expect(field.jsonFieldName).toBe('my_field');
            });

            it('With custom jsonFieldName', function() {
                const field = new BaseFieldView({
                    fieldID: 'my_field',
                    jsonFieldName: 'my_custom_name',
                    model: editor,
                });

                expect(field.$el.data('field-id')).toBe('my_field');
                expect(field.jsonFieldName).toBe('my_custom_name');
            });
        });

        describe('Properties', function() {
            it('fieldName', function() {
                expect(field.fieldName()).toBe('myField');
            });
        });

        describe('Methods', function() {
            describe('_loadValue', function() {
                it('Built-in field', function() {
                    field.useExtraData = false;
                    draft.set('myField', 'this is a test');

                    expect(field._loadValue()).toBe('this is a test');
                });

                it('Custom field', function() {
                    extraData.my_field = 'this is a test';

                    expect(field._loadValue()).toBe('this is a test');
                });

                it('Custom field and custom jsonFieldName', function() {
                    const field = new BaseFieldView({
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    extraData.foo = 'this is a test';

                    expect(field._loadValue()).toBe('this is a test');
                });
            });

            describe('_saveValue', function() {
                it('Built-in field', function(done) {
                    field.useExtraData = false;
                    field._saveValue('test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    my_field: 'test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });

                it('Custom field', function(done) {
                    field._saveValue('this is a test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    'extra_data.my_field': 'this is a test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });

                it('Custom field and custom jsonFieldName', function(done) {
                    const field = new BaseFieldView({
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    field._saveValue('this is a test')
                        .then(() => {
                            expect(draft.save.calls.argsFor(0)[0].data)
                                .toEqual({
                                    'extra_data.foo': 'this is a test',
                                });

                            done();
                        })
                        .catch(err => done.fail(err));
                });
            });
        });
    });

    describe('TextFieldView', function() {
        beforeEach(function() {
            field = new TextFieldView({
                fieldID: 'my_field',
                model: editor,
            });
            editorView.addFieldView(field);
        });

        describe('Properties', function() {
            describe('jsonTextTypeFieldName', function() {
                it('With fieldID != "text"', function() {
                    expect(field.jsonTextTypeFieldName)
                        .toBe('my_field_text_type');
                });

                it('With fieldID = "text"', function() {
                    field = new TextFieldView({
                        fieldID: 'text',
                        model: editor,
                    });

                    expect(field.jsonTextTypeFieldName).toBe('text_type');
                });
            });

            describe('richTextAttr', function() {
                it('With allowRichText=true', function() {
                    field.allowRichText = true;

                    expect(field.richTextAttr()).toBe('myFieldRichText');
                });

                it('With allowRichText=false', function() {
                    field.allowRichText = false;

                    expect(field.richTextAttr()).toBe(null);
                });
            });
        });

        describe('Methods', function() {
            describe('render', function() {
                beforeEach(function() {
                    field.$el.addClass('editable');
                    rawTextFields.extra_data = {
                        my_field: '**Hello world**',
                        my_field_text_type: 'markdown',
                    };
                });

                describe('With allowRichText=true', function() {
                    beforeEach(function() {
                        field.allowRichText = true;
                    });

                    it('With richText=true', function() {
                        rawTextFields.extra_data.my_field_text_type =
                            'markdown';

                        field.render();

                        expect(field.inlineEditorView.textEditor.richText)
                            .toBe(true);
                        expect(field.inlineEditorView.options.rawValue)
                            .toBe('**Hello world**');
                    });

                    it('With richText=false', function() {
                        rawTextFields.extra_data.my_field_text_type = 'plain';

                        field.render();

                        expect(field.inlineEditorView.textEditor.richText)
                            .toBe(false);
                        expect(field.inlineEditorView.options.rawValue)
                            .toBe('**Hello world**');
                    });
                });
            });

            describe('_formatField', function() {
                it('With built-in field', function() {
                    field.useExtraData = false;

                    draft.set('myField', 'Hello world');

                    field._formatField();
                    expect(field.$el.text()).toBe('Hello world');
                });

                it('With custom field', function() {
                    editorView.addFieldView(field);

                    extraData.my_field = 'Hello world';

                    field._formatField();
                    expect(field.$el.text()).toBe('Hello world');
                });

                it('With formatValue as function', function() {
                    field.formatValue = function(value) {
                        this.$el.text(`[${value}]`);
                    };

                    extraData.my_field = 'Hello world';

                    field._formatField();
                    expect(field.$el.text()).toBe('[Hello world]');
                });
            });

            describe('_getInlineEditorClass', function() {
                it('With allowRichText=true', function() {
                    field.allowRichText = true;

                    expect(field._getInlineEditorClass())
                        .toBe(RB.RichTextInlineEditorView);
                });

                it('With allowRichText=false', function() {
                    field.allowRichText = false;

                    expect(field._getInlineEditorClass())
                        .toBe(RB.InlineEditorView);
                });
            });

            describe('_loadRichTextValue', function() {
                beforeEach(function() {
                    field.allowRichText = true;
                });

                describe('With built-in field', function() {
                    beforeEach(function() {
                        field.useExtraData = false;
                    });

                    it('With value=undefined', function() {
                        draft.set('myFieldRichText', undefined);
                        expect(field._loadRichTextValue()).toBe(undefined);
                    });

                    it('With value=false', function() {
                        draft.set('myFieldRichText', false);
                        expect(field._loadRichTextValue()).toBe(false);
                    });

                    it('With value=true', function() {
                        draft.set('myFieldRichText', true);
                        expect(field._loadRichTextValue()).toBe(true);
                    });
                });

                describe('With custom field', function() {
                    it('With textType=undefined', function() {
                        expect(field._loadRichTextValue()).toBe(undefined);
                    });

                    it('With textType=plain', function() {
                        rawTextFields.extra_data.my_field_text_type = 'plain';
                        expect(field._loadRichTextValue()).toBe(false);
                    });

                    it('With textType=markdown', function() {
                        rawTextFields.extra_data.my_field_text_type =
                            'markdown';
                        expect(field._loadRichTextValue()).toBe(true);
                    });

                    it('With textType=invalid value', function() {
                        rawTextFields.extra_data.my_field_text_type = 'html';

                        try {
                            field._loadRichTextValue();
                        } catch (e) {
                            // Do nothing.
                        }

                        expect(console.assert).toHaveBeenCalledWith(
                            false,
                            'Text type "html" in field "my_field_text_type" ' +
                            'not supported.');
                    });
                });
            });
        });
    });

    describe('MultilineTextFieldView', function() {
        describe('Initialization from DOM', function() {
            let $el;

            beforeEach(function() {
                $el = $('<span data-allow-markdown="true">')
                    .text('DOM text value');
            });

            describe('allowRichText', function() {
                it('allow-markdown=true', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(true);
                });

                it('allow-markdown=false', function() {

                    field = new MultilineTextFieldView({
                        el: $el.attr('data-allow-markdown', 'false'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(false);
                });

                it('allow-markdown unset', function() {
                    field = new MultilineTextFieldView({
                        el: $el.removeAttr('data-allow-markdown'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(field.allowRichText).toBe(undefined);
                });
            });

            describe('Text value', function() {
                it('raw-value set', function() {

                    field = new MultilineTextFieldView({
                        el: $el.attr('data-raw-value', 'attr text value'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo).toBe('attr text value');
                    expect($el.attr('data-raw-value')).toBe(undefined);
                });

                it('raw-value unset', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo).toBe('DOM text value');
                });
            });

            describe('Text type value', function() {
                it('rich-text class present', function() {
                    field = new MultilineTextFieldView({
                        el: $el.addClass('rich-text'),
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo_text_type).toBe('markdown');
                });

                it('rich-text class not present', function() {
                    field = new MultilineTextFieldView({
                        el: $el,
                        fieldID: 'my_field',
                        jsonFieldName: 'foo',
                        model: editor,
                    });

                    expect(extraData.foo_text_type).toBe('plain');
                });
            });
        });
    });

    describe('TrackedBugsFieldView', function() {
        function buildField(options={}) {
            const $el = $('<div>')
                .attr('id', 'field_bugs:1')
                .data({
                    'bug-search-url': options.searchURL || '',
                    'bug-tracker-id': 1,
                    'bug-url-template':
                        '/r/1/bug-trackers/1/bugs/--bug_id--/',
                    'can-view-bugs': options.canView !== false ? '1' : '',
                })
                .text(options.text || '');

            if (options.editable) {
                $el.addClass('editable');
            }

            const view = new TrackedBugsFieldView({
                el: $el,
                fieldID: 'bugs:1',
                model: editor,
            });
            view.reviewRequestEditorView = editorView;

            return view;
        }

        afterEach(function() {
            TrackedBugsFieldView.instances.splice(
                0, TrackedBugsFieldView.instances.length);
        });

        describe('Initialization', function() {
            it('Parses state from data attributes', function() {
                field = buildField({
                    text: '12, 34',
                });

                expect(field.bugTrackerID).toBe(1);
                expect(field.canViewBugs).toBeTrue();
                expect(field._loadValue()).toEqual(['12', '34']);
                expect(TrackedBugsFieldView.instances).toContain(field);
            });
        });

        describe('formatValue', function() {
            it('With viewable bugs', function() {
                field = buildField();
                field.formatValue(['12', '34']);

                const $links = field.$el.find('a.bug');
                expect($links.length).toBe(2);
                expect($links.eq(0).attr('href'))
                    .toBe('/r/1/bug-trackers/1/bugs/12/');
                expect($links.eq(0).text()).toBe('12');
            });

            it('Without viewable bugs', function() {
                field = buildField({
                    canView: false,
                });
                field.formatValue(['12', '34']);

                expect(field.$el.find('a').length).toBe(0);
                expect(field.$el.text()).toBe('12, 34');
            });
        });

        describe('Editing', function() {
            beforeEach(function() {
                editor.set('editable', true);
            });

            function sendKey(
                inputEl: HTMLInputElement,
                key: string,
            ) {
                inputEl.dispatchEvent(new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: key,
                }));
            }

            it('Enter tokenizes typed text without saving', function() {
                field = buildField({
                    editable: true,
                    searchURL: '/api/bug-searches/',
                    text: '12',
                });
                field.render();

                spyOn(editor, 'setDraftField').and.resolveTo();

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();

                const comboBox = inlineEditor.comboBox;
                const inputEl = comboBox.textField.inputEl;

                inputEl.value = 'ENG-5';
                sendKey(inputEl, 'Enter');

                expect(comboBox.textField.value).toBe('');
                expect(inlineEditor.getBugsValue()).toBe('12, ENG-5');
                expect(editor.setDraftField).not.toHaveBeenCalled();

                /* A second Enter, with nothing typed, saves. */
                sendKey(inputEl, 'Enter');

                expect(editor.setDraftField).toHaveBeenCalled();
            });

            it('Comma tokenizes typed text', function() {
                field = buildField({
                    editable: true,
                    searchURL: '/api/bug-searches/',
                    text: '12',
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();

                const comboBox = inlineEditor.comboBox;
                const inputEl = comboBox.textField.inputEl;

                inputEl.value = '34';
                sendKey(inputEl, ',');

                expect(comboBox.textField.value).toBe('');
                expect(inlineEditor.getBugsValue()).toBe('12, 34');
            });

            it('Backspace moves the last chip into the field', function() {
                field = buildField({
                    editable: true,
                    searchURL: '/api/bug-searches/',
                    text: '12, 34',
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();

                const comboBox = inlineEditor.comboBox;
                const inputEl = comboBox.textField.inputEl;

                sendKey(inputEl, 'Backspace');

                expect(comboBox.textField.value).toBe('34');
                expect(inlineEditor.getBugsValue()).toBe('12, 34');

                /* The restored text is editable like any typed text. */
                inputEl.value = '345';
                sendKey(inputEl, 'Enter');

                expect(inlineEditor.getBugsValue()).toBe('12, 345');
            });

            it('Reopening the editor clears typed text', function() {
                field = buildField({
                    editable: true,
                    searchURL: '/api/bug-searches/',
                    text: '12, 34',
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                expect(inlineEditor.comboBox).not.toBeNull();

                inlineEditor.startEdit();

                /*
                 * Simulate a bug ID typed but not accepted as a token,
                 * with the suggestions pop-up it would have opened.
                 */
                inlineEditor.comboBox.textField.value = '56';
                inlineEditor.comboBox.open();
                expect(inlineEditor.getBugsValue()).toBe('12, 34, 56');
                expect(inlineEditor.comboBox.isOpen).toBeTrue();

                /* The typed text makes the editor dirty. */
                spyOn(window, 'confirm').and.returnValue(true);

                inlineEditor.cancel();
                inlineEditor.startEdit();

                expect(inlineEditor.comboBox.textField.value).toBe('');
                expect(inlineEditor.comboBox.isOpen).toBeFalse();
                expect(inlineEditor.getBugsValue()).toBe('12, 34');
            });
        });

        describe('_saveValue', function() {
            it('Sorts and de-duplicates the bugs for display', function() {
                field = buildField({
                    text: '12',
                });

                spyOn(editor, 'setDraftField').and.resolveTo();

                field._saveValue('34, 12, 34');
                expect(field._loadValue()).toEqual(['12', '34']);

                /* Non-numeric IDs sort alphabetically. */
                field._saveValue('ENG-5, ENG-12');
                expect(field._loadValue()).toEqual(['ENG-12', 'ENG-5']);
            });

            it('Adopts the saved draft bug ordering', async function() {
                field = buildField({
                    text: '12',
                });

                spyOn(editor, 'setDraftField').and.callFake(async () => {
                    /*
                     * Simulate the response ordering the bugs with the
                     * tracker service's keys, differing from the local
                     * sort.
                     */
                    draft.set('bugs', [
                        {id: 'ENG-5', tracker: 1},
                        {id: 'ENG-12', tracker: 1},
                        {id: '99', tracker: 2},
                    ]);
                });

                await field._saveValue('ENG-12, ENG-5');

                expect(field._loadValue()).toEqual(['ENG-5', 'ENG-12']);
            });

            it('Combines bugs across tracked fields', function() {
                field = buildField({
                    text: '12',
                });

                const $otherEl = $('<div>')
                    .attr('id', 'field_bugs:2')
                    .data('bug-tracker-id', 2)
                    .text('500');
                const otherField = new TrackedBugsFieldView({
                    el: $otherEl,
                    fieldID: 'bugs:2',
                    model: editor,
                });

                spyOn(editor, 'setDraftField').and.resolveTo();

                field._saveValue('12, 34');

                expect(editor.setDraftField).toHaveBeenCalled();
                const args = editor.setDraftField.calls.argsFor(0);
                expect(args[0]).toBe('bugs');
                expect(args[1].split(',').sort()).toEqual(
                    ['1:12', '1:34', '2:500']);
            });
        });
    });

    describe('TrackedBugsTableFieldView', function() {
        /**
         * Return the HTML for a server-rendered table of bugs.
         *
         * Args:
         *     rows (Array of Array of string):
         *         The bug ID, summary, and status for each row.
         *
         *     options (object):
         *         Options for the table.
         *
         * Returns:
         *     string:
         *     The rendered table.
         */
        function buildTableHTML(rows, options={}) {
            const showMetadata = (options.showMetadata !== false);

            /* Bugs are only linked for users who may use the tracker. */
            const linked = (options.linked !== false);

            const rowsHTML = rows.map(([rawBugID, summary, status]) => {
                const bugID = _.escape(rawBugID);

                return `
                <tr class="rb-c-bug-list__bug" data-bug-id="${bugID}">
                 <td class="rb-c-bug-list__id">${linked
                   ? `<a class="bug"
                         href="/r/1/bug-trackers/1/bugs/${bugID}/">${bugID}</a>`
                   : bugID}</td>
                 ${showMetadata ? `
                 <td class="rb-c-bug-list__summary">${summary}</td>
                 <td class="rb-c-bug-list__status">${status}</td>
                 ` : ''}
                </tr>
                `;
            }).join('');

            return `
                <div class="rb-c-review-request-field-tabular rb-c-bug-list">
                 <table class="rb-c-review-request-field-tabular__data">
                  <thead>
                   <tr>
                    <th class="rb-c-bug-list__column-id">Bug</th>
                    ${showMetadata ? `
                    <th class="rb-c-bug-list__column-summary">Summary</th>
                    <th class="rb-c-bug-list__column-status">Status</th>
                    ` : ''}
                   </tr>
                  </thead>
                  <tbody>${rowsHTML}</tbody>
                 </table>
                </div>
            `;
        }

        /**
         * Return a new table field view.
         *
         * Args:
         *     rows (Array of Array of string):
         *         The bug ID, summary, and status for each row.
         *
         *     options (object):
         *         Options for the field.
         *
         * Returns:
         *     RB.ReviewRequestFields.TrackedBugsTableFieldView:
         *     The new field view.
         */
        function buildField(rows, options={}) {
            const $el = $('<div>')
                .attr('id', 'field_bugs:1')
                .data({
                    'bug-info-stale': options.stale ? '1' : '',
                    'bug-info-url': options.bugInfoURL !== null
                                    ? '/r/1/bug-trackers/1/bug-info/'
                                    : '',
                    'bug-tracker-id': 1,
                    'bug-url-template':
                        '/r/1/bug-trackers/1/bugs/--bug_id--/',
                    'can-view-bugs': '1',
                    'supports-bug-search': options.editable ? '1' : '',
                })
                .html(buildTableHTML(rows, options));

            if (options.editable) {
                $el.addClass('editable');
            }

            const view = new TrackedBugsTableFieldView({
                el: $el,
                fieldID: 'bugs:1',
                model: editor,
            });
            view.reviewRequestEditorView = editorView;

            return view;
        }

        beforeEach(function() {
            /* Keep the tests from reaching the metadata endpoint. */
            spyOn(window, 'fetch').and.resolveTo(
                new Response('{"bugs": {}}'));
        });

        afterEach(function() {
            TrackedBugsFieldView.instances.splice(
                0, TrackedBugsFieldView.instances.length);
        });

        describe('Initialization', function() {
            it('Loads bug IDs from the table', function() {
                field = buildField([
                    ['12', 'A crash', 'open'],
                    ['34', '', ''],
                ]);

                expect(field._loadValue()).toEqual(['12', '34']);
                expect(TrackedBugsFieldView.instances).toContain(field);
            });
        });

        describe('formatValue', function() {
            it('Renders a table of bugs', function() {
                field = buildField([
                    ['12', 'A crash', 'open'],
                ]);
                field.formatValue(['12', '34']);

                const $rows = field.$el.find('.rb-c-bug-list__bug');
                expect($rows.length).toBe(2);

                expect($rows.eq(0).find('a.bug').attr('href'))
                    .toBe('/r/1/bug-trackers/1/bugs/12/');

                /* The metadata from the server-rendered table is kept. */
                expect($rows.eq(0).find('.rb-c-bug-list__summary').text())
                    .toBe('A crash');
                expect($rows.eq(0).find('.rb-c-bug-list__status').text())
                    .toBe('open');

                expect($rows.eq(1).attr('data-bug-id')).toBe('34');
                expect($rows.eq(1).find('.rb-c-bug-list__summary').text())
                    .toBe('');
            });

            it('With no bugs', function() {
                field = buildField([]);
                field.formatValue([]);

                expect(field.$el.find('.rb-c-bug-list__bug').length).toBe(0);
                expect(field.$el.find('.rb-c-bug-list__empty').length).toBe(1);
            });

            it('Without metadata support', function() {
                field = buildField([['12', '', '']], {
                    bugInfoURL: null,
                    showMetadata: false,
                });
                field.formatValue(['12']);

                expect(field.$el.find('.rb-c-bug-list__summary').length)
                    .toBe(0);
                expect(field.$el.find('.rb-c-bug-list__bug').length).toBe(1);
            });
        });

        describe('Fetching metadata', function() {
            it('When stale', async function() {
                /*
                 * A plain object stands in for the response, so that
                 * reading its body only takes promise callbacks.
                 */
                (window.fetch as jasmine.Spy).and.resolveTo({
                    json: () => Promise.resolve({
                        bugs: {
                            12: {
                                status: 'open',
                                summary: 'A crash',
                            },
                        },
                    }),
                    ok: true,
                });

                field = buildField([['12', '', '']], {
                    stale: true,
                });
                field.render();

                /*
                 * The metadata is fetched and shown asynchronously. All
                 * pending promise callbacks run before this timeout.
                 */
                await new Promise(resolve => setTimeout(resolve, 0));

                expect(window.fetch).toHaveBeenCalled();
                expect(field.$el.find('.rb-c-bug-list__summary').text())
                    .toBe('A crash');
            });

            it('When fresh', function() {
                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                expect(window.fetch).not.toHaveBeenCalled();
            });
        });

        describe('Row clicks', function() {
            it('Opens the bug', function() {
                spyOn(RB, 'navigateTo');

                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                field.$el
                    .find('.rb-c-bug-list__bug')
                    .trigger($.Event('click', {
                        button: 0,
                    }));

                expect(RB.navigateTo).toHaveBeenCalledWith(
                    '/r/1/bug-trackers/1/bugs/12/');
            });

            it('Without a link', function() {
                spyOn(RB, 'navigateTo');

                /* Users failing the tracker's conditions get bare IDs. */
                field = buildField([['12', '', '']], {
                    bugInfoURL: null,
                    linked: false,
                    showMetadata: false,
                });
                field.render();

                field.$el
                    .find('.rb-c-bug-list__bug')
                    .trigger($.Event('click', {
                        button: 0,
                    }));

                expect(RB.navigateTo).not.toHaveBeenCalled();
            });

            it('With modifier keys', function() {
                spyOn(RB, 'navigateTo');

                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                const $row = field.$el.find('.rb-c-bug-list__bug');

                /* These are left to the browser, such as to open a tab. */
                for (const key of ['altKey', 'ctrlKey', 'metaKey',
                                   'shiftKey']) {
                    $row.trigger($.Event('click', {
                        [key]: true,
                        button: 0,
                    }));
                }

                expect(RB.navigateTo).not.toHaveBeenCalled();
            });

            it('With a button other than the primary', function() {
                spyOn(RB, 'navigateTo');

                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                field.$el
                    .find('.rb-c-bug-list__bug')
                    .trigger($.Event('click', {
                        button: 1,
                    }));

                expect(RB.navigateTo).not.toHaveBeenCalled();
            });

            it('On the link', function() {
                spyOn(RB, 'navigateTo');

                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                /*
                 * The link opens the bug itself. jQuery doesn't follow
                 * links when triggering clicks on them.
                 */
                field.$el
                    .find('a.bug')
                    .trigger($.Event('click', {
                        button: 0,
                    }));

                expect(RB.navigateTo).not.toHaveBeenCalled();
            });

            it('When ending a text selection', function() {
                spyOn(RB, 'navigateTo');
                spyOn(window, 'getSelection').and.returnValue({
                    toString: () => 'A crash',
                } as Selection);

                field = buildField([['12', 'A crash', 'open']]);
                field.render();

                field.$el
                    .find('.rb-c-bug-list__bug')
                    .trigger($.Event('click', {
                        button: 0,
                    }));

                expect(RB.navigateTo).not.toHaveBeenCalled();
            });
        });

        describe('Editing', function() {
            beforeEach(function() {
                editor.set('editable', true);
            });

            it('Shows the edit icon next to the field label', function() {
                /*
                 * The icon is placed by looking the label up in the
                 * document, so it has to be attached.
                 */
                const $label = $('<label for="field_bugs:1">')
                    .appendTo(document.body);

                try {
                    field = buildField([['12', 'A crash', 'open']], {
                        editable: true,
                    });
                    field.render();

                    expect($label.find('.rb-c-inline-editor-edit-icon')
                           .length)
                        .toBe(1);
                } finally {
                    $label.remove();
                }
            });

            it('Focuses the search field', function() {
                field = buildField([['12', 'A crash', 'open']], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                spyOn(inlineEditor.comboBox, 'focus');

                inlineEditor.startEdit();

                expect(inlineEditor.comboBox.focus).toHaveBeenCalled();
            });

            it('Renders the current bugs as rows', function() {
                field = buildField([
                    ['12', 'A crash', 'open'],
                    ['34', '', ''],
                ], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                expect(inlineEditor.comboBox).not.toBeNull();

                inlineEditor.startEdit();

                /* The value comes from the table, not the element's text. */
                expect(inlineEditor.getBugsValue()).toBe('12, 34');

                const $rows = $(inlineEditor.$field)
                    .find('.rb-c-bug-list__bug');
                expect($rows.length).toBe(2);
                expect($rows.eq(0).attr('data-bug-id')).toBe('12');

                /* Summaries come from the rendered table. */
                expect($rows.eq(0).find('.rb-c-bug-list__summary').text())
                    .toBe('A crash');
                expect($rows.eq(1).find('.rb-c-bug-list__summary').text())
                    .toBe('');
            });

            it('Removes bugs', function() {
                field = buildField([
                    ['12', 'A crash', 'open'],
                    ['34', '', ''],
                ], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();

                $(inlineEditor.$field)
                    .find('.rb-c-bug-list__bug[data-bug-id="34"] ' +
                          '.rb-c-bug-list__remove')
                    .click();

                expect(inlineEditor.getBugsValue()).toBe('12');
                expect($(inlineEditor.$field)
                       .find('.rb-c-bug-list__bug').length)
                    .toBe(1);
            });

            it('With quotes in bug IDs', function() {
                field = buildField([
                    ['ABC-"1"', 'A crash', 'open'],
                ], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();

                const $rows = $(inlineEditor.$field)
                    .find('.rb-c-bug-list__bug');
                expect($rows.length).toBe(1);
                expect($rows.attr('data-bug-id')).toBe('ABC-"1"');
                expect($rows.find('.rb-c-bug-list__summary').text())
                    .toBe('A crash');
            });

            it('Adds typed bug IDs', function() {
                field = buildField([['12', 'A crash', 'open']], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                spyOn(inlineEditor, 'submit');
                inlineEditor.startEdit();

                const input = inlineEditor.comboBox.textField.$el
                    .find('input')[0] as HTMLInputElement;
                input.value = '34';
                input.dispatchEvent(new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                }));

                /*
                 * The typed ID becomes a row, without a summary. Editing
                 * continues.
                 */
                expect(inlineEditor.submit).not.toHaveBeenCalled();
                expect(input.value).toBe('');
                expect(inlineEditor.getBugsValue()).toBe('12, 34');

                const $row = $(inlineEditor.$field)
                    .find('.rb-c-bug-list__bug[data-bug-id="34"]');
                expect($row.length).toBe(1);
                expect($row.find('.rb-c-bug-list__summary').text()).toBe('');
            });

            it('Shows the table while saving', function() {
                field = buildField([['12', 'A crash', 'open']], {
                    editable: true,
                });
                field.render();

                /* The save never finishes, to look at the field meanwhile. */
                spyOn(editor, 'setDraftField').and.returnValue(
                    new Promise(() => {}));

                const inlineEditor = field.inlineEditorView;
                inlineEditor.startEdit();
                inlineEditor.comboBox.selectedItems.add({
                    id: '34',
                    label: '34',
                });
                inlineEditor.submit();

                expect(editor.setDraftField).toHaveBeenCalled();

                const $rows = field.$el.find('.rb-c-bug-list__bug');
                expect($rows.length).toBe(2);
                expect($rows.eq(0).find('.rb-c-bug-list__summary').text())
                    .toBe('A crash');
                expect($rows.eq(1).attr('data-bug-id')).toBe('34');
            });

            it('Saves on Enter with nothing typed', function() {
                field = buildField([['12', 'A crash', 'open']], {
                    editable: true,
                });
                field.render();

                const inlineEditor = field.inlineEditorView;
                spyOn(inlineEditor, 'submit');
                inlineEditor.startEdit();

                const input = inlineEditor.comboBox.textField.$el
                    .find('input')[0];
                const evt = new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                });
                input.dispatchEvent(evt);

                /* The browser must not submit the editor's form. */
                expect(evt.defaultPrevented).toBeTrue();
                expect(inlineEditor.submit).toHaveBeenCalledTimes(1);
            });

            describe('Without search support', function() {
                beforeEach(function() {
                    field = buildField([['12', 'A crash', 'open']], {
                        editable: true,
                    });
                    field.$el.data('supports-bug-search', '');
                    field.render();
                });

                it('Saves on Enter', function() {
                    const inlineEditor = field.inlineEditorView;
                    expect(inlineEditor.comboBox).toBeNull();

                    spyOn(inlineEditor, 'submit');
                    inlineEditor.startEdit();

                    const evt = new KeyboardEvent('keydown', {
                        cancelable: true,
                        key: 'Enter',
                    });
                    inlineEditor.$field[0].dispatchEvent(evt);

                    /* The browser must not submit the editor's form. */
                    expect(evt.defaultPrevented).toBeTrue();
                    expect(inlineEditor.submit).toHaveBeenCalledTimes(1);
                });

                it('Saves once on Ctrl+Enter', function() {
                    const inlineEditor = field.inlineEditorView;

                    spyOn(inlineEditor, 'submit');
                    inlineEditor.startEdit();

                    const evt = new KeyboardEvent('keydown', {
                        cancelable: true,
                        ctrlKey: true,
                        key: 'Enter',
                    });
                    inlineEditor.$field[0].dispatchEvent(evt);

                    expect(evt.defaultPrevented).toBeTrue();
                    expect(inlineEditor.submit).toHaveBeenCalledTimes(1);
                });
            });
        });

        describe('_saveValue', function() {
            it('Combines bugs across tracked fields', function() {
                field = buildField([['12', 'A crash', 'open']]);

                const $otherEl = $('<div>')
                    .attr('id', 'field_bugs:2')
                    .data('bug-tracker-id', 2)
                    .text('500');
                const otherField = new TrackedBugsFieldView({
                    el: $otherEl,
                    fieldID: 'bugs:2',
                    model: editor,
                });

                spyOn(editor, 'setDraftField').and.resolveTo();

                field._saveValue('12, 34');

                const args = editor.setDraftField.calls.argsFor(0);
                expect(args[0]).toBe('bugs');
                expect(args[1].split(',').sort()).toEqual(
                    ['1:12', '1:34', '2:500']);
            });
        });
    });
});
