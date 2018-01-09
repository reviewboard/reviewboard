suite('rb/views/DiffFragmentQueueView', function() {
    const URL_PREFIX = '/r/123/_fragments/diff-comments/';

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
        let $container4;

        beforeEach(function() {
            $container1 = $('<div id="container1_123"/>')
                .appendTo(window.$testsScratch);
            $container2 = $('<div id="container1_124"/>')
                .appendTo(window.$testsScratch);
            $container3 = $('<div id="container1_125"/>')
                .appendTo(window.$testsScratch);
            $container4 = $('<div id="container1_126"/>')
                .appendTo(window.$testsScratch);

            fragmentQueue.queueLoad('123', 'key1');
            fragmentQueue.queueLoad('124', 'key1');
            fragmentQueue.queueLoad('125', 'key1');
            fragmentQueue.queueLoad('126', 'key2');
        });

        it('Fragment queueing', function() {
            const queue = fragmentQueue._queue;

            expect(queue.length).not.toBe(0);

            expect(queue.key1.length).toBe(3);
            expect(queue.key1).toContain({
                commentID: '123',
                onFragmentRendered: null,
            });
            expect(queue.key1).toContain({
                commentID: '124',
                onFragmentRendered: null,
            });
            expect(queue.key1).toContain({
                commentID: '125',
                onFragmentRendered: null,
            });
            expect(queue.key2.length).toBe(1);
            expect(queue.key2).toContain({
                commentID: '126',
                onFragmentRendered: null,
            });
        });

        it('Batch loading', function(done) {
            spyOn($, 'ajax').and.callFake(function(options) {
                expect(options.dataType).toBe('arraybuffer');

                const url = options.url;
                let blob;

                if (url === `${URL_PREFIX}123,124,125/`) {
                    const html1 = new Blob(['<span>Comment one</span>']);
                    const html2 = new Blob(['<span>Comment two</span>']);
                    const html3 = new Blob(['<span>Comment three</span>']);

                    blob = RB.DataUtils.buildBlob([
                        [{
                            type: 'uint32',
                            values: [123, html1.size],
                        }],
                        html1,
                        [{
                            type: 'uint32',
                            values: [124, html2.size],
                        }],
                        html2,
                        [{
                            type: 'uint32',
                            values: [125, html3.size],
                        }],
                        html3,
                    ]);
                } else if (url === `${URL_PREFIX}126/`) {
                    const html = new Blob(['<span>Comment 4</span>']);

                    blob = RB.DataUtils.buildBlob([
                        [{
                            type: 'uint32',
                            values: [126, html.size],
                        }],
                        html,
                    ]);
                } else {
                    fail(`Unexpected URL ${url}`);
                    return;
                }

                RB.DataUtils.readBlobAsArrayBuffer(blob, options.success);
            });

            fragmentQueue.loadFragments(() => {
                expect($.ajax.calls.count()).toBe(2);

                expect($container1.data('diff-fragment-view')).toBeTruthy();
                expect($container1.html()).toBe('<span>Comment one</span>');

                expect($container2.data('diff-fragment-view')).toBeTruthy();
                expect($container2.html()).toBe('<span>Comment two</span>');

                expect($container3.data('diff-fragment-view')).toBeTruthy();
                expect($container3.html()).toBe('<span>Comment three</span>');

                expect($container4.data('diff-fragment-view')).toBeTruthy();
                expect($container4.html()).toBe('<span>Comment 4</span>');

                done();
            });
        });

        it('With Unicode content', function(done) {
            spyOn($, 'ajax').and.callFake(function(options) {
                expect(options.dataType).toBe('arraybuffer');

                const url = options.url;
                let arrayBuffer;

                if (url === `${URL_PREFIX}123,124,125/`) {
                    /* UTF-8 bytes for "<span>áéíóú 🔥</span>" */
                    const html1 = [
                        60, 115, 112, 97, 110, 62, 195, 161, 195, 169,
                        195, 173, 195, 179, 195, 186, 32, 240, 159, 148,
                        165, 60, 47, 115, 112, 97, 110, 62,
                    ];

                    /* UTF-8 bytes for "<span>ÄËÏÖÜŸ 😱</span>" */
                    const html2 = [
                        60, 115, 112, 97, 110, 62, 195, 132, 195, 139,
                        195, 143, 195, 150, 195, 156, 197, 184, 32, 240,
                        159, 152, 177, 60, 47, 115, 112, 97, 110, 62,
                    ];

                    /* UTF-8 bytes for "<span>🔥😱</span>" */
                    const html3 = [
                        60, 115, 112, 97, 110, 62, 240, 159, 148, 165, 240,
                        159, 152, 177, 60, 47, 115, 112, 97, 110, 62,
                    ];

                    expect(html1.length).toBe(28);
                    expect(html2.length).toBe(30);
                    expect(html3.length).toBe(21);

                    arrayBuffer = RB.DataUtils.buildArrayBuffer([
                        {
                            type: 'uint32',
                            values: [123, html1.length],
                        },
                        {
                            type: 'uint8',
                            values: html1,
                        },
                        {
                            type: 'uint32',
                            values: [124, html2.length],
                        },
                        {
                            type: 'uint8',
                            values: html2,
                        },
                        {
                            type: 'uint32',
                            values: [125, html3.length],
                        },
                        {
                            type: 'uint8',
                            values: html3,
                        },
                    ]);
                } else if (url === `${URL_PREFIX}126/`) {
                    /* UTF-8 bytes for "<span>ĀĒĪŌ 👿</span>" */
                    const html = [
                        60, 115, 112, 97, 110, 62, 196, 128, 196, 146,
                        196, 170, 197, 140, 32, 240, 159, 145, 191, 60,
                        47, 115, 112, 97, 110, 62,
                    ];

                    expect(html.length).toBe(26);

                    arrayBuffer = RB.DataUtils.buildArrayBuffer([
                        {
                            type: 'uint32',
                            values: [126, html.length],
                        },
                        {
                            type: 'uint8',
                            values: html,
                        },
                    ]);
                } else {
                    fail(`Unexpected URL ${url}`);
                    return;
                }

                options.success(arrayBuffer);
            });

            fragmentQueue.loadFragments(() => {
                expect($.ajax.calls.count()).toBe(2);

                expect($container1.data('diff-fragment-view')).toBeTruthy();
                expect($container1.html()).toBe('<span>áéíóú 🔥</span>');

                expect($container2.data('diff-fragment-view')).toBeTruthy();
                expect($container2.html()).toBe('<span>ÄËÏÖÜŸ 😱</span>');

                expect($container3.data('diff-fragment-view')).toBeTruthy();
                expect($container3.html()).toBe('<span>🔥😱</span>');

                expect($container4.data('diff-fragment-view')).toBeTruthy();
                expect($container4.html()).toBe('<span>ĀĒĪŌ 👿</span>');

                done();
            });
        });

        it('With saved fragments', function(done) {
            spyOn($, 'ajax').and.callFake(function(options) {
                expect(options.dataType).toBe('arraybuffer');

                const url = options.url;
                let blob;

                if (url === `${URL_PREFIX}124/`) {
                    const html = new Blob(['<span>New comment 2</span>']);

                    blob = RB.DataUtils.buildBlob([
                        [{
                            type: 'uint32',
                            values: [124, html.size],
                        }],
                        html,
                    ]);
                } else if (url === `${URL_PREFIX}126/`) {
                    const html = new Blob(['<span>New comment 4</span>']);

                    blob = RB.DataUtils.buildBlob([
                        [{
                            type: 'uint32',
                            values: [126, html.size],
                        }],
                        html,
                    ]);
                } else {
                    fail(`Unexpected URL ${url}`);
                    return;
                }

                RB.DataUtils.readBlobAsArrayBuffer(blob, options.success);
            });

            /*
             * We'll set up three containers, with the third being having its
             * view disassociated and the fourth as a completely new container.
             * The unsaved pre-loaded containers (2) and the new container (4)
             * will be loaded. The disassociated container (3) will have a
             * new view set up.
             */
            const view1 = new RB.DiffFragmentView();
            $container1
                .html('<span>Comment 1</span>')
                .data('diff-fragment-view', view1);

            const view2 = new RB.DiffFragmentView();
            $container2
                .html('<span>Comment 2</span>')
                .data('diff-fragment-view', view2);

            const view3 = new RB.DiffFragmentView();
            $container3
                .html('<span>Comment 3</span>')
                .data('diff-fragment-view', view3);

            /*
             * We're going to save 123, 125, and 126 (which is not loaded).
             * Only 123 and 125 will actually be saved.
             */
            fragmentQueue.saveFragment('123');
            fragmentQueue.saveFragment('125');
            fragmentQueue.saveFragment('126');

            /* Disassociate container 3's view. */
            $container3.removeData('diff-fragment-view');

            fragmentQueue.loadFragments(() => {
                expect($.ajax.calls.count()).toBe(2);

                expect($container1.data('diff-fragment-view')).toBe(view1);
                expect($container1.html()).toBe('<span>Comment 1</span>');

                expect($container2.data('diff-fragment-view')).toBe(view2);
                expect($container2.html()).toBe('<span>New comment 2</span>');

                expect($container3.data('diff-fragment-view')).toBeTruthy();
                expect($container3.data('diff-fragment-view')).not.toBe(view3);
                expect($container3.html()).toBe('<span>Comment 3</span>');

                expect($container4.data('diff-fragment-view')).toBeTruthy();
                expect($container4.html()).toBe('<span>New comment 4</span>');

                expect(fragmentQueue._saved).toEqual({});

                done();
            });
        });
    });
});
