import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    expect,
    it,
} from 'jasmine-core';

import { PromiseQueue } from 'reviewboard/common';


suite('rb/utils/promiseQueue', () => {
    const queue = new PromiseQueue();
    let abort: AbortController;

    beforeEach(() => {
        abort = new AbortController();
    });

    afterEach(() => {
        queue.clear();
    });

    it('Runs queued tasks', async () => {
        const results = [];

        queue.add(async () => {
            results.push(1);
        });
        queue.add(async () => {
            results.push(2);
        });
        queue.add(async () => {
            results.push(3);
        });

        await queue.start(abort.signal);

        expect(results).toEqual([1, 2, 3]);
    });

    it('Continues running despite errored task', async () => {
        const results = [];

        spyOn(console, 'error');
        const error = new Error('Fail!');

        queue.add(async () => {
            results.push(1);
        });
        queue.add(async () => {
            throw error;
        });
        queue.add(async () => {
            results.push(3);
        });

        await queue.start(abort.signal);

        expect(results).toEqual([1, 3]);
        expect(console.error).toHaveBeenCalledWith(
            'Queued task returned error:',
            error);
    });

    it('Runs task that was added during queue', async () => {
        const results = [];

        queue.add(async () => {
            results.push(1);
        });
        queue.add(async () => {
            queue.add(async () => {
                results.push(3);
            });

            results.push(2);
        });

        await queue.start(abort.signal);

        expect(results).toEqual([1, 2, 3]);
    });

    it('Stops after abort', async () => {
        const results = [];

        queue.add(async () => {
            results.push(1);
        });
        queue.add(async () => {
            results.push(2);

            abort.abort();
        });
        queue.add(async () => {
            results.push(3);
        });

        await queue.start(abort.signal);

        expect(results).toEqual([1, 2]);
    });

    it('Stops after clear', async () => {
        const results = [];

        queue.add(async () => {
            results.push(1);
        });
        queue.add(async () => {
            results.push(2);

            queue.clear();
        });
        queue.add(async () => {
            results.push(3);
        });

        await queue.start(abort.signal);

        expect(results).toEqual([1, 2]);
    });
});
