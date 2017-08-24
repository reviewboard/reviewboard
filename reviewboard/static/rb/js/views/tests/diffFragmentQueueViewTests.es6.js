suite('rb/views/DiffFragmentQueueView', function() {
    const URL_PREFIX = '/r/123/fragments/diff-comments/';
    const URL_SUFFIX = '/?container_prefix=container1&queue=diff_fragments&' +
                       TEMPLATE_SERIAL;

    let fragmentQueue;

    beforeEach(function() {
        fragmentQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'container1',
            reviewRequestPath: '/r/123/',
            queueName: 'diff_fragments'
        });
    });

    describe('Diff fragment loading', function() {
        let $container1;
        let $container2;
        let $container3;

        beforeEach(function() {
            $container1 = $('<div id="container1_123"/>')
                .appendTo(window.$testsScratch);
            $container2 = $('<div id="container1_124"/>')
                .appendTo(window.$testsScratch);
            $container3 = $('<div id="container1_125"/>')
                .appendTo(window.$testsScratch);

            fragmentQueue.queueLoad('123', 'key1');
            fragmentQueue.queueLoad('124', 'key1');
            fragmentQueue.queueLoad('125', 'key2');
        });

        it('Fragment queueing', function() {
            const queue = fragmentQueue._queue;

            expect(queue.length).not.toBe(0);

            expect(queue.key1.length).toBe(2);
            expect(queue.key1).toContain('123');
            expect(queue.key1).toContain('124');
            expect(queue.key2.length).toBe(1);
            expect(queue.key2).toContain('125');
        });

        it('Batch loading', function() {
            const urls = [
                `${URL_PREFIX}123,124${URL_SUFFIX}`,
                `${URL_PREFIX}125${URL_SUFFIX}`,
            ];

            spyOn(fragmentQueue, '_addScript').and.callFake(
                function(url, callback) {
                    if (url === urls[0]) {
                        $container1.html('<span>Comment 1</span>');
                        $container2.html('<span>Comment 2</span>');
                    } else if (url === urls[1]) {
                        $container3.html('<span>Comment 3</span>');
                    } else {
                        fail(`Unexpected URL ${url}`);
                        return;
                    }

                    if (callback !== undefined) {
                        callback();
                    }

                    $.funcQueue('diff_fragments').next();
                });

            fragmentQueue.loadFragments();

            expect(fragmentQueue._addScript.calls.count()).toBe(2);

            expect($container1.data('diff-fragment-view')).toBeTruthy();
            expect($container1.html()).toBe('<span>Comment 1</span>');

            expect($container2.data('diff-fragment-view')).toBeTruthy();
            expect($container2.html()).toBe('<span>Comment 2</span>');

            expect($container3.data('diff-fragment-view')).toBeTruthy();
            expect($container3.html()).toBe('<span>Comment 3</span>');
        });

        it('With saved fragments', function() {
            const urls = [
                `${URL_PREFIX}124${URL_SUFFIX}`,
                `${URL_PREFIX}125${URL_SUFFIX}`,
            ];

            spyOn(fragmentQueue, '_addScript').and.callFake(
                function(url, callback) {
                    if (url === urls[0]) {
                        $container2.html('<span>New comment 2</span>');
                    } else if (url === urls[1]) {
                        $container3.html('<span>New comment 3</span>');
                    } else {
                        fail(`Unexpected URL ${url}`);
                        return;
                    }

                    if (callback !== undefined) {
                        callback();
                    }

                    $.funcQueue('diff_fragments').next();
                });

            /*
             * We'll set up the first two containers, but leave the third as
             * completely new. Both the unsaved pre-loaded container (2) and
             * the new container (3) will be loaded.
             */
            $container1
                .html('<span>Comment 1</span>')
                .data('diff-fragment-view', new RB.DiffFragmentView());

            $container2
                .html('<span>Comment 2</span>')
                .data('diff-fragment-view', new RB.DiffFragmentView());

            /*
             * We're going to save 123 and 125 (which is not loaded). Only
             * 123 will actually be saved.
             */
            fragmentQueue.saveFragment('123');
            fragmentQueue.saveFragment('125');

            fragmentQueue.loadFragments();

            expect(fragmentQueue._addScript.calls.count()).toBe(2);

            expect($container1.data('diff-fragment-view')).toBeTruthy();
            expect($container1.html()).toBe('<span>Comment 1</span>');

            expect($container2.data('diff-fragment-view')).toBeTruthy();
            expect($container2.html()).toBe('<span>New comment 2</span>');

            expect($container3.data('diff-fragment-view')).toBeTruthy();
            expect($container3.html()).toBe('<span>New comment 3</span>');

            expect(fragmentQueue._saved).toEqual({});
        });
    });
});
