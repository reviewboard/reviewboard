import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    BaseComment,
    BaseResource,
    CommentIssueStatusType,
} from 'reviewboard/common';


suite('rb/resources/models/BaseComment', function() {
    const strings = BaseComment.strings;
    let parentObject;
    let model;

    beforeEach(function() {
        parentObject = new BaseResource({
            'public': true,
        });

        model = new BaseComment({
            parentObject: parentObject,
        });

        expect(model.validate(model.attributes)).toBe(undefined);
    });

    describe('State values', function() {
        it('STATE_DROPPED', function() {
            expect(BaseComment.STATE_DROPPED).toBe('dropped');
            expect(BaseComment.STATE_DROPPED)
                .toBe(CommentIssueStatusType.DROPPED);
        });

        it('STATE_OPEN', function() {
            expect(BaseComment.STATE_OPEN).toBe('open');
            expect(BaseComment.STATE_OPEN).toBe(CommentIssueStatusType.OPEN);
        });

        it('STATE_RESOLVED', function() {
            expect(BaseComment.STATE_RESOLVED).toBe('resolved');
            expect(BaseComment.STATE_RESOLVED)
                .toBe(CommentIssueStatusType.RESOLVED);
        });

        it('STATE_VERIFYING_DROPPED', function() {
            expect(BaseComment.STATE_VERIFYING_DROPPED)
                .toBe('verifying-dropped');
            expect(BaseComment.STATE_VERIFYING_DROPPED)
                .toBe(CommentIssueStatusType.VERIFYING_DROPPED);
        });

        it('STATE_VERIFYING_RESOLVED', function() {
            expect(BaseComment.STATE_VERIFYING_RESOLVED)
                .toBe('verifying-resolved');
            expect(BaseComment.STATE_VERIFYING_RESOLVED)
                .toBe(CommentIssueStatusType.VERIFYING_RESOLVED);
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
                my_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text: 'foo',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(CommentIssueStatusType.RESOLVED);
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
                model.set('issueStatus', CommentIssueStatusType.DROPPED);
                const data = model.toJSON();
                expect(data.issue_status).toBe(undefined);
            });

            it('When loaded and parent is not public', function() {
                parentObject.set('public', false);

                model.set({
                    issueStatus: CommentIssueStatusType.DROPPED,
                    loaded: true,
                    parentObject: parentObject,
                });

                const data = model.toJSON();
                expect(data.issue_status).toBe(undefined);
            });

            it('When loaded and parent is public', function() {
                parentObject.set('public', true);

                model.set({
                    issueStatus: CommentIssueStatusType.DROPPED,
                    loaded: true,
                    parentObject: parentObject,
                });

                const data = model.toJSON();
                expect(data.issue_status).toBe(CommentIssueStatusType.DROPPED);
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
            it('DROPPED', function() {
                expect(model.validate({
                    issueStatus: CommentIssueStatusType.DROPPED,
                })).toBe(undefined);
            });

            it('OPEN', function() {
                expect(model.validate({
                    issueStatus: CommentIssueStatusType.OPEN,
                })).toBe(undefined);
            });

            it('RESOLVED', function() {
                expect(model.validate({
                    issueStatus: CommentIssueStatusType.RESOLVED,
                })).toBe(undefined);
            });

            it('VERIFYING_DROPPED', function() {
                expect(model.validate({
                    issueStatus: CommentIssueStatusType.VERIFYING_DROPPED,
                })).toBe(undefined);
            });

            it('VERIFYING_RESOLVED', function() {
                expect(model.validate({
                    issueStatus: CommentIssueStatusType.VERIFYING_RESOLVED,
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
                })).toBe(BaseResource.strings.UNSET_PARENT_OBJECT);
            });
        });
    });
});
