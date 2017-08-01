suite('rb/pages/views/DiffViewerPageView', function() {
    var tableTemplate = _.template([
            '<div class="diff-container">',
            ' <table class="sidebyside">',
            '  <thead>',
            '   <tr class="filename-row">',
            '    <th colspan="4">',
            '     <a name="<%- fileID %>" class="file-anchor"></a>',
            '    </th>',
            '   </tr>',
            '  </thead>',
            '  <% _.each(chunks, function(chunk) { %>',
            '   <tbody class="<%- chunk.type %>">',
            '    <% _.each(chunk.lines, function(line, i) { %>',
            '     <tr line="<%- line.vNumber %>">',
            '      <th>',
            '       <% if (i === 0 && chunk.type !== "equal") { %>',
            '        <a name="<%- chunk.id %>" class="chunk-anchor"></a>',
            '       <% } %>',
            '       <%- line.leftNumber || "" %>',
            '      </th>',
            '      <td class="l"></td>',
            '      <th><%- line.rightNumber || "" %></th>',
            '      <td class="r"></td>',
            '     </tr>',
            '    <% }); %>',
            '   </tbody>',
            '  <% }); %>',
            ' </table>',
            '</div>'
        ].join('')),
        pageView;

    beforeEach(function() {
        /*
         * Disable the router so that the page doesn't change the URL on the
         * page while tests run.
         */
        spyOn(Backbone.history, 'start');

        pageView = new RB.DiffViewerPageView({
            el: $('<div/>').appendTo($testsScratch),
            model: new RB.DiffViewerPageModel({
                revision: 1,
                is_interdiff: false,
                interdiff_revision: null
            }, {parse: true}),
            reviewRequestData: {
                id: 123,
                loaded: true,
                state: RB.ReviewRequest.PENDING
            },
            editorData: {
                mutableByUser: true,
                statusMutableByUser: true
            }
        });

        /* Don't communicate with the server for page updates. */
        spyOn(pageView.reviewRequest, 'ready').andCallFake(
            function(options, context) {
                options.ready.call(context);
            });
        spyOn(pageView.reviewRequest, 'beginCheckForUpdates');
    });

    describe('Anchors', function() {
        it('Tracks all types', function() {
            pageView.$el.html(tableTemplate({
                fileID: 'file1',
                chunks: [
                    {
                        id: '1.1',
                        lines: [
                            {
                                type: 'insert',
                                vNumber: 100,
                                leftNumber: 100,
                                rightNumber: 101
                            }
                        ]
                    },
                    {
                        id: '1.2',
                        lines: [
                            {
                                type: 'equal',
                                vNumber: 101,
                                leftNumber: 101,
                                rightNumber: 101
                            }
                        ]
                    },
                    {
                        id: '1.3',
                        lines: [
                            {
                                type: 'delete',
                                vNumber: 102,
                                leftNumber: 102,
                                rightNumber: 101
                            }
                        ]
                    }
                ]
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
                pageView.$el.html([
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
                                        rightNumber: 101
                                    }
                                ]
                            },
                            {
                                id: '1.2',
                                lines: [
                                    {
                                        type: 'equal',
                                        vNumber: 101,
                                        leftNumber: 101,
                                        rightNumber: 101
                                    }
                                ]
                            }
                        ]
                    }),
                    tableTemplate({
                        fileID: 'file2',
                        chunks: []
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
                                        rightNumber: 101
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
                                        rightNumber: 101
                                    }
                                ]
                            }
                        ]
                    })
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
            var evt = $.Event('keypress');
            evt.which = c.charCodeAt(0);

            pageView.$el.trigger(evt);
        }

        function testKeys(description, funcName, keyList) {
            describe(description, function() {
                _.each(keyList, function(key) {
                    var label,
                        c;

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
});
