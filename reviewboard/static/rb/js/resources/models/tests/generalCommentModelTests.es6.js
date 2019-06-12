suite('rb/resources/models/GeneralComment', function() {
    let model;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new RB.GeneralComment({
            parentObject: new RB.BaseResource({
                'public': true,
            }),
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                general_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text_type: 'markdown',
                    text: 'foo',
                },
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
            spyOn(RB.BaseComment.prototype, 'toJSON').and.callThrough();
            model.toJSON();
            expect(RB.BaseComment.prototype.toJSON).toHaveBeenCalled();
        });
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(RB.BaseComment.prototype, 'validate');
            model.validate({});
            expect(RB.BaseComment.prototype.validate).toHaveBeenCalled();
        });
    });
});
