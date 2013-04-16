describe('models/DraftReviewRequest', function() {
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
            expect(request.data.public).toBe(1);

            request.success({
                stat: 'ok',
                draft: {
                    id: 1,
                    links: {}
                }
            });
        });

        draft.publish({
            success: callbacks.success,
            error: callbacks.error
        });

        expect(RB.apiCall).toHaveBeenCalled();
        expect($.ajax).toHaveBeenCalled();
        expect(callbacks.success).toHaveBeenCalled();
        expect(callbacks.error).not.toHaveBeenCalled();
    });

    it('parse', function() {
        var data = draft.parse({
            draft: {
                id: 1,
                branch: 'branch',
                bugs_closed: 'bugsClosed',
                change_description: 'changeDescription',
                description: 'description',
                public: 'public',
                summary: 'summary',
                target_groups: 'targetGroups',
                target_people: 'targetPeople',
                testing_done: 'testingDone'
            }
        });

        expect(data).not.toBe(undefined);
        expect(data.id).toBe(1);
        expect(data.branch).toBe('branch');
        expect(data.bugsClosed).toBe('bugsClosed');
        expect(data.changeDescription).toBe('changeDescription');
        expect(data.description).toBe('description');
        expect(data.public).toBe('public');
        expect(data.summary).toBe('summary');
        expect(data.targetGroups).toBe('targetGroups');
        expect(data.targetPeople).toBe('targetPeople');
        expect(data.testingDone).toBe('testingDone');
    });
});

