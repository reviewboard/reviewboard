import { suite } from '@beanbag/jasmine-suites';
import {
    afterAll,
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { ContentViewport } from 'reviewboard/ui';


declare const $testsScratch: JQuery;


suite('rb/ui/models/ContentViewport', () => {
    let contentViewport: ContentViewport;
    let el1: HTMLElement;
    let el2: HTMLElement;

    async function waitForResize() {
        await new Promise(resolve => {
            contentViewport.once('handledResize',
                                 () => setTimeout(resolve, 0));
        });
    }

    beforeEach(() => {
        contentViewport = new ContentViewport();

        el1 = document.createElement('div');
        el1.style.width = '200px';
        el1.style.height = '100px';
        $testsScratch.append(el1);

        el2 = document.createElement('div');
        el2.style.width = '75px';
        el2.style.height = '50px';
        $testsScratch.append(el2);
    });

    afterEach(() => {
        contentViewport.clearTracking();
    });

    afterAll(() => {
        contentViewport = null;
        el1 = null;
        el2 = null;
    });

    describe('Methods', () => {
        describe('trackElement', () => {
            it('On top', () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'top',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 0,
                    top: 100,
                });

                contentViewport.trackElement({
                    el: el2,
                    side: 'top',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 0,
                    top: 150,
                });
            });

            it('On bottom', () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'bottom',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 100,
                    left: 0,
                    right: 0,
                    top: 0,
                });

                contentViewport.trackElement({
                    el: el2,
                    side: 'bottom',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 150,
                    left: 0,
                    right: 0,
                    top: 0,
                });
            });

            it('On left', () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'left',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 200,
                    right: 0,
                    top: 0,
                });

                contentViewport.trackElement({
                    el: el2,
                    side: 'left',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 275,
                    right: 0,
                    top: 0,
                });
            });

            it('On right', () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'right',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 200,
                    top: 0,
                });

                contentViewport.trackElement({
                    el: el2,
                    side: 'right',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 275,
                    top: 0,
                });
            });
        });

        it('untrackElement', async () => {
            contentViewport.trackElement({
                el: el1,
                side: 'bottom',
            });
            contentViewport.trackElement({
                el: el2,
                side: 'bottom',
            });
            contentViewport.untrackElement(el1);

            expect(contentViewport.attributes).toEqual({
                bottom: 50,
                left: 0,
                right: 0,
                top: 0,
            });

            contentViewport.untrackElement(el2);

            expect(contentViewport.attributes).toEqual({
                bottom: 0,
                left: 0,
                right: 0,
                top: 0,
            });

            /* Make sure a resize doesn't trigger anything. */
            el1.style.width = '1000px';
            el2.style.height = '1000px';

            await new Promise(resolve => setTimeout(resolve, 50));

            expect(contentViewport.attributes).toEqual({
                bottom: 0,
                left: 0,
                right: 0,
                top: 0,
            });
        });
    });

    describe('Events', () => {
        describe('Element resize', () => {
            it('On top', async () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'top',
                });
                contentViewport.trackElement({
                    el: el2,
                    side: 'top',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 0,
                    top: 150,
                });

                /* Resize the first element. */
                el1.style.height = '113px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 0,
                    top: 163,
                });

                /* Resize the second element. */
                el2.style.height = '23px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 0,
                    top: 136,
                });
            });

            it('On bottom', async () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'bottom',
                });
                contentViewport.trackElement({
                    el: el2,
                    side: 'bottom',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 150,
                    left: 0,
                    right: 0,
                    top: 0,
                });

                /* Resize the first element. */
                el1.style.height = '113px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 163,
                    left: 0,
                    right: 0,
                    top: 0,
                });

                /* Resize the second element. */
                el2.style.height = '23px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 136,
                    left: 0,
                    right: 0,
                    top: 0,
                });
            });

            it('On left', async () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'left',
                });
                contentViewport.trackElement({
                    el: el2,
                    side: 'left',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 275,
                    right: 0,
                    top: 0,
                });

                /* Resize the first element. */
                el1.style.width = '209px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 284,
                    right: 0,
                    top: 0,
                });

                /* Resize the second element. */
                el2.style.width = '72px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 281,
                    right: 0,
                    top: 0,
                });
            });

            it('On right', async () => {
                contentViewport.trackElement({
                    el: el1,
                    side: 'right',
                });
                contentViewport.trackElement({
                    el: el2,
                    side: 'right',
                });

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 275,
                    top: 0,
                });

                /* Resize the first element. */
                el1.style.width = '209px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 284,
                    top: 0,
                });

                /* Resize the second element. */
                el2.style.width = '72px';

                await waitForResize();

                expect(contentViewport.attributes).toEqual({
                    bottom: 0,
                    left: 0,
                    right: 281,
                    top: 0,
                });
            });
        });
    });
});
