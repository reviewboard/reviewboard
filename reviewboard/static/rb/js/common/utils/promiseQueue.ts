/**
 * A queue for running multiple promises in sequence.
 *
 * Version Added:
 *     8.0
 */


/**
 * Type for a task that can be added to the queue.
 *
 * This is either a promise, or a method that returns a promise.
 *
 * Version Added:
 *     8.0
 */
type Task = Promise<unknown> | ((abort: AbortSignal) => Promise<unknown>);


/**
 * A queue for running multiple promises in sequence.
 *
 * Version Added:
 *     8.0
 */
export class PromiseQueue {
    /**********************
     * Instance variables *
     **********************/

    /** The queue of operations to run. */
    #queue: Task[] = [];

    /** Whether the queue is currently running. */
    #running = false;

    /**
     * Add a task to the queue.
     *
     * Args:
     *     task (Task):
     *         The task to add.
     */
    add(task: Task) {
        this.#queue.push(task);
    }

    /**
     * Clear the queue.
     */
    clear() {
        this.#queue = [];
    }

    /**
     * Start the queue.
     *
     * Args:
     *     abort (AbortSignal):
     *         The signal for an abort controller.
     */
    async start(abort: AbortSignal) {
        if (this.#running) {
            /*
             * The queue was asked to start when it's already running. We can
             * just bail out now since the existing run will pick up any
             * newly-added items.
             */
            return;
        }

        this.#running = true;

        while (this.#queue.length && !abort.aborted) {
            const task = this.#queue.shift();

            try {
                if (typeof task === 'function') {
                    await task(abort);
                } else {
                    await task;
                }
            } catch(e) {
                console.error('Queued task returned error:', e);
            }
        }

        if (abort.aborted) {
            this.clear();
        }

        this.#running = false;
    }
}
