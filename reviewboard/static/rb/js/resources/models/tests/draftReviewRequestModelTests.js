suite('rb/resources/models/DraftReviewRequest', function() {
    var draft,
        callbacks;

    beforeEach(function() {
        var reviewRequest = new RB.ReviewRequest({
            id: 1,
            links: {
                draft: {
                    href: '/api/review-requests/123/draft/'
                }
            }
        });

        draft = reviewRequest.draft;

        callbacks = {
            success: function() {},
            error: function() {}
        };

        spyOn(callbacks, 'success');
        spyOn(callbacks, 'error');

        spyOn(reviewRequest, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });

        spyOn(reviewRequest, 'ensureCreated')
            .andCallFake(function(options, context) {
                options.success.call(context);
            });

        spyOn(draft, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });
    });

    it('url', function() {
        expect(draft.url()).toBe('/api/review-requests/123/draft/');
    });

    it('publish', function() {
        spyOn(RB, 'apiCall').andCallThrough();
        spyOn($, 'ajax').andCallFake(function(request) {
            expect(request.data['public']).toBe(1);

            request.success({
                stat: 'ok',
                draft: {
                    id: 1,
                    links: {}
                }
            });
        });

        /* Set some fields in order to pass validation. */
        draft.set({
            targetGroups: [{
                name: 'mygroup',
                url: '/groups/mygroup'
            }],
            summary: 'My summary',
            description: 'My description'
        });

        draft.publish({
            success: callbacks.success,
            error: callbacks.error
        });

        expect(callbacks.error).not.toHaveBeenCalled();
        expect(callbacks.success).toHaveBeenCalled();
        expect(RB.apiCall).toHaveBeenCalled();
        expect($.ajax).toHaveBeenCalled();
    });

    it('parse', function() {
        var data = draft.parse({
            stat: 'ok',
            draft: {
                id: 1,
                branch: 'branch',
                bugs_closed: 'bugsClosed',
                changedescription: 'changeDescription',
                changedescription_text_type: 'markdown',
                description: 'description',
                'public': 'public',
                description_text_type: 'markdown',
                summary: 'summary',
                target_groups: 'targetGroups',
                target_people: 'targetPeople',
                testing_done: 'testingDone',
                testing_done_text_type: 'plain'
            }
        });

        expect(data).not.toBe(undefined);
        expect(data.id).toBe(1);
        expect(data.branch).toBe('branch');
        expect(data.bugsClosed).toBe('bugsClosed');
        expect(data.changeDescription).toBe('changeDescription');
        expect(data.changeDescriptionRichText).toBe(true);
        expect(data.description).toBe('description');
        expect(data.descriptionRichText).toBe(true);
        expect(data['public']).toBe('public');
        expect(data.summary).toBe('summary');
        expect(data.targetGroups).toBe('targetGroups');
        expect(data.targetPeople).toBe('targetPeople');
        expect(data.testingDone).toBe('testingDone');
        expect(data.testingDoneRichText).toBe(false);
    });

    describe('validate', function() {
        describe('When publishing', function() {
            var options = {
                    publishing: true
                },
                attrs;

            beforeEach(function() {
                attrs = {
                    targetGroups: [{
                        name: 'mygroup',
                        url: '/groups/mygroup/'
                    }],
                    targetPeople: [{
                        username: 'myuser',
                        url: '/users/myuser/'
                    }],
                    summary: 'summary',
                    description: 'description'
                };
            });

            describe('Description', function() {
                it('Has description', function() {
                    expect(draft.validate(attrs, options)).toBe(undefined);
                });

                it('No description', function() {
                    attrs.description = '';
                    expect(draft.validate(attrs, options)).toBe(
                        RB.DraftReviewRequest.strings.DESCRIPTION_REQUIRED);
                });

                it('No description (after trim)', function() {
                    attrs.description = '    ';
                    expect(draft.validate(attrs, options)).toBe(
                        RB.DraftReviewRequest.strings.DESCRIPTION_REQUIRED);
                });
            });

            describe('Summary', function() {
                it('Has summary', function() {
                    expect(draft.validate(attrs, options)).toBe(undefined);
                });

                it('No summary', function() {
                    attrs.summary = '';
                    expect(draft.validate(attrs, options)).toBe(
                        RB.DraftReviewRequest.strings.SUMMARY_REQUIRED);
                });

                it('No summary (after trim)', function() {
                    attrs.summary = '    ';
                    expect(draft.validate(attrs, options)).toBe(
                        RB.DraftReviewRequest.strings.SUMMARY_REQUIRED);
                });
            });

            describe('Reviewers', function() {
                it('Has groups and no users', function() {
                    attrs.targetPeople = [];
                    expect(draft.validate(attrs, options)).toBe(undefined);
                });

                it('Has users and no groups', function() {
                    attrs.targetGroups = [];
                    expect(draft.validate(attrs, options)).toBe(undefined);
                });

                it('No reviewers', function() {
                    attrs.targetGroups = [];
                    attrs.targetPeople = [];
                    expect(draft.validate(attrs, options)).toBe(
                        RB.DraftReviewRequest.strings.REVIEWERS_REQUIRED);
                });
            });
        });
    });
});

