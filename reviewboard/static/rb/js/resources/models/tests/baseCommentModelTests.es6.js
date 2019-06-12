suite('rb/resources/models/BaseComment', function() {
    const strings = RB.BaseComment.strings;
    let parentObject;
    let model;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            'public': true,
        });

        model = new RB.BaseComment({
            parentObject: parentObject,
        });

        expect(model.validate(model.attributes)).toBe(undefined);
    });

    describe('State values', function() {
        it('STATE_DROPPED', function() {
            expect(RB.BaseComment.STATE_DROPPED).toBe('dropped');
        });

        it('STATE_OPEN', function() {
            expect(RB.BaseComment.STATE_OPEN).toBe('open');
        });

        it('STATE_RESOLVED', function() {
            expect(RB.BaseComment.STATE_RESOLVED).toBe('resolved');
        });
    });

    describe('destroyIfEmpty', function() {
        beforeEach(function() {
            spyOn(model, 'destroy');
        });

        it('Destroying when text is empty', function() {
            model.set('text', '');
            model.destroyIfEmpty();
            expect(model.destroy).toHaveBeenCalled();
        });

        it('Not destroying when text is not empty', function() {
            model.set('text', 'foo');
            model.destroyIfEmpty();
            expect(model.destroy).not.toHaveBeenCalled();
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_comment';
        });

        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                my_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text: 'foo',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(RB.BaseComment.STATE_RESOLVED);
            expect(data.text).toBe('foo');
        });
    });

    describe('toJSON', function() {
        describe('force_text_type field', function() {
            it('With value', function() {
                model.set('forceTextType', 'html');
                const data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();
                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                model.set('includeTextTypes', 'html');
                const data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();

                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('issue_opened field', function() {
            it('Default', function() {
                const data = model.toJSON();
                expect(data.issue_opened).toBe(null);
            });

            it('With value', function() {
                model.set('issueOpened', false);
                let data = model.toJSON();
                expect(data.issue_opened).toBe(false);

                model.set('issueOpened', true);
                data = model.toJSON();
                expect(data.issue_opened).toBe(true);
            });
        });

        describe('issue_status field', function() {
            it('When not loaded', function() {
                model.set('issueStatus', RB.BaseComment.STATE_DROPPED);
                const data = model.toJSON();
                expect(data.issue_status).toBe(undefined);
            });

            it('When loaded and parent is not public', function() {
                parentObject.set('public', false);

                model.set({
                    loaded: true,
                    issueStatus: RB.BaseComment.STATE_DROPPED,
                    parentObject: parentObject,
                });

                const data = model.toJSON();
                expect(data.issue_status).toBe(undefined);
            });

            it('When loaded and parent is public', function() {
                parentObject.set('public', true);

                model.set({
                    loaded: true,
                    issueStatus: RB.BaseComment.STATE_DROPPED,
                    parentObject: parentObject,
                });

                const data = model.toJSON();
                expect(data.issue_status).toBe(RB.BaseComment.STATE_DROPPED);
            });
        });

        describe('richText field', function() {
            it('With true', function() {
                model.set('richText', true);
                const data = model.toJSON();
                expect(data.text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('richText', false);
                const data = model.toJSON();
                expect(data.text_type).toBe('plain');
            });
        });

        describe('text field', function() {
            it('With value', function() {
                model.set('text', 'foo');
                const data = model.toJSON();
                expect(data.text).toBe('foo');
            });
        });
    });

    describe('validate', function() {
        describe('issueState', function() {
            it('STATE_DROPPED', function() {
                expect(model.validate({
                    issueStatus: RB.BaseComment.STATE_DROPPED,
                })).toBe(undefined);
            });

            it('STATE_OPEN', function() {
                expect(model.validate({
                    issueStatus: RB.BaseComment.STATE_OPEN,
                })).toBe(undefined);
            });

            it('STATE_RESOLVED', function() {
                expect(model.validate({
                    issueStatus: RB.BaseComment.STATE_RESOLVED,
                })).toBe(undefined);
            });

            it('Unset', function() {
                expect(model.validate({
                    issueStatus: '',
                })).toBe(undefined);

                expect(model.validate({
                    issueStatus: undefined,
                })).toBe(undefined);

                expect(model.validate({
                    issueStatus: null,
                })).toBe(undefined);
            });

            it('Invalid values', function() {
                expect(model.validate({
                    issueStatus: 'foobar',
                })).toBe(strings.INVALID_ISSUE_STATUS);
            });
        });

        describe('parentObject', function() {
            it('With value', function() {
                expect(model.validate({
                    parentObject: parentObject,
                })).toBe(undefined);
            });

            it('Unset', function() {
                expect(model.validate({
                    parentObject: null,
                })).toBe(RB.BaseResource.strings.UNSET_PARENT_OBJECT);
            });
        });
    });
});
