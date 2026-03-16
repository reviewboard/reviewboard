import { suite } from '@beanbag/jasmine-suites';

import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import {
    BaseComment,
    BaseResource,
    GeneralComment,
} from 'reviewboard/common';


suite('rb/resources/models/GeneralComment', function() {
    let model: GeneralComment;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new GeneralComment({
            parentObject: new BaseResource({
                'public': true,
            }),
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                general_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text: 'foo',
                    text_type: 'markdown',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(RB.BaseComment.STATE_RESOLVED);
            expect(data.richText).toBe(true);
            expect(data.text).toBe('foo');
        });
    });

    describe('toJSON', function() {
        it('BaseComment.toJSON called', function() {
            spyOn(BaseComment.prototype, 'toJSON').and.callThrough();
            model.toJSON();
            expect(BaseComment.prototype.toJSON).toHaveBeenCalled();
        });
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(BaseComment.prototype, 'validate');
            model.validate({});
            expect(BaseComment.prototype.validate).toHaveBeenCalled();
        });
    });
});
