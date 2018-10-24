suite('rb/pages/views/DiffViewerPageView', function() {
    /**
     * Make a replacement function for $.ajax(url).
     *
     * Args:
     *     url (string):
     *         The expected URL.
     *
     *     rsp (object):
     *         The response to trigger the done callback with.
     *
     * Returns:
     *     function:
     *     A function to use in ``spyOn().and.fallFake()``.
     *
     *     The returned function returns an object that mimics the return of
     *     ``$.ajax(url)``.
     */
    function makeAjaxFn(url, rsp) {
        return function(url) {
            expect(url).toBe(url);

            return {
                done(cb) {
                    cb(rsp);
                },
            };
        };
    }

    const tableTemplate = _.template(dedent`
        <div class="diff-container">
         <table class="sidebyside">
          <thead>
           <tr class="filename-row">
            <th colspan="4">
             <a name="<%- fileID %>" class="file-anchor"></a>
            </th>
           </tr>
          </thead>
          <% _.each(chunks, function(chunk) { %>
           <tbody class="<%- chunk.type %>">
            <% _.each(chunk.lines, function(line, i) { %>
             <tr line="<%- line.vNumber %>">
              <th>
               <% if (i === 0 && chunk.type !== "equal") { %>
                <a name="<%- chunk.id %>" class="chunk-anchor"></a>
               <% } %>
               <%- line.leftNumber || "" %>
              </th>
              <td class="l"></td>
              <th><%- line.rightNumber || "" %></th>
              <td class="r"></td>
             </tr>
            <% }); %>
           </tbody>
          <% }); %>
         </table>
        </div>
    `);

    const pageTemplate = dedent`
        <div>
         <div id="review-banner"></div>
         <div id="diff_commit_list">
          <div class="commit-list-container">
          </div>
         </div>
         <div id="diffs"></div>
        </div>
    `;

    let page;
    let pageView;
    let $diffs;

    beforeEach(function() {
        /*
         * Disable the router so that the page doesn't change the URL on the
         * page while tests run.
         */
        spyOn(window.history, 'pushState');
        spyOn(window.history, 'replaceState');
    });

    afterEach(function() {
        RB.DnDUploader.instance = null;
        Backbone.history.stop();
    });

    describe('Without commits', function() {
        beforeEach(function() {
            page = new RB.DiffViewerPage({
                checkForUpdates: false,
                pagination: {
                    current_page: 1,
                },
                reviewRequestData: {
                    id: 123,
                    loaded: true,
                    state: RB.ReviewRequest.PENDING,
                },
                revision: {
                    revision: 1,
                    interdiff_revision: null,
                    is_interdiff: false,
                },
                editorData: {
                    mutableByUser: true,
                    statusMutableByUser: true,
                },
            }, {
                parse: true,
            });

            pageView = new RB.DiffViewerPageView({
                el: $(pageTemplate).appendTo($testsScratch),
                model: page,
            });

            $diffs = pageView.$el.children('#diffs');

            /* Don't communicate with the server for page updates. */
            spyOn(page.get('reviewRequest'), 'ready').and.callFake(
                (options, context) => options.ready.call(context));
        });

        describe('Anchors', function() {
            it('Tracks all types', function() {
                $diffs.html(tableTemplate({
                    fileID: 'file1',
                    chunks: [
                        {
                            id: '1.1',
                            lines: [
                                {
                                    type: 'insert',
                                    vNumber: 100,
                                    leftNumber: 100,
                                    rightNumber: 101,
                                },
                            ],
                        },
                        {
                            id: '1.2',
                            lines: [
                                {
                                    type: 'equal',
                                    vNumber: 101,
                                    leftNumber: 101,
                                    rightNumber: 101,
                                },
                            ],
                        },
                        {
                            id: '1.3',
                            lines: [
                                {
                                    type: 'delete',
                                    vNumber: 102,
                                    leftNumber: 102,
                                    rightNumber: 101,
                                },
                            ],
                        },
                    ],
                }));

                pageView.render();
                pageView._updateAnchors(pageView.$el.find('table').eq(0));

                expect(pageView._$anchors.length).toBe(4);
                expect(pageView._$anchors[0].name).toBe('file1');
                expect(pageView._$anchors[1].name).toBe('1.1');
                expect(pageView._$anchors[2].name).toBe('1.2');
                expect(pageView._$anchors[3].name).toBe('1.3');
                expect(pageView._selectedAnchorIndex).toBe(0);
            });

            describe('Navigation', function() {
                beforeEach(function() {
                    $diffs.html([
                        tableTemplate({
                            fileID: 'file1',
                            chunks: [
                                {
                                    id: '1.1',
                                    lines: [
                                        {
                                            type: 'insert',
                                            vNumber: 100,
                                            leftNumber: 100,
                                            rightNumber: 101,
                                        },
                                    ],
                                },
                                {
                                    id: '1.2',
                                    lines: [
                                        {
                                            type: 'equal',
                                            vNumber: 101,
                                            leftNumber: 101,
                                            rightNumber: 101,
                                        },
                                    ],
                                },
                            ],
                        }),
                        tableTemplate({
                            fileID: 'file2',
                            chunks: [],
                        }),
                        tableTemplate({
                            fileID: 'file3',
                            chunks: [
                                {
                                    id: '2.1',
                                    lines: [
                                        {
                                            type: 'insert',
                                            vNumber: 100,
                                            leftNumber: 100,
                                            rightNumber: 101,
                                        }
                                    ]
                                },
                                {
                                    id: '2.2',
                                    lines: [
                                        {
                                            type: 'equal',
                                            vNumber: 101,
                                            leftNumber: 101,
                                            rightNumber: 101,
                                        },
                                    ],
                                },
                            ],
                        }),
                    ]);

                    pageView.render();

                    pageView.$el.find('table').each(function() {
                        pageView._updateAnchors($(this));
                    });
                });

                describe('Previous file', function() {
                    it('From file', function() {
                        pageView.selectAnchorByName('file2');
                        expect(pageView._selectedAnchorIndex).toBe(3);

                        pageView._selectPreviousFile();

                        expect(pageView._selectedAnchorIndex).toBe(0);
                    });

                    it('From chunk', function() {
                        pageView.selectAnchorByName('2.2');
                        expect(pageView._selectedAnchorIndex).toBe(6);

                        pageView._selectPreviousFile();

                        expect(pageView._selectedAnchorIndex).toBe(4);
                    });

                    it('On first file', function() {
                        pageView.selectAnchorByName('file1');
                        expect(pageView._selectedAnchorIndex).toBe(0);

                        pageView._selectPreviousFile();

                        expect(pageView._selectedAnchorIndex).toBe(0);
                    });
                });

                describe('Next file', function() {
                    it('From file', function() {
                        pageView.selectAnchorByName('file1');
                        expect(pageView._selectedAnchorIndex).toBe(0);

                        pageView._selectNextFile();

                        expect(pageView._selectedAnchorIndex).toBe(3);
                    });

                    it('From chunk', function() {
                        pageView.selectAnchorByName('1.1');
                        expect(pageView._selectedAnchorIndex).toBe(1);

                        pageView._selectNextFile();

                        expect(pageView._selectedAnchorIndex).toBe(3);
                    });

                    it('On last file', function() {
                        pageView.selectAnchorByName('file3');
                        expect(pageView._selectedAnchorIndex).toBe(4);

                        pageView._selectNextFile();

                        expect(pageView._selectedAnchorIndex).toBe(4);
                    });
                });

                describe('Previous anchor', function() {
                    it('From file to file', function() {
                        pageView.selectAnchorByName('file3');
                        expect(pageView._selectedAnchorIndex).toBe(4);

                        pageView._selectPreviousDiff();

                        expect(pageView._selectedAnchorIndex).toBe(3);
                    });

                    it('From file to chunk', function() {
                        pageView.selectAnchorByName('file2');
                        expect(pageView._selectedAnchorIndex).toBe(3);

                        pageView._selectPreviousDiff();

                        expect(pageView._selectedAnchorIndex).toBe(2);
                    });

                    it('From chunk to file', function() {
                        pageView.selectAnchorByName('2.1');
                        expect(pageView._selectedAnchorIndex).toBe(5);

                        pageView._selectPreviousDiff();

                        expect(pageView._selectedAnchorIndex).toBe(4);
                    });

                    it('From chunk to chunk', function() {
                        pageView.selectAnchorByName('2.2');
                        expect(pageView._selectedAnchorIndex).toBe(6);

                        pageView._selectPreviousDiff();

                        expect(pageView._selectedAnchorIndex).toBe(5);
                    });

                    it('On first file', function() {
                        pageView.selectAnchorByName('file1');
                        expect(pageView._selectedAnchorIndex).toBe(0);

                        pageView._selectPreviousDiff();

                        expect(pageView._selectedAnchorIndex).toBe(0);
                    });
                });

                describe('Next anchor', function() {
                    it('From file to file', function() {
                        pageView.selectAnchorByName('file2');
                        expect(pageView._selectedAnchorIndex).toBe(3);

                        pageView._selectNextDiff();

                        expect(pageView._selectedAnchorIndex).toBe(4);
                    });

                    it('From file to chunk', function() {
                        pageView.selectAnchorByName('file1');
                        expect(pageView._selectedAnchorIndex).toBe(0);

                        pageView._selectNextDiff();

                        expect(pageView._selectedAnchorIndex).toBe(1);
                    });

                    it('From chunk to file', function() {
                        pageView.selectAnchorByName('1.2');
                        expect(pageView._selectedAnchorIndex).toBe(2);

                        pageView._selectNextDiff();

                        expect(pageView._selectedAnchorIndex).toBe(3);
                    });

                    it('From chunk to chunk', function() {
                        pageView.selectAnchorByName('2.1');
                        expect(pageView._selectedAnchorIndex).toBe(5);

                        pageView._selectNextDiff();

                        expect(pageView._selectedAnchorIndex).toBe(6);
                    });

                    it('On last chunk', function() {
                        pageView.selectAnchorByName('2.2');
                        expect(pageView._selectedAnchorIndex).toBe(6);

                        pageView._selectNextDiff();

                        expect(pageView._selectedAnchorIndex).toBe(6);
                    });
                });
            });
        });

        describe('Key bindings', function() {
            function triggerKeyPress(c) {
                const evt = $.Event('keypress');
                evt.which = c.charCodeAt(0);

                pageView.$el.trigger(evt);
            }

            function testKeys(description, funcName, keyList) {
                describe(description, function() {
                    keyList.forEach(key => {
                        let label;
                        let c;

                        if (key.length === 2) {
                            label = key[0];
                            c = key[1];
                        } else {
                            label = "'" + key + "'";
                            c = key;
                        }

                        it(label, function() {
                            pageView.render();
                            spyOn(pageView, funcName);
                            triggerKeyPress(c);
                            expect(pageView[funcName]).toHaveBeenCalled();
                        });
                    });
                });
            }

            testKeys('Previous file',
                     '_selectPreviousFile',
                     ['a', 'A', 'K', 'P', '<', 'm']);
            testKeys('Next file',
                     '_selectNextFile',
                     ['f', 'F', 'J', 'N', '>']);
            testKeys('Previous anchor',
                     '_selectPreviousDiff',
                     ['s', 'S', 'k', 'p', ',']);
            testKeys('Next anchor',
                     '_selectNextDiff',
                     ['d', 'D', 'j', 'n', '.']);
            testKeys('Previous comment',
                     '_selectPreviousComment',
                     ['[', 'x']);
            testKeys('Next comment',
                     '_selectNextComment',
                     [']', 'c']);
            testKeys('Recenter selected',
                     '_recenterSelected',
                     [['Enter', '\x0d']]);
            testKeys('Create comment',
                     '_createComment',
                     ['r', 'R']);
        });

        describe('Reviewable Management', function() {
            beforeEach(function() {
                spyOn(pageView, 'queueLoadDiff');

                pageView.render();
            });

            it('File added', function() {
                expect($diffs.find('.diff-container').length).toBe(0);
                expect(pageView.queueLoadDiff.calls.count()).toBe(0);

                page.files.reset([
                    new RB.DiffFile({
                        id: 100,
                        filediff: {
                            id: 200,
                            revision: 1,
                        },
                    }),
                ]);

                expect($diffs.find('.diff-container').length).toBe(1);
                expect(pageView.queueLoadDiff.calls.count()).toBe(1);
            });

            it('Files reset', function() {
                expect($diffs.find('.diff-container').length).toBe(0);
                expect(pageView.queueLoadDiff.calls.count()).toBe(0);

                /* Add an initial batch of files. */
                page.files.reset([
                    new RB.DiffFile({
                        id: 100,
                        filediff: {
                            id: 200,
                            revision: 1,
                        },
                    }),
                ]);

                expect($diffs.find('.diff-container').length).toBe(1);
                expect(pageView.queueLoadDiff.calls.count()).toBe(1);

                /* Now do another. */
                page.files.reset([
                    new RB.DiffFile({
                        id: 101,
                        filediff: {
                            id: 201,
                            revision: 2,
                        },
                    }),
                ]);

                const $containers = $diffs.find('.diff-container');
                expect($containers.length).toBe(1);
                expect($containers.find('.sidebyside')[0].id)
                    .toBe('file_container_101');
                expect(pageView.queueLoadDiff.calls.count()).toBe(2);
            });
        });

        describe('Page view/URL state', function() {
            let router;

            beforeEach(function() {
                spyOn(page, 'loadDiffRevision');

                /*
                 * Bypass all the actual history logic and get to the actual
                 * router handler.
                 */
                spyOn(Backbone.history, 'matchRoot').and.returnValue(true);

                router = pageView.router;
                spyOn(router, 'navigate').and.callFake((url, options) => {
                    if (!options || options.trigger !== false) {
                        Backbone.history.loadUrl(url);
                    }
                });
            });

            describe('Initial URL', function() {
                it('Initial default load', function() {
                    pageView._setInitialURL('', 'index_header');

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('Initial load of first page explicit', function() {
                    pageView._setInitialURL('?page=1', 'index_header');

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?page=1#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('Initial load of page > 1', function() {
                    pageView._setInitialURL('?page=2', 'index_header');

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?page=2#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('Initial load of interdiff', function() {
                    page.revision.set('revision', 2);
                    page.revision.set('interdiffRevision', 3);
                    pageView._setInitialURL('?page=2', 'index_header');

                    expect(router.navigate).toHaveBeenCalledWith(
                        '2-3/?page=2#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('Initial load with filename patterns', function() {
                    pageView._setInitialURL('?filenames=*.js,src/*',
                                            'index_header');

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?filenames=*.js,src/*#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });
            });

            describe('_navigate', function() {
                beforeEach(function() {
                    page.set('filenamePatterns', '*.js,src/*');
                });

                it('With page == 1', function() {
                    pageView._navigate({
                        page: 1,
                    });

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?filenames=*.js%2Csrc%2F*',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: '*.js,src/*',
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });
                });

                it('With page > 1', function() {
                    pageView._navigate({
                        page: 2,
                    });

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?page=2&filenames=*.js%2Csrc%2F*',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: '*.js,src/*',
                        interdiffRevision: null,
                        page: 2,
                        revision: 1,
                        tipCommitID: null,
                    });
                });

                it('New revision on page > 1', function() {
                    page.pagination.set('currentPage', 2);
                    pageView._onRevisionSelected([0, 2]);

                    expect(router.navigate).toHaveBeenCalledWith(
                        '2/?filenames=*.js%2Csrc%2F*',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: '*.js,src/*',
                        interdiffRevision: null,
                        page: 1,
                        revision: 2,
                        tipCommitID: null,
                    });
                });

                it('Same revision on page > 1', function() {
                    page.pagination.set('currentPage', 2);

                    pageView._navigate({
                        revision: 1,
                    });

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?page=2&filenames=*.js%2Csrc%2F*',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: '*.js,src/*',
                        interdiffRevision: null,
                        page: 2,
                        revision: 1,
                        tipCommitID: null,
                    });
                });

                it('With updateURLOnly', function() {
                    page.pagination.set('currentPage', 2);

                    pageView._navigate({
                        revision: 2,
                        interdiffRevision: 3,
                        updateURLOnly: true,
                    });

                    expect(router.navigate).toHaveBeenCalledWith(
                        '2-3/?filenames=*.js%2Csrc%2F*',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('With anchor', function() {
                    pageView._navigate({
                        anchor: 'test',
                    });

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?filenames=*.js%2Csrc%2F*#test',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: '*.js,src/*',
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });
                });
            });

            describe('Revision selector', function() {
                describe('New diff revision selected', function() {
                    it('From single revision', function() {
                        pageView._onRevisionSelected([0, 2]);

                        expect(router.navigate).toHaveBeenCalledWith(
                            '2/',
                            {
                                trigger: true,
                            });
                        expect(page.loadDiffRevision).toHaveBeenCalledWith({
                            baseCommitID: null,
                            filenamePatterns: null,
                            interdiffRevision: null,
                            page: 1,
                            revision: 2,
                            tipCommitID: null,
                        });
                    });

                    it('From interdiff revision', function() {
                        page.revision.set('interdiffRevision', 2);

                        pageView._onRevisionSelected([0, 2]);

                        expect(router.navigate).toHaveBeenCalledWith(
                            '2/',
                            {
                                trigger: true,
                            });
                        expect(page.loadDiffRevision).toHaveBeenCalledWith({
                            baseCommitID: null,
                            filenamePatterns: null,
                            interdiffRevision: null,
                            page: 1,
                            revision: 2,
                            tipCommitID: null,
                        });
                    });
                });

                it('New interdiff revision selected', function() {
                    pageView._onRevisionSelected([2, 5]);

                    expect(router.navigate).toHaveBeenCalledWith(
                        '2-5/',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: null,
                        interdiffRevision: 5,
                        page: 1,
                        revision: 2,
                        tipCommitID: null,
                    });
                });
            });

            describe('Page selector', function() {
                it('With page == 1', function() {
                    pageView._onPageSelected(true, 1);

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        page: 1,
                        revision: 1,
                        interdiffRevision: null,
                        filenamePatterns: null,
                        tipCommitID: null,
                    });
                });

                it('With page > 1', function() {
                    pageView._onPageSelected(true, 2);

                    expect(router.navigate).toHaveBeenCalledWith(
                        '1/?page=2',
                        {
                            trigger: true,
                        });
                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        page: 2,
                        revision: 1,
                        interdiffRevision: null,
                        filenamePatterns: null,
                        tipCommitID: null,
                    });
                });
            });

            it('Anchor selection', function() {
                const $anchor = $('<a name="test"/>');

                pageView.render();
                pageView.selectAnchor($anchor);

                expect(router.navigate).toHaveBeenCalledWith(
                    '1/#test',
                    {
                        replace: true,
                        trigger: false,
                    });
                expect(page.loadDiffRevision).not.toHaveBeenCalled();
            });
        });
    });

    describe('With commits', function() {
        let $commitList;

        beforeEach(function() {
            page = new RB.DiffViewerPage({
                checkForUpdates: false,
                pagination: {
                    current_page: 1,
                },
                reviewRequestData: {
                    id: 123,
                    loaded: true,
                    state: RB.ReviewRequest.PENDING,
                },
                revision: {
                    revision: 1,
                    interdiff_revision: null,
                    is_interdiff: false,
                },
                editorData: {
                    mutableByUser: true,
                    statusMutableByUser: true,
                },
                commits: [
                    {
                        author_name: 'Author Name',
                        commit_id: 'r123',
                        commit_message: 'Commit message 1',
                        id: 1,
                        parent_id: 'r122',
                    },
                    {
                        author_name: 'Author Name',
                        commit_id: 'r124',
                        commit_message: 'Commit message 2',
                        id: 2,
                        parent_id: 'r123',
                    },
                    {
                        author_name: 'Author Name',
                        commit_id: 'r125',
                        commit_message: 'Commit message 3',
                        id: 3,
                        parent_id: 'r124',
                    },
                ],
            }, {
                parse: true,
            });

            pageView = new RB.DiffViewerPageView({
                el: $(pageTemplate).appendTo($testsScratch),
                model: page,
            });

            $commitList = $testsScratch.find('#diff_commit_list');

            /* Don't communicate with the server for page updates. */
            spyOn(page.get('reviewRequest'), 'ready').and.callFake(
                (options, context) => options.ready.call(context));
        });

        describe('Render', function() {
            it('Initial render (without interdiff)', function() {
                pageView.render();

                const $table = $commitList.find('table');
                expect($table.length).toBe(1);
                expect($table.find('tbody tr').length).toBe(3);
            });

            it('Initial render (with interdiff)', function() {
                page.revision.set('interdiffRevision', 456);
                page.commitHistoryDiff.reset([
                    {
                        entry_type: RB.CommitHistoryDiffEntry.REMOVED,
                        old_commit_id: 1,
                    },
                    {
                        entry_type: RB.CommitHistoryDiffEntry.ADDED,
                        new_commit_id: 2,
                    },
                    {
                        entry_type: RB.CommitHistoryDiffEntry.ADDED,
                        new_commit_id: 3,
                    },
                ], {
                    parse: true,
                });

                pageView.render();

                const $table = $commitList.find('table');
                expect($table.length).toBe(1);
                expect($table.find('tbody tr').length).toBe(3);
            });

            it('Subsequent render (without interdiff)', function() {
                pageView.render();

                spyOn($, 'ajax').and.callFake(makeAjaxFn(
                    '/api/review-requests/123/diff-context/?revision=2',
                    {
                        diff_context: {
                            revision: {
                                revision: 2,
                                interdiff_revision: null,
                                is_interdiff: false,
                            },
                            commits: [
                                {
                                    author_name: 'Author Name',
                                    commit_id: 'r125',
                                    commit_message: 'Commit message',
                                    id: 4,
                                    parent_id: 'r124',
                                },
                            ],
                        }
                    }));

                page.loadDiffRevision({
                    revision: 2,
                });

                expect($.ajax).toHaveBeenCalled();

                const $table = $commitList.find('table');
                expect($table.length).toBe(1);
                expect($table.find('tbody tr').length).toBe(1);
            });

            it('Subsequent render (with interdiff)', function() {
                pageView.render();

                const rspPayload = {
                    diff_context: {
                        revision: {
                            revision: 2,
                            interdiff_revision: 3,
                            is_interdiff: true,
                        },
                        commits: [
                            {
                                author_name: 'Author Name',
                                commit_id: 'r124',
                                commit_message: 'Commit message',
                                id: 1,
                            },
                            {
                                author_name: 'Author Name',
                                commit_id: 'r125',
                                commit_message: 'Commit message',
                                id: 2,
                            },
                        ],
                        commit_history_diff: [
                            {
                                entry_type: RB.CommitHistoryDiffEntry.REMOVED,
                                old_commit_id: 1,
                            },
                            {
                                entry_type: RB.CommitHistoryDiffEntry.ADDED,
                                new_commit_id: 2,
                            },
                        ],
                    },
                };

                spyOn($, 'ajax').and.callFake(makeAjaxFn(
                    '/api/review-requests/123/diff-context/' +
                    '?revision=2&interdiff-revision=3',
                    rspPayload));

                page.loadDiffRevision({
                    revision: 2,
                    interdiffRevision: 3,
                });

                expect($.ajax).toHaveBeenCalled();

                const $table = $commitList.find('table');
                expect($table.length).toBe(1);
                expect($table.find('tbody tr').length).toBe(2);
            });

            it('Initial render with base commit ID', function() {
                page.revision.set('baseCommitID', 1);

                pageView.render();

                const commitListModel = pageView._commitListView.model;
                expect(commitListModel.get('baseCommitID')).toBe(1);
                expect(commitListModel.get('tipCommitID')).toBe(null);
            });

            it('Initial render with tip commit ID', function() {
                page.revision.set('tipCommitID', 2);

                pageView.render();

                const commitListModel = pageView._commitListView.model;
                expect(commitListModel.get('baseCommitID')).toBe(null);
                expect(commitListModel.get('tipCommitID')).toBe(2);
            });

            it('Initial render with base commit ID and tip commit ID',
               function() {
                   page.revision.set({
                       baseCommitID: 1,
                       tipCommitID: 2,
                   });

                   pageView.render();

                   const commitListModel = pageView._commitListView.model;
                   expect(commitListModel.get('baseCommitID')).toBe(1);
                   expect(commitListModel.get('tipCommitID')).toBe(2);
               });
        });

        describe('Page view/URL state', function() {
            beforeEach(function() {
                spyOn(page, 'loadDiffRevision').and.callThrough();

                spyOn(Backbone.history, 'matchRoot').and.returnValue(true);
                spyOn(pageView.router, 'navigate')
                    .and.callFake((url, options) => {
                        if (!options || options.trigger !== false) {
                            Backbone.history.loadUrl(url);
                        }
                    });
            });

            describe('Initial URL', function() {
                it('With base-commit-id', function() {
                    pageView._setInitialURL('?base-commit-id=2',
                                            'index_header');

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?base-commit-id=2#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('With tip-commit-id', function() {
                    pageView._setInitialURL('?tip-commit-id=2',
                                            'index_header');

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?tip-commit-id=2#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });

                it('With base-commit-id and tip-commit-id', function() {
                    pageView._setInitialURL('?base-commit-id=1&tip-commit-id=2',
                                            'index_header');

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?base-commit-id=1&tip-commit-id=2#index_header',
                        {
                            replace: true,
                            trigger: false,
                        });
                    expect(page.loadDiffRevision).not.toHaveBeenCalled();
                });
            });

            describe('Commit range controls', function() {
                it('Selecting initial base commit ID', function() {
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1&base-commit-id=1',
                        {
                            diff_context: {
                                revision: {
                                    revision: 1,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    base_commit_id: 1,
                                    tip_commit_id: null,
                                },
                            },
                        }));

                    $rows.eq(1).find('.base-commit-selector').click();

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?base-commit-id=1',
                        {
                            trigger: true,
                        });

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: 1,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(1);
                    expect(page.revision.get('tipCommitID')).toBe(null);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(1);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(null);
                });

                it('Selecting initial tip commit ID', function() {
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1&tip-commit-id=2',
                        {
                            diff_context: {
                                revision: {
                                    base_commit_id: null,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    revision: 1,
                                    tip_commit_id: 2,
                                },
                            },
                        }));

                    $rows.eq(1).find('.tip-commit-selector').click();

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?tip-commit-id=2',
                        {
                            trigger: true,
                        });

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: 2,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(null);
                    expect(page.revision.get('tipCommitID')).toBe(2);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(null);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(2);
                });

                it('Selecting new base commit ID', function() {
                    page.revision.set('baseCommitID', 3);
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1&base-commit-id=1',
                        {
                            diff_context: {
                                revision: {
                                    base_commit_id: 1,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    revision: 1,
                                    tip_commit_id: null,
                                },
                            },
                        }));

                    $rows.eq(1).find('.base-commit-selector').click();

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?base-commit-id=1',
                        {
                            trigger: true,
                        });

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: 1,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(1);
                    expect(page.revision.get('tipCommitID')).toBe(null);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(1);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(null);
                });


                it('Selecting new tip commit ID', function() {
                    page.revision.set('tipCommitID', 2);
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1&tip-commit-id=1',
                        {
                            diff_context: {
                                revision: {
                                    base_commit_id: null,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    revision: 1,
                                    tip_commit_id: 1,
                                },
                            },
                        }));

                    $rows.eq(0).find('.tip-commit-selector').click();

                    expect(pageView.router.navigate).toHaveBeenCalledWith(
                        '1/?tip-commit-id=1',
                        {
                            trigger: true,
                        });

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: 1,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(null);
                    expect(page.revision.get('tipCommitID')).toBe(1);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(null);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(1);
                });

                it('Selecting blank base commit ID', function() {
                    page.revision.set('baseCommitID', 2);
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1',
                        {
                            diff_context: {
                                revision: {
                                    base_commit_id: null,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    revision: 1,
                                    tip_commit_id: null,
                                },
                            },
                        }));

                    $rows.eq(0).find('.base-commit-selector').click();

                    expect(pageView.router.navigate)
                        .toHaveBeenCalledWith('1/', {trigger: true});

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(null);
                    expect(page.revision.get('tipCommitID')).toBe(null);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(null);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(null);
                });

                it('Selecting blank tip commit ID', function() {
                    page.revision.set('tipCommitID', 2);
                    pageView.render();

                    const $table = $commitList.find('table');
                    const $rows = $table.find('tbody tr');

                    expect($table.length).toBe(1);
                    expect($rows.length).toBe(3);

                    spyOn($, 'ajax').and.callFake(makeAjaxFn(
                        '/api/review-requests/123/diff-context/' +
                        '?revision=1',
                        {
                            diff_context: {
                                revision: {
                                    base_commit_id: null,
                                    interdiff_revision: null,
                                    is_interdiff: false,
                                    revision: 1,
                                    tip_commit_id: null,
                                },
                            },
                        }));

                    $rows.eq(2).find('.tip-commit-selector').click();

                    expect(pageView.router.navigate)
                        .toHaveBeenCalledWith('1/', {trigger: true});

                    expect(page.loadDiffRevision).toHaveBeenCalledWith({
                        baseCommitID: null,
                        filenamePatterns: null,
                        interdiffRevision: null,
                        page: 1,
                        revision: 1,
                        tipCommitID: null,
                    });

                    expect(page.revision.get('baseCommitID')).toBe(null);
                    expect(page.revision.get('tipCommitID')).toBe(null);

                    const diffCommitListModel = pageView._commitListView.model;
                    expect(diffCommitListModel.get('baseCommitID')).toBe(null);
                    expect(diffCommitListModel.get('tipCommitID')).toBe(null);
                });
            });
        });
    });
});
