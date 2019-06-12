suite('rb/views/ReviewRequestEditorView', function() {
    const template = dedent`
        <div>
         <div id="review-request-banners"></div>
         <div id="review-request-warning"></div>
         <div class="actions">
          <a href="#" id="discard-review-request-action"></a>
          <a href="#" id="submit-review-request-action"></a>
          <a href="#" id="delete-review-request-action"></a>
         </div>
         <div class="review-request">
          <div id="review-request-main">
           <span id="field_summary"
                 data-field-id="summary"
                 class="field editable"></span>
           <span id="field_branch"
                 data-field-id="branch"
                 class="field editable"></span>
           <span id="field_submitter"
                 data-field-id="submitter"
                 class="field editable"></span>
           <span id="field_bugs_closed"
                 data-field-id="bugs_closed"
                 class="field editable comma-editable"></span>
           <span id="field_depends_on"
                 data-field-id="depends_on"
                 class="field editable comma-editable"></span>
           <span id="field_target_groups"
                 data-field-id="target_groups"
                 class="field editable comma-editable"></span>
           <span id="field_target_people"
                 data-field-id="target_people"
                 class="field editable"></span>
           <div class="review-request-section">
            <pre id="field_description"
                 data-field-id="description"
                 class="field field-text-area editable"></pre>
           </div>
           <div class="review-request-section">
            <pre id="field_testing_done"
                 data-field-id="testing_done"
                 class="field field-text-area editable"></pre>
           </div>
           <div class="review-request-section">
            <div class="field-container">
             <pre id="field_my_custom"
                  data-field-id="my_custom"
                  class="field editable"></pre>
             <pre id="field_my_rich_text_custom"
                  data-field-id="my_rich_text_custom"
                  class="field field-text-area editable rich-text"
                  data-allow-markdown="True"></pre>
             <pre id="field_text"
                  data-field-id="text"
                  class="field field-text-area editable"
                  data-allow-markdown="True"></pre>
             <input id="field_checkbox"
                    data-field-id="checkbox"
                    class="field"
                    type="checkbox">
            </div>
           </div>
          </div>
         </div>
         <div id="review-request-extra">
          <div>
           <div id="file-list"><br /></div>
          </div>
          <div>
           <div id="screenshot-thumbnails"><br /></div>
          </div>
         </div>
        </div>
    `;
    const screenshotThumbnailTemplate = _.template(dedent`
        <div class="screenshot-container" data-screenshot-id="<%= id %>">
         <div class="screenshot-caption">
          <a class="edit"></a>
         </div>
         <a class="delete">X</a>
        '</div>
    `);
    let reviewRequest;
    let editor;
    let view;
    let $filesContainer;
    let $screenshotsContainer;

    beforeEach(function() {
        RB.DnDUploader.create();

        reviewRequest = new RB.ReviewRequest({
            id: 123,
            'public': true,
            state: RB.ReviewRequest.PENDING,
        });

        editor = new RB.ReviewRequestEditor({
            mutableByUser: true,
            statusMutableByUser: true,
            reviewRequest: reviewRequest,
            commentIssueManager: new RB.CommentIssueManager(),
        });

        const $el = $(template).appendTo($testsScratch);

        view = new RB.ReviewRequestEditorView({
            el: $el,
            model: editor,
        });

        view.addFieldView(
            new RB.ReviewRequestFields.SummaryFieldView({
                el: $el.find('#field_summary'),
                fieldID: 'summary',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.BranchFieldView({
                el: $el.find('#field_branch'),
                fieldID: 'branch',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.OwnerFieldView({
                el: $el.find('#field_submitter'),
                fieldID: 'submitter',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.BugsFieldView({
                el: $el.find('#field_bugs_closed'),
                fieldID: 'bugs_closed',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.DependsOnFieldView({
                el: $el.find('#field_depends_on'),
                fieldID: 'depends_on',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.TargetGroupsFieldView({
                el: $el.find('#field_target_groups'),
                fieldID: 'target_groups',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.TargetPeopleFieldView({
                el: $el.find('#field_target_people'),
                fieldID: 'target_people',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.DescriptionFieldView({
                el: $el.find('#field_description'),
                fieldID: 'description',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.TestingDoneFieldView({
                el: $el.find('#field_testing_done'),
                fieldID: 'testing_done',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.TextFieldView({
                el: $el.find('#field_my_custom'),
                fieldID: 'my_custom',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.MultilineTextFieldView({
                el: $el.find('#field_my_rich_text_custom'),
                fieldID: 'my_rich_text_custom',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.MultilineTextFieldView({
                el: $el.find('#field_text'),
                fieldID: 'text',
                model: editor,
            }));

        view.addFieldView(
            new RB.ReviewRequestFields.CheckboxFieldView({
                el: $el.find('#field_checkbox'),
                fieldID: 'checkbox',
                model: editor,
            }));

        $filesContainer = $testsScratch.find('#file-list');
        $screenshotsContainer = $testsScratch.find('#screenshot-thumbnails');

        /*
         * XXX Prevent _refreshPage from being called. Eventually, that
         *     function will go away.
         */
        spyOn(view, '_refreshPage');

        spyOn(reviewRequest.draft, 'ready').and.callFake(
            (options, context) => options.ready.call(context));
    });

    afterEach(function() {
        RB.DnDUploader.instance = null;
    });

    describe('Actions bar', function() {
        describe('Close', function() {
            beforeEach(function() {
                view.render();
            });

            it('Delete Permanently', function() {
                let $buttons = $();

                spyOn(reviewRequest, 'destroy');
                spyOn($.fn, 'modalBox').and.callFake(options => {
                    options.buttons.forEach($btn => {
                        $buttons = $buttons.add($btn);
                    });

                    /* Simulate the modalBox API for what we need. */
                    return {
                        modalBox: cmd => {
                            expect(cmd).toBe('buttons');
                            return $buttons;
                        }
                    };
                });

                $('#delete-review-request-action').click();
                expect($.fn.modalBox).toHaveBeenCalled();

                $buttons.filter('input[value="Delete"]').click();
                expect(reviewRequest.destroy).toHaveBeenCalled();
            });

            it('Discarded', function() {
                spyOn(reviewRequest, 'close').and.callFake(options => {
                    expect(options.type).toBe(RB.ReviewRequest.CLOSE_DISCARDED);
                });

                spyOn(window, 'confirm').and.returnValue(true);

                $('#discard-review-request-action').click();

                expect(reviewRequest.close).toHaveBeenCalled();
            });

            it('Submitted', function() {
                spyOn(reviewRequest, 'close').and.callFake(options => {
                    expect(options.type).toBe(RB.ReviewRequest.CLOSE_SUBMITTED);
                });

                $('#submit-review-request-action').click();

                expect(reviewRequest.close).toHaveBeenCalled();
            });
        });

        it('ReviewRequestActionHooks', function() {
            var MyExtension,
                extension,
                $action;

            MyExtension = RB.Extension.extend({
                initialize: function() {
                    RB.Extension.prototype.initialize.call(this);

                    new RB.ReviewRequestActionHook({
                        extension: this,
                        callbacks: {
                            '#my-action': _.bind(function() {
                                this.actionClicked = true;
                            }, this)
                        }
                    });
                }
            });

            extension = new MyExtension();

            /*
             * Actions are rendered server-side, not client-side, so we won't
             * get the action added through the hook above.
             */
            $action = $('<a href="#" id="my-action" />')
                .appendTo(view.$('.actions'));

            view.render();

            $action.click();
            expect(extension.actionClicked).toBe(true);
        });
    });

    describe('Banners', function() {
        beforeEach(function() {
            view.render();
        });

        describe('Draft banner', function() {
            describe('Visibility', function() {
                it('Hidden when saving', function() {
                    expect(view.banner).toBe(null);
                    editor.trigger('saving');
                    expect(view.banner).toBe(null);
                });

                it('Show when saved', function() {
                    const summaryField = view.getFieldView('summary');
                    const summaryEditor = summaryField.inlineEditorView;

                    expect(view.banner).toBe(null);

                    spyOn(reviewRequest.draft, 'ensureCreated').and.callFake(
                        (options, context) => options.success.call(context));
                    spyOn(reviewRequest.draft, 'save').and.callFake(
                        (options, context) => options.success.call(context));

                    summaryEditor.startEdit();
                    summaryEditor.setValue('New summary');
                    summaryEditor.save();

                    expect(view.banner).not.toBe(null);
                    expect(view.banner.$el.is(':visible')).toBe(true);
                });
            });

            describe('Buttons actions', function() {
                beforeEach(function() {
                    reviewRequest.set({
                        links: {
                            submitter: {
                                title: 'submitter',
                            },
                        },
                    });
                });
                it('Discard Draft', function() {
                    view.model.set('hasDraft', true);
                    view.showBanner();

                    spyOn(reviewRequest.draft, 'destroy');

                    $('#btn-draft-discard').click();

                    expect(reviewRequest.draft.destroy).toHaveBeenCalled();
                });

                it('Discard Review Request', function() {
                    reviewRequest.set('public', false);
                    view.model.set('hasDraft', true);
                    view.showBanner();

                    spyOn(reviewRequest, 'close').and.callFake(
                        options => expect(options.type).toBe(
                            RB.ReviewRequest.CLOSE_DISCARDED));

                    $('#btn-review-request-discard').click();

                    expect(reviewRequest.close).toHaveBeenCalled();
                });

                describe('Publish', function() {
                    beforeEach(function() {
                        view.model.set('hasDraft', true);

                        spyOn(editor, 'publishDraft').and.callThrough();
                        spyOn(reviewRequest.draft, 'ensureCreated')
                            .and.callFake(
                                (options, context) => options.success.call(context));
                        spyOn(reviewRequest.draft, 'publish');

                        /* Set up some basic state so that we pass validation. */
                        reviewRequest.draft.set({
                            targetGroups: [{
                                name: 'foo',
                                url: '/groups/foo',
                            }],
                            summary: 'foo',
                            links: {
                                submitter: {
                                    title: 'submitter',
                                },
                            },
                            description: 'foo',
                        });
                    });

                    it('Basic publishing', function() {
                        view.showBanner();

                        $('#btn-draft-publish').click();

                        expect(editor.get('publishing')).toBe(true);
                        expect(editor.get('pendingSaveCount')).toBe(0);
                        expect(editor.publishDraft).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish).toHaveBeenCalled();
                    });

                    it('With submitter changed', function() {
                        reviewRequest.draft.set({
                            links: {
                                submitter: {
                                    title: 'submitter2',
                                },
                            },
                        });
                        view.showBanner();

                        spyOn(window, 'confirm').and.returnValue(true);

                        $('#btn-draft-publish').click();

                        expect(editor.get('publishing')).toBe(true);
                        expect(editor.get('pendingSaveCount')).toBe(0);
                        expect(editor.publishDraft).toHaveBeenCalled();
                        expect(window.confirm).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish).toHaveBeenCalled();
                    });

                    it('With Send E-Mail turned on', function() {
                        view.model.set('showSendEmail', true);
                        view.showBanner();

                        $('#btn-draft-publish').click();

                        expect(editor.get('publishing')).toBe(true);
                        expect(editor.get('pendingSaveCount')).toBe(0);
                        expect(editor.publishDraft).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish.calls
                               .argsFor(0)[0].trivial).toBe(0);
                    });

                    it('With Send E-Mail turned off', function() {
                        view.model.set('showSendEmail', true);
                        view.showBanner();

                        $('.send-email').prop('checked', false);
                        $('#btn-draft-publish').click();

                        expect(editor.get('publishing')).toBe(true);
                        expect(editor.get('pendingSaveCount')).toBe(0);
                        expect(editor.publishDraft).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish).toHaveBeenCalled();
                        expect(reviewRequest.draft.publish.calls
                               .argsFor(0)[0].trivial).toBe(1);
                    });
                });
            });

            describe('Button states', function() {
                let $buttons;

                beforeEach(function() {
                    view.model.set('hasDraft', true);
                    view.showBanner();

                    $buttons = view.banner.$buttons;
                });

                it('Enabled by default', function() {
                    expect($buttons.prop('disabled')).toBe(false);
                });

                it('Disabled when saving', function() {
                    expect($buttons.prop('disabled')).toBe(false);
                    editor.trigger('saving');
                    expect($buttons.prop('disabled')).toBe(true);
                });

                it('Enabled when saved', function() {
                    expect($buttons.prop('disabled')).toBe(false);
                    editor.trigger('saving');
                    expect($buttons.prop('disabled')).toBe(true);
                    editor.trigger('saved');
                    expect($buttons.prop('disabled')).toBe(false);
                });
            });
        });

        describe('Discarded banner', function() {
            beforeEach(function() {
                reviewRequest.set('state', RB.ReviewRequest.CLOSE_DISCARDED);
            });

            it('Visibility', function() {
                expect(view.banner).toBe(null);

                view.showBanner();

                expect(view.banner).not.toBe(null);
                expect(view.banner.el.id).toBe('discard-banner');
                expect(view.banner.$el.is(':visible')).toBe(true);
            });

            describe('Buttons actions', function() {
                beforeEach(function() {
                    expect(view.banner).toBe(null);
                    view.showBanner();
                });

                it('Reopen', function() {
                    spyOn(reviewRequest, 'reopen');

                    $('#btn-review-request-reopen').click();

                    expect(reviewRequest.reopen).toHaveBeenCalled();
                });
            });

            describe('Close description', function() {
                let fieldEditor;
                let $input;

                beforeEach(function() {
                    view.showBanner();
                    fieldEditor = view.banner.field.inlineEditorView;
                    $input = fieldEditor.$field;
                });

                function testCloseDescription(testName, richText) {
                    it(testName, function(done) {
                        fieldEditor.startEdit();
                        const textEditor = fieldEditor.textEditor;
                        textEditor.setText('My description');
                        textEditor.setRichText(richText);

                        $input.triggerHandler('keyup');

                        const t = setInterval(() => {
                            if (fieldEditor.isDirty()) {
                                clearInterval(t);

                                spyOn(reviewRequest, 'close')
                                    .and.callFake(options => {
                                        expect(options.type)
                                            .toBe(RB.ReviewRequest.CLOSE_DISCARDED);
                                        expect(options.description)
                                            .toBe('My description');
                                        expect(options.richText).toBe(richText);
                                    });

                                fieldEditor.submit();
                                expect(reviewRequest.close).toHaveBeenCalled();

                                done();
                            }
                        }, 100);
                    });
                }

                describe('Saves', function() {
                    testCloseDescription('For Markdown', true);
                    testCloseDescription('For plain text', false);
                });
            });
        });

        describe('Submitted banner', function() {
            beforeEach(function() {
                reviewRequest.set('state', RB.ReviewRequest.CLOSE_SUBMITTED);
            });

            it('Visibility', function() {
                expect(view.banner).toBe(null);

                view.showBanner();

                expect(view.banner).not.toBe(null);
                expect(view.banner.el.id).toBe('submitted-banner');
                expect(view.banner.$el.is(':visible')).toBe(true);
            });

            describe('Buttons actions', function() {
                beforeEach(function() {
                    expect(view.banner).toBe(null);
                    reviewRequest.set('state', RB.ReviewRequest.CLOSE_SUBMITTED);
                    view.showBanner();
                });

                it('Reopen', function() {
                    spyOn(reviewRequest, 'reopen');

                    $('#btn-review-request-reopen').click();

                    expect(reviewRequest.reopen).toHaveBeenCalled();
                });
            });

            describe('Close description', function() {
                let fieldEditor;
                let $input;

                beforeEach(function() {
                    view.showBanner();
                    fieldEditor = view.banner.field.inlineEditorView;
                    $input = fieldEditor.$field;
                });

                function testCloseDescription(testName, richText) {
                    it(testName, function(done) {
                        fieldEditor.startEdit();
                        const textEditor = fieldEditor.textEditor;
                        textEditor.setText('My description');
                        textEditor.setRichText(richText);

                        $input.triggerHandler('keyup');

                        const t = setInterval(function() {
                            if (fieldEditor.isDirty()) {
                                clearInterval(t);

                                spyOn(reviewRequest, 'close')
                                    .and.callFake(options => {
                                        expect(options.type)
                                            .toBe(RB.ReviewRequest.CLOSE_SUBMITTED);
                                        expect(options.description)
                                            .toBe('My description');
                                        expect(options.richText).toBe(richText);
                                    });

                                fieldEditor.submit();
                                expect(reviewRequest.close).toHaveBeenCalled();

                                done();
                            }
                        }, 100);
                    });
                }

                describe('Saves', function() {
                    testCloseDescription('For Markdown', true);
                    testCloseDescription('For plain text', false);
                });
            });
        });
    });

    describe('Fields', function() {
        let saveSpyFunc;
        let fieldName;
        let jsonFieldName;
        let jsonTextTypeFieldName;
        let supportsRichText;
        let useExtraData;
        let fieldView;
        let fieldEditor;
        let $field;
        let $input;

        beforeEach(function() {
            if (!saveSpyFunc) {
                saveSpyFunc = (options, context) => {
                    expect(options.data[jsonFieldName]).toBe('My Value');
                    options.success.call(context);
                };
            }

            spyOn(reviewRequest.draft, 'save').and.callFake(saveSpyFunc);

            view.render();
        });

        function setupFieldTests(options) {
            beforeEach(function() {
                fieldName = options.fieldName;
                jsonFieldName = options.jsonFieldName;
                jsonTextTypeFieldName = (jsonFieldName === 'text'
                                         ? 'text_type'
                                         : jsonFieldName + '_text_type');
                supportsRichText = !!options.supportsRichText;
                useExtraData = options.useExtraData;
                fieldView = view.getFieldView(options.fieldID || options.jsonFieldName);
                fieldEditor = fieldView.inlineEditorView;
                $field = view.$(options.selector);
                $input = fieldEditor.$field;
            });
        }

        function hasAutoCompleteTest() {
            it('Has auto-complete', function() {
                expect($input.data('uiRbautocomplete')).not.toBe(undefined);
            });
        }

        function hasEditorTest() {
            it('Has editor', function() {
                expect(fieldEditor).not.toBe(undefined);
            });
        }

        function runSavingTest(richText, textType, supportsRichTextEV) {
            beforeEach(function(done) {
                expect(supportsRichText).toBe(supportsRichTextEV);

                fieldEditor.startEdit();

                if (supportsRichText) {
                    expect($field.hasClass('field-text-area')).toBe(true);

                    const textEditor = fieldEditor.textEditor;
                    textEditor.setText('My Value');
                    textEditor.setRichText(richText);
                } else {
                    $input.val('My Value');
                }

                $input.triggerHandler('keyup');
                expect(fieldEditor.getValue()).toBe('My Value');

                const t = setInterval(() => {
                    if (fieldEditor.isDirty()) {
                        clearInterval(t);
                        done();
                    }
                }, 100);
            });

            it('', function() {
                const expectedData = {};
                const fieldPrefix = (useExtraData ? 'extra_data.' : '');

                expectedData[fieldPrefix + jsonFieldName] = 'My Value';

                if (supportsRichText) {
                    expectedData[fieldPrefix + jsonTextTypeFieldName] =
                        textType;

                    expectedData.force_text_type = 'html';
                    expectedData.include_text_types = 'raw';
                }

                expect(fieldEditor.isDirty()).toBe(true);
                fieldEditor.submit();

                expect(reviewRequest.draft.save).toHaveBeenCalled();
                expect(reviewRequest.draft.save.calls.argsFor(0)[0].data)
                    .toEqual(expectedData);
            });
        }

        function savingTest() {
            describe('Saves', function() {
                runSavingTest(undefined, undefined, false);
            });
        }

        function richTextSavingTest() {
            describe('Saves', function() {
                describe('For Markdown', function() {
                    runSavingTest(true, 'markdown', true);
                });

                describe('For plain text', function() {
                    runSavingTest(false, 'plain', true);
                });
            });
        }

        function inlineEditorResizeTests() {
            it('Propagates resizes', function() {
                spyOn(fieldView, 'trigger').and.callThrough();

                fieldView.inlineEditorView.textEditor.$el.triggerHandler(
                    'resize');

                expect(fieldView.trigger).toHaveBeenCalledWith('resize');
            });
        }

        function editCountTests() {
            describe('Edit counts', function() {
                it('When opened', function() {
                    expect(editor.get('editCount')).toBe(0);
                    fieldEditor.startEdit();
                    expect(editor.get('editCount')).toBe(1);
                });

                it('When canceled', function() {
                    fieldEditor.startEdit();
                    fieldEditor.cancel();
                    expect(editor.get('editCount')).toBe(0);
                });

                it('When submitted', function() {
                    fieldEditor.startEdit();
                    $input
                        .val('My Value')
                        .triggerHandler('keyup');
                    fieldEditor.submit();

                    expect(editor.get('editCount')).toBe(0);
                });
            });
        }

        function securityTests(options={}) {
            if (options.supportsRichText) {
                describe('Security measures', function() {
                    it('No self-XSS when draft field changes', function() {
                        let fieldOwner;

                        delete window.rbTestFoundXSS;

                        if (options.fieldOnReviewRequest) {
                            fieldOwner = reviewRequest;
                        } else {
                            fieldOwner = reviewRequest.draft;
                        }

                        fieldOwner.set(
                            fieldName,
                            '"><script>window.rbTestFoundXSS = true;</script>');
                        fieldOwner.trigger('change:' + fieldName);
                        fieldOwner.trigger('fieldChange:' + fieldName);

                        expect(window.rbTestFoundXSS).toBe(undefined);
                    });
                });
            }
        }

        describe('Branch', function() {
            setupFieldTests({
                fieldName: 'branch',
                jsonFieldName: 'branch',
                selector: '#field_branch',
            });

            hasEditorTest();
            savingTest();
            editCountTests();
            securityTests();
        });

        describe('Bugs Closed', function() {
            setupFieldTests({
                fieldName: 'bugsClosed',
                jsonFieldName: 'bugs_closed',
                selector: '#field_bugs_closed',
            });

            hasEditorTest();
            savingTest();

            describe('Formatting', function() {
                it('With bugTrackerURL', function() {
                    reviewRequest.set('bugTrackerURL',
                                      'http://issues/?id=--bug_id--');
                    reviewRequest.draft.set('bugsClosed', [1, 2, 3]);
                    editor.trigger('fieldChanged:bugsClosed');

                    expect($field.text()).toBe('1, 2, 3');

                    const $links = $field.children('a');
                    expect($links.length).toBe(3);

                    let $link = $links.eq(0);
                    expect($link.hasClass('bug')).toBe(true);
                    expect($link.text()).toBe('1');
                    expect($link.attr('href')).toBe('http://issues/?id=1');

                    $link = $links.eq(1);
                    expect($link.hasClass('bug')).toBe(true);
                    expect($link.text()).toBe('2');
                    expect($link.attr('href')).toBe('http://issues/?id=2');

                    $link = $links.eq(2);
                    expect($link.hasClass('bug')).toBe(true);
                    expect($link.text()).toBe('3');
                    expect($link.attr('href')).toBe('http://issues/?id=3');
                });

                it('Without bugTrackerURL', function() {
                    reviewRequest.set('bugTrackerURL', '');
                    reviewRequest.draft.set('bugsClosed', [1, 2, 3]);
                    editor.trigger('fieldChanged:bugsClosed');

                    expect($field.html()).toBe('1, 2, 3');
                });
            });

            editCountTests();
            securityTests();
        });

        describe('Depends On', function() {
            setupFieldTests({
                fieldName: 'dependsOn',
                jsonFieldName: 'depends_on',
                selector: '#field_depends_on',
            });

            hasAutoCompleteTest();
            hasEditorTest();
            savingTest();

            it('Formatting', function() {
                reviewRequest.draft.set('dependsOn', [
                    {
                        id: '123',
                        url: '/r/123/',
                    },
                    {
                        id: '124',
                        url: '/r/124/',
                    },
                ]);
                editor.trigger('fieldChanged:dependsOn');

                const $fieldChildren = $field.children();
                expect($field.text()).toBe('123, 124');
                expect($fieldChildren.eq(0).attr('href')).toBe('/r/123/');
                expect($fieldChildren.eq(1).attr('href')).toBe('/r/124/');
            });

            editCountTests();
            securityTests();
        });

        describe('Change Descriptions', function() {
            function closeDescriptionTests(options) {
                beforeEach(function() {
                    reviewRequest.set('state', options.closeType);
                    view.showBanner();

                    spyOn(reviewRequest, 'close').and.callThrough();
                    spyOn(reviewRequest, 'save');
                });

                setupFieldTests({
                    fieldName: 'closeDescription',
                    jsonFieldName: 'close_description',
                    selector: options.bannerSel + ' #field_close_description',
                });

                hasEditorTest();

                it('Starts closed', function() {
                    expect($input.is(':visible')).toBe(false);
                });

                describe('Saves', function() {
                    function testSave(richText, textType, setRichText) {
                        const expectedData = {
                            status: options.jsonCloseType,
                            force_text_type: 'html',
                            include_text_types: 'raw',
                        };

                        expectedData[options.jsonTextTypeFieldName] = textType;
                        expectedData[options.jsonFieldName] = 'My Value';

                        fieldEditor.startEdit();

                        const textEditor = fieldEditor.textEditor;
                        textEditor.setText('My Value');

                        if (setRichText !== false) {
                            textEditor.setRichText(richText);
                        }

                        $input.triggerHandler('keyup');
                        fieldEditor.submit();

                        expect(reviewRequest.close).toHaveBeenCalled();
                        expect(reviewRequest.save).toHaveBeenCalled();
                        expect(reviewRequest.save.calls.argsFor(0)[0].data)
                            .toEqual(expectedData);
                    }

                    it('For Markdown', function() {
                        testSave(true, 'markdown');
                    });

                    it('For plain text', function() {
                        testSave(false, 'plain');
                    });
                });

                describe('State when statusEditable', function() {
                    it('Disabled when false', function() {
                        editor.set('statusEditable', false);
                        expect(fieldEditor.options.enabled).toBe(false);
                    });

                    it('Enabled when true', function() {
                        editor.set('statusEditable', true);
                        expect(fieldEditor.options.enabled).toBe(true);
                    });
                });

                describe('Formatting', function() {
                    it('Links', function() {
                        reviewRequest.set('closeDescription',
                                          'Testing /r/123');
                        editor.trigger('fieldChanged:closeDescription');

                        expect($field.text()).toBe('Testing /r/123');
                        expect($field.find('a').attr('href')).toBe('/r/123/');
                    });
                });

                inlineEditorResizeTests();
                editCountTests();
                securityTests({
                    fieldOnReviewRequest: true,
                    supportsRichText: true,
                });
            }

            describe('Discarded review requests', function() {
                closeDescriptionTests({
                    bannerSel: '#discard-banner',
                    closeType: RB.ReviewRequest.CLOSE_DISCARDED,
                    jsonCloseType: 'discarded',
                    jsonFieldName: 'close_description',
                    jsonTextTypeFieldName: 'close_description_text_type',
                });
            });

            describe('Draft review requests', function() {
                beforeEach(function() {
                    view.model.set('hasDraft', true);
                    view.showBanner();
                });

                setupFieldTests({
                    supportsRichText: true,
                    fieldID: 'change_description',
                    fieldName: 'changeDescription',
                    jsonFieldName: 'changedescription',
                    selector: '#draft-banner #field_change_description',
                });

                hasEditorTest();
                richTextSavingTest();

                editCountTests();
                securityTests({
                    fieldOnReviewRequest: true,
                    supportsRichText: true,
                });
            });

            describe('Submitted review requests', function() {
                closeDescriptionTests({
                    bannerSel: '#submitted-banner',
                    closeType: RB.ReviewRequest.CLOSE_SUBMITTED,
                    jsonCloseType: 'submitted',
                    jsonFieldName: 'close_description',
                    jsonTextTypeFieldName: 'close_description_text_type',
                });
            });
        });

        describe('Description', function() {
            setupFieldTests({
                supportsRichText: true,
                fieldName: 'description',
                jsonFieldName: 'description',
                selector: '#field_description',
            });

            hasEditorTest();
            richTextSavingTest();

            describe('Formatting', function() {
                it('Links', function() {
                    reviewRequest.draft.set('description', 'Testing /r/123');
                    editor.trigger('fieldChanged:description');

                    expect($field.text()).toBe('Testing /r/123');
                    expect($field.find('a').attr('href')).toBe('/r/123/');
                });
            });

            inlineEditorResizeTests();
            editCountTests();
            securityTests({
                supportsRichText: true,
            });
        });

        describe('Summary', function() {
            setupFieldTests({
                fieldName: 'summary',
                jsonFieldName: 'summary',
                selector: '#field_summary',
            });

            hasEditorTest();
            savingTest();
            editCountTests();
            securityTests();
        });

        describe('Testing Done', function() {
            setupFieldTests({
                supportsRichText: true,
                fieldName: 'testingDone',
                jsonFieldName: 'testing_done',
                selector: '#field_testing_done',
            });

            hasEditorTest();
            richTextSavingTest();

            describe('Formatting', function() {
                it('Links', function() {
                    reviewRequest.draft.set('testingDone', 'Testing /r/123');
                    editor.trigger('fieldChanged:testingDone');

                    expect($field.text()).toBe('Testing /r/123');
                    expect($field.find('a').attr('href')).toBe('/r/123/');
                });
            });

            inlineEditorResizeTests();
            editCountTests();
            securityTests({
                supportsRichText: true,
            });
        });

        describe('Reviewers', function() {
            describe('Groups', function() {
                setupFieldTests({
                    fieldName: 'targetGroups',
                    jsonFieldName: 'target_groups',
                    selector: '#field_target_groups',
                });

                hasAutoCompleteTest();
                hasEditorTest();
                savingTest();

                it('Formatting', function() {
                    reviewRequest.draft.set('targetGroups', [
                        {
                            name: 'group1',
                            url: '/groups/group1/',
                        },
                        {
                            name: 'group2',
                            url: '/groups/group2/',
                        }
                    ]);
                    editor.trigger('fieldChanged:targetGroups');

                    expect($field.html()).toBe(
                        '<a href="/groups/group1/">group1</a>, ' +
                        '<a href="/groups/group2/">group2</a>');
                });

                editCountTests();
                securityTests();
            });

            describe('People', function() {
                setupFieldTests({
                    fieldName: 'targetPeople',
                    jsonFieldName: 'target_people',
                    selector: '#field_target_people',
                });

                hasAutoCompleteTest();
                hasEditorTest();
                savingTest();

                it('Formatting', function() {
                    reviewRequest.draft.set('targetPeople', [
                        {
                            username: 'user1',
                            url: '/users/user1/',
                        },
                        {
                            username: 'user2',
                            url: '/users/user2/',
                        },
                    ]);
                    editor.trigger('fieldChanged:targetPeople');

                    expect($field.text()).toBe('user1, user2');
                    expect($($field.children()[0]).attr('href')).toBe('/users/user1/');
                    expect($($field.children()[1]).attr('href')).toBe('/users/user2/');
                });

                editCountTests();
                securityTests();
            });
        });

        describe('Owner', function() {
            setupFieldTests({
                jsonFieldName: 'submitter',
                selector: '#field_submitter',
            });

            hasAutoCompleteTest();
            hasEditorTest();
            savingTest();

            it('Formatting', function() {
                reviewRequest.draft.set('submitter',
                    {
                        title: 'user1',
                        href: '/users/user1/',
                    }
                );
                editor.trigger('fieldChanged:submitter');

                expect($field.text()).toBe('user1');
                expect(($field.children()).attr('href')).toBe('/users/user1/');
            });

            editCountTests();
        });

        describe('Custom fields', function() {
            beforeEach(function() {
                saveSpyFunc = (options, context) => {
                    expect(options.data['extra_data.' + jsonFieldName])
                        .toBe('My Value');
                    options.success.call(context);
                };
            });

            setupFieldTests({
                fieldID: 'my_custom',
                jsonFieldName: 'my_custom',
                selector: '#field_my_custom',
                useExtraData: true,
            });

            hasEditorTest();
            savingTest();
            editCountTests();
            securityTests();
        });

        describe('Custom rich-text field', function() {
            beforeEach(function() {
                saveSpyFunc = (options, context) => {
                    expect(options.data['extra_data.' + jsonFieldName])
                        .toBe('My Value');
                    options.success.call(context);
                };
            });

            setupFieldTests({
                supportsRichText: true,
                fieldID: 'my_rich_text_custom',
                jsonFieldName: 'my_rich_text_custom',
                selector: '#field_my_rich_text_custom',
                useExtraData: true,
            });

            it('Initial rich text state', function() {
                expect(fieldEditor.textEditor.richText).toBe(true);
            });

            hasEditorTest();
            richTextSavingTest();
            inlineEditorResizeTests();
            editCountTests();
            securityTests();
        });

        describe('Custom rich-text field with special name', function() {
            beforeEach(function() {
                saveSpyFunc = (options, context) => {
                    expect(options.data['extra_data.' + jsonFieldName])
                        .toBe('My Value');
                    options.success.call(context);
                };
            });

            setupFieldTests({
                supportsRichText: true,
                fieldID: 'text',
                jsonFieldName: 'text',
                selector: '#field_text',
                useExtraData: true,
            });

            hasEditorTest();
            richTextSavingTest();
            inlineEditorResizeTests();
            editCountTests();
            securityTests();
        });

        describe('Custom checkbox field', function() {
            beforeEach(function() {
                $field = view.$('#field_checkbox');

                saveSpyFunc = (options, context) => {
                    expect(options.data['extra_data.checkbox'])
                        .toBe(true);
                    options.success.call(context);
                };
                reviewRequest.draft.save.and.callFake(saveSpyFunc);
            });

            it('Saves', function() {
                const expectedData = {
                    'extra_data.checkbox': true,
                };

                $field.click();

                expect(reviewRequest.draft.save).toHaveBeenCalled();
                expect(reviewRequest.draft.save.calls.argsFor(0)[0].data)
                    .toEqual(expectedData);
            });
        });
    });

    describe('File attachments', function() {
        it('Rendering when added', function() {
            spyOn(RB.FileAttachmentThumbnail.prototype, 'render')
                .and.callThrough();

            expect($filesContainer.find('.file-container').length).toBe(0);

            view.render();
            editor.createFileAttachment();

            expect(RB.FileAttachmentThumbnail.prototype.render)
                .toHaveBeenCalled();
            expect($filesContainer.find('.file-container').length).toBe(1);
        });

        describe('Events', function() {
            let fileAttachment;
            let $thumbnail;

            beforeEach(function() {
                view.render();
                fileAttachment = editor.createFileAttachment();

                $thumbnail = $($filesContainer.find('.file-container')[0]);
                expect($thumbnail.length).toBe(1);
            });

            describe('beginEdit', function() {
                it('Increment edit count', function() {
                    expect(editor.get('editCount')).toBe(0);

                    $thumbnail.find('.file-caption .edit')
                        .data('inline-editor')
                        .startEdit();

                    expect(editor.get('editCount')).toBe(1);
                });
            });

            describe('endEdit', function() {
                describe('Decrement edit count', function() {
                    let $caption;
                    let inlineEditorView;

                    beforeEach(function() {
                        expect(editor.get('editCount')).toBe(0);

                        $caption = $thumbnail.find('.file-caption .edit');
                        inlineEditorView = $caption.data('inline-editor');
                        inlineEditorView.startEdit();
                    });

                    it('On cancel', function() {
                        inlineEditorView.cancel();
                        expect(editor.get('editCount')).toBe(0);
                    });

                    it('On submit', function() {
                        spyOn(fileAttachment, 'ready').and.callFake(
                            (options, context) => options.ready.call(context));
                        spyOn(fileAttachment, 'save');

                        $thumbnail.find('input')
                            .val('Foo')
                            .triggerHandler('keyup');

                        inlineEditorView.submit();

                        expect(editor.get('editCount')).toBe(0);
                    });
                });
            });
        });
    });

    describe('Methods', function() {
        describe('getFieldView', function() {
            it('Correct field is returned', function() {
                const fieldView = view.getFieldView('target_groups');
                expect(fieldView).not.toBe(undefined);
                expect(fieldView.fieldID).toBe('target_groups');

                expect(view.getFieldView('some_random_id')).toBe(undefined);
            });
        });
    });

    describe('Screenshots', function() {
        describe('Importing on render', function() {
            it('No screenshots', function() {
                view.render();

                expect(editor.get('screenshots').length).toBe(0);
            });

            it('With screenshots', function() {
                const screenshots = editor.get('screenshots');

                $screenshotsContainer.append(
                    screenshotThumbnailTemplate({ id: 42 }));

                spyOn(RB.ScreenshotThumbnail.prototype, 'render')
                    .and.callThrough();

                view.render();

                expect(RB.ScreenshotThumbnail.prototype.render)
                    .toHaveBeenCalled();
                expect(screenshots.length).toBe(1);
                expect(screenshots.at(0).id).toBe(42);
            });
        });

        describe('Events', function() {
            let $thumbnail;
            let screenshot;

            beforeEach(function() {
                $thumbnail = $(screenshotThumbnailTemplate({ id: 42 }))
                    .appendTo($screenshotsContainer);

                view.render();

                screenshot = editor.get('screenshots').at(0);
            });

            describe('beginEdit', function() {
                it('Increment edit count', function() {
                    expect(editor.get('editCount')).toBe(0);

                    $thumbnail.find('.screenshot-caption .edit')
                        .inlineEditor('startEdit');

                    expect(editor.get('editCount')).toBe(1);
                });
            });

            describe('endEdit', function() {
                describe('Decrement edit count', function() {
                    let $caption;

                    beforeEach(function() {
                        expect(editor.get('editCount')).toBe(0);

                        $caption = $thumbnail.find('.screenshot-caption .edit')
                            .inlineEditor('startEdit');
                    });

                    it('On cancel', function() {
                        $caption.inlineEditor('cancel');
                        expect(editor.get('editCount')).toBe(0);
                    });

                    it('On submit', function() {
                        spyOn(screenshot, 'ready').and.callFake(
                            (options, context) => options.ready.call(context));
                        spyOn(screenshot, 'save');

                        $thumbnail.find('input')
                            .val('Foo')
                            .triggerHandler('keyup');

                        $caption.inlineEditor('submit');

                        expect(editor.get('editCount')).toBe(0);
                    });
                });
            });
        });
    });

    describe('beforeUnload event handler', function() {
        /*
         * The components in ReviewablePageView uses editCount to determine how
         * many fields are being modified at the time, whereas editable/
         * statusEditable is only used in ReviewRequestEditorView.
         * So test both editable/statusEditable states to catch regressions
         * where onBeforeUnload becomes tied to editable/statusEditable states.
         */
        describe('editable=true', function() {
            beforeEach(function() {
                editor.set('statusEditable', true);
                editor.set('editable', true);

                expect(editor.get('statusEditable')).toBe(true);
                expect(editor.get('editable')).toBe(true);
                expect(editor.get('editCount')).toBe(0);
            });

            it('Warn user beforeUnload when editing', function() {
                view.model.incr('editCount');
                expect(editor.get('editCount')).toBe(1);

                expect(view._onBeforeUnload($.Event('beforeunload'))).toBeDefined();
            });

            it("Don't warn user beforeUnload when not editing", function() {
                expect(view._onBeforeUnload($.Event('beforeunload'))).toBeUndefined();
            });
        });

        describe('editable=false', function() {
            beforeEach(function() {
                editor.set('statusEditable', false);
                editor.set('editable', false);

                expect(editor.get('statusEditable')).toBe(false);
                expect(editor.get('editable')).toBe(false);
                expect(editor.get('editCount')).toBe(0);
            });

            it('Warn user beforeUnload when editing', function() {
                view.model.incr('editCount');
                expect(editor.get('editCount')).toBe(1);

                expect(view._onBeforeUnload($.Event('beforeunload'))).toBeDefined();
            });

            it("Don't warn user beforeUnload when not editing", function() {
                expect(view._onBeforeUnload($.Event('beforeunload'))).toBeUndefined();
            });
        });
    });
});
