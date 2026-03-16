import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    type DraftReviewRequest,
    API,
    ReviewRequest,
} from 'reviewboard/common';


suite('rb/resources/models/DraftReviewRequest', function() {
    let draft: DraftReviewRequest;

    beforeEach(function() {
        const reviewRequest = new ReviewRequest({
            id: 1,
            links: {
                draft: {
                    href: '/api/review-requests/123/draft/',
                },
            },
        });

        draft = reviewRequest.draft;

        spyOn(reviewRequest, 'ready').and.resolveTo();
        spyOn(reviewRequest, 'ensureCreated').and.resolveTo();
        spyOn(draft, 'ready').and.resolveTo();
    });

    it('url', function() {
        expect(draft.url()).toBe('/api/review-requests/123/draft/');
    });

    describe('publish', function() {
        it('With promises', async function() {
            spyOn(API, 'request').and.callThrough();
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.data.public).toBe(1);

                request.success({
                    draft: {
                        id: 1,
                        links: {},
                    },
                    stat: 'ok',
                });
            });

            /* Set some fields in order to pass validation. */
            draft.set({
                targetGroups: [{
                    name: 'mygroup',
                    url: '/groups/mygroup',
                }],
                summary: 'My summary',
                description: 'My description',
            });

            await draft.publish();

            expect(API.request).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
        });
    });

    it('parse', function() {
        const data = draft.parse({
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
                testing_done_text_type: 'plain',
                links: {
                    submitter: 'submitter',
                },
            },
        });

        expect(data).not.toBe(undefined);
        expect(data.id).toBe(1);
        expect(data.branch).toBe('branch');
        expect(data.bugsClosed).toBe('bugsClosed');
        expect(data.changeDescription).toBe('changeDescription');
        expect(data.changeDescriptionRichText).toBe(true);
        expect(data.description).toBe('description');
        expect(data.descriptionRichText).toBe(true);
        expect(data.public).toBe('public');
        expect(data.summary).toBe('summary');
        expect(data.submitter).toBe('submitter');
        expect(data.targetGroups).toBe('targetGroups');
        expect(data.targetPeople).toBe('targetPeople');
        expect(data.testingDone).toBe('testingDone');
        expect(data.testingDoneRichText).toBe(false);
    });
});
