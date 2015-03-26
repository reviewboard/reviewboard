suite('rb/views/DiffFragmentQueueView', function() {
    var fragmentQueue;

    beforeEach(function() {
        fragmentQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'container1',
            reviewRequestPath: '/r/123/',
            queueName: 'diff_fragments'
        });
    });

    describe('Diff fragment loading', function() {
        beforeEach(function() {
            fragmentQueue.queueLoad("123", 'key1');
            fragmentQueue.queueLoad("124", 'key1');
            fragmentQueue.queueLoad("125", 'key2');
        });

        it('Fragment queueing', function() {
            var queue = fragmentQueue._queue;

            expect(queue.length).not.toBe(0);

            expect(queue.key1.length).toBe(2);
            expect(queue.key1).toContain('123');
            expect(queue.key1).toContain('124');
            expect(queue.key2.length).toBe(1);
            expect(queue.key2).toContain('125');
        });

        it('Batch loading', function() {
            spyOn(fragmentQueue, '_addScript');

            fragmentQueue.loadFragments();

            expect(fragmentQueue._addScript).toHaveBeenCalledWith(
                '/r/123/fragments/diff-comments/' +
                '123,124/?queue=diff_fragments&' +
                'container_prefix=container1&' + TEMPLATE_SERIAL
            );
        });
    });
});
