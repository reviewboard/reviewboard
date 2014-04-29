suite('rb/diffviewer/views/DiffReviewableView', function() {
    var diffTableTemplate = _.template([
            '<table class="sidebyside">',
            ' <thead>',
            '  <tr>',
            '   <th colspan="2">',
            '    <a name="1" class="file-anchor"></a> my-file.txt',
            '   </th>',
            '  </tr>',
            '  <tr>',
            '   <th class="rev">Revision 1</th>',
            '   <th class="rev">Revision 2</th>',
            '  </tr>',
            ' </thead>',
            ' <% _.each(chunks, function(chunk, index) { %>',
            '  <% if (chunk.type === "collapsed") { %>',
            '   <tbody class="diff-header">',
            '    <tr>',
            '     <th>',
            '      <a href="#" class="diff-expand-btn tests-expand-above"',
            '         data-chunk-index="<%= index %>"',
            '         data-lines-of-context="20,0"><img /></a>',
            '     </th>',
            '     <th colspan="3">',
            '      <a href="#" class="diff-expand-btn tests-expand-chunk"',
            '         data-chunk-index="<%= index %>"><img /> Expand</a>',
            '     </th>',
            '    </tr>',
            '    <tr>',
            '     <th>',
            '      <a href="#" class="diff-expand-btn tests-expand-below"',
            '         data-chunk-index="<%= index %>"',
            '         data-lines-of-context="0,20"><img /></a>',
            '     </th>',
            '     <th colspan="3">',
            '      <a href="#" class="diff-expand-btn tests-expand-header"',
            '         data-chunk-index="<%= index %>"',
            '         data-lines-of-context="0,<%= chunk.expandHeaderLines %>">',
            '       <img /> <code>Some Function</code>',
            '      </a>',
            '     </th>',
            '    </tr>',
            '   </tbody>',
            '  <% } else { %>',
            '   <tbody class="<%= chunk.type %>',
            '                 <% if (chunk.expanded) { %>loaded<% } %>',
            '                 <%= chunk.extraClass || "" %>"',
            '          id="chunk0.<%= index %>">',
            '    <% for (var i = 0; i < chunk.numRows; i++) { %>',
            '     <tr line="<%= i + chunk.startRow %>">',
            '      <th></th>',
            '      <td>',
            '       <% if (chunk.expanded && i === 0) { %>',
            '        <div class="collapse-floater">',
            '         <img class="diff-collapse-btn"',
            '              data-chunk-index="<%= index %>"',
            '              data-lines-of-context="0" />',
            '        </div>',
            '       <% } %>',
            '      </td>',
            '      <th></th>',
            '      <td></td>',
            '     </tr>',
            '    <% } %>',
            '   </tbody>',
            '  <% } %>',
            ' <% }); %>',
            '</table>'
        ].join('')),
        reviewRequest,
        $container,
        view;

    beforeEach(function() {
        $container = $('<div/>').appendTo($testsScratch);

        reviewRequest = new RB.ReviewRequest();
    });

    afterEach(function() {
        view.remove();
    });

    describe('CommentRowSelector', function() {
        var selector,
            $rows;

        beforeEach(function() {
            view = new RB.DiffReviewableView({
                model: new RB.DiffReviewable({
                    reviewRequest: reviewRequest
                }),
                el: $(diffTableTemplate({
                    chunks: [
                        {
                            type: 'equal',
                            startRow: 1,
                            numRows: 5
                        },
                        {
                            type: 'delete',
                            startRow: 6,
                            numRows: 10
                        }
                    ]
                }))
            });
            view.render().$el.appendTo($container);

            selector = view._selector;
            $rows = view.$el.find('tbody tr');
        });

        describe('Selecting range', function() {
            var $startRow,
                startCell;

            beforeEach(function() {
                $startRow = $($rows[4]);
                startCell = $startRow[0].cells[0];
            });

            it('Beginning selection', function() {
                selector._onMouseOver({
                    target: startCell
                });

                selector._onMouseDown({
                    target: startCell
                });

                expect($startRow.hasClass('selected')).toBe(true);
                expect(selector._$begin[0]).toBe($startRow[0]);
                expect(selector._$end[0]).toBe($startRow[0]);
                expect(selector._beginLineNum).toBe(5);
                expect(selector._endLineNum).toBe(5);
                expect(selector._lastSeenIndex).toBe($startRow[0].rowIndex);
            });

            describe('Adding rows to selection', function() {
                it('Above', function() {
                    var $prevRow = $($rows[3]);

                    selector._onMouseOver({
                        target: startCell
                    });

                    selector._onMouseDown({
                        target: startCell
                    });

                    selector._onMouseOver({
                        target: $prevRow[0].cells[0]
                    });

                    expect($startRow.hasClass('selected')).toBe(true);
                    expect($prevRow.hasClass('selected')).toBe(true);
                    expect(selector._$begin[0]).toBe($prevRow[0]);
                    expect(selector._$end[0]).toBe($startRow[0]);
                    expect(selector._beginLineNum).toBe(4);
                    expect(selector._endLineNum).toBe(5);
                    expect(selector._lastSeenIndex).toBe($prevRow[0].rowIndex);
                });

                it('Below', function() {
                    var $nextRow = $($rows[5]);

                    selector._onMouseOver({
                        target: startCell
                    });

                    selector._onMouseDown({
                        target: startCell
                    });

                    selector._onMouseOver({
                        target: $nextRow[0].cells[0]
                    });

                    expect($startRow.hasClass('selected')).toBe(true);
                    expect($nextRow.hasClass('selected')).toBe(true);
                    expect(selector._$begin[0]).toBe($startRow[0]);
                    expect(selector._$end[0]).toBe($nextRow[0]);
                    expect(selector._beginLineNum).toBe(5);
                    expect(selector._endLineNum).toBe(6);
                    expect(selector._lastSeenIndex).toBe($nextRow[0].rowIndex);
                });

                it('Rows inbetween two events', function() {
                    var $laterRow = $($rows[7]);

                    selector._onMouseOver({
                        target: startCell
                    });

                    selector._onMouseDown({
                        target: startCell
                    });

                    selector._onMouseOver({
                        target: $laterRow[0].cells[0]
                    });

                    expect($($rows[4]).hasClass('selected')).toBe(true);
                    expect($($rows[5]).hasClass('selected')).toBe(true);
                    expect($($rows[6]).hasClass('selected')).toBe(true);
                    expect($($rows[7]).hasClass('selected')).toBe(true);
                    expect(selector._$begin[0]).toBe($startRow[0]);
                    expect(selector._$end[0]).toBe($laterRow[0]);
                    expect(selector._beginLineNum).toBe(5);
                    expect(selector._endLineNum).toBe(8);
                    expect(selector._lastSeenIndex).toBe($laterRow[0].rowIndex);
                });
            });

            describe('Removing rows from selection', function() {
                it('Above', function() {
                    var $prevRow = $($rows[3]),
                        prevCell = $prevRow[0].cells[0];

                    selector._onMouseOver({
                        target: startCell
                    });

                    selector._onMouseDown({
                        target: startCell
                    });

                    selector._onMouseOver({
                        target: prevCell
                    });

                    selector._onMouseOut({
                        relatedTarget: startCell,
                        target: prevCell
                    });

                    selector._onMouseOver({
                        target: startCell
                    });

                    expect($startRow.hasClass('selected')).toBe(true);
                    expect($prevRow.hasClass('selected')).toBe(false);
                    expect(selector._$begin[0]).toBe($startRow[0]);
                    expect(selector._$end[0]).toBe($startRow[0]);
                    expect(selector._beginLineNum).toBe(5);
                    expect(selector._endLineNum).toBe(5);
                    expect(selector._lastSeenIndex).toBe($startRow[0].rowIndex);
                });

                it('Below', function() {
                    var $nextRow = $($rows[5]),
                        nextCell = $nextRow[0].cells[0];

                    selector._onMouseOver({
                        target: startCell
                    });

                    selector._onMouseDown({
                        target: startCell
                    });

                    selector._onMouseOver({
                        target: nextCell
                    });

                    selector._onMouseOut({
                        relatedTarget: startCell,
                        target: nextCell
                    });

                    selector._onMouseOver({
                        target: startCell
                    });

                    expect($startRow.hasClass('selected')).toBe(true);
                    expect($nextRow.hasClass('selected')).toBe(false);
                    expect(selector._$begin[0]).toBe($startRow[0]);
                    expect(selector._$end[0]).toBe($startRow[0]);
                    expect(selector._beginLineNum).toBe(5);
                    expect(selector._endLineNum).toBe(5);
                    expect(selector._lastSeenIndex).toBe($startRow[0].rowIndex);
                });
            });

            describe('Finishing selection', function() {
                beforeEach(function() {
                    spyOn(view, 'createAndEditCommentBlock');
                });

                describe('With single line', function() {
                    var $row,
                        cell;

                    beforeEach(function() {
                        $row = $($rows[4]);
                        cell = $row[0].cells[0];
                    });

                    it('And existing comment', function() {
                        var onClick = jasmine.createSpy('onClick');

                        $('<a class="commentflag" />')
                            .click(onClick)
                            .appendTo(cell);

                        selector._onMouseOver({
                            target: cell
                        });

                        selector._onMouseDown({
                            target: cell
                        });

                        selector._onMouseUp({
                            target: cell,
                            stopImmediatePropagation: function() {},
                            preventDefault: function() {}
                        });

                        expect(view.createAndEditCommentBlock)
                            .not.toHaveBeenCalled();
                        expect(onClick).toHaveBeenCalled();

                        expect($row.hasClass('selected')).toBe(false);
                        expect(selector._$begin).toBe(null);
                        expect(selector._$end).toBe(null);
                        expect(selector._beginLineNum).toBe(0);
                        expect(selector._endLineNum).toBe(0);
                        expect(selector._lastSeenIndex).toBe(0);
                    });

                    it('And no existing comment', function() {
                        selector._onMouseOver({
                            target: cell
                        });

                        selector._onMouseDown({
                            target: cell
                        });

                        selector._onMouseUp({
                            target: cell,
                            stopImmediatePropagation: function() {},
                            preventDefault: function() {}
                        });

                        expect(view.createAndEditCommentBlock)
                            .toHaveBeenCalledWith({
                                $beginRow: $row,
                                $endRow: $row,
                                beginLineNum: 5,
                                endLineNum: 5
                            });

                        expect($row.hasClass('selected')).toBe(false);
                        expect(selector._$begin).toBe(null);
                        expect(selector._$end).toBe(null);
                        expect(selector._beginLineNum).toBe(0);
                        expect(selector._endLineNum).toBe(0);
                        expect(selector._lastSeenIndex).toBe(0);
                    });
                });

                describe('With multiple lines', function() {
                    var $startRow,
                        $endRow,
                        startCell,
                        endCell;

                    beforeEach(function() {
                        $startRow = $($rows[4]);
                        $endRow = $($rows[5]);
                        startCell = $startRow[0].cells[0];
                        endCell = $endRow[0].cells[0];
                    });

                    xit('And existing comment', function() {
                        var onClick = jasmine.createSpy('onClick');

                        $('<a class="commentflag" />')
                            .click(onClick)
                            .appendTo(cell);

                        selector._onMouseOver({
                            target: startCell
                        });

                        selector._onMouseDown({
                            target: startCell
                        });

                        selector._onMouseOver({
                            target: endCell
                        });

                        expect(selector._$begin[0]).toBe($startRow[0]);
                        expect(selector._$end[0]).toBe($endRow[0]);

                        /* Copy these so we can directly compare. */
                        $startRow = selector._$begin;
                        $endRow = selector._$end;

                        selector._onMouseUp({
                            target: endCell,
                            stopImmediatePropagation: function() {},
                            preventDefault: function() {}
                        });

                        expect(view.createAndEditCommentBlock)
                            .toHaveBeenCalledWith({
                                $beginRow: $startRow,
                                $endRow: $endRow,
                                beginLineNum: 5,
                                endLineNum: 6
                            });

                        expect(onClick).not.toHaveBeenCalled();
                        expect($startRow.hasClass('selected')).toBe(false);
                        expect($endRow.hasClass('selected')).toBe(false);
                        expect(selector._$begin).toBe(null);
                        expect(selector._$end).toBe(null);
                        expect(selector._beginLineNum).toBe(0);
                        expect(selector._endLineNum).toBe(0);
                        expect(selector._lastSeenIndex).toBe(0);
                    });

                    it('And no existing comment', function() {
                        selector._onMouseOver({
                            target: startCell
                        });

                        selector._onMouseDown({
                            target: startCell
                        });

                        selector._onMouseOver({
                            target: endCell
                        });

                        expect(selector._$begin[0]).toBe($startRow[0]);
                        expect(selector._$end[0]).toBe($endRow[0]);

                        /* Copy these so we can directly compare. */
                        $startRow = selector._$begin;
                        $endRow = selector._$end;

                        selector._onMouseUp({
                            target: endCell,
                            stopImmediatePropagation: function() {},
                            preventDefault: function() {}
                        });

                        expect(view.createAndEditCommentBlock)
                            .toHaveBeenCalledWith({
                                $beginRow: $startRow,
                                $endRow: $endRow,
                                beginLineNum: 5,
                                endLineNum: 6
                            });

                        expect($startRow.hasClass('selected')).toBe(false);
                        expect($endRow.hasClass('selected')).toBe(false);
                        expect(selector._$begin).toBe(null);
                        expect(selector._$end).toBe(null);
                        expect(selector._beginLineNum).toBe(0);
                        expect(selector._endLineNum).toBe(0);
                        expect(selector._lastSeenIndex).toBe(0);
                    });
                });
            });
        });

        describe('Hovering', function() {
            describe('Over line', function() {
                var $row,
                    cell;

                beforeEach(function() {
                    $row = $($rows[4]);
                });

                it('Contents cell', function() {
                    cell = $row[0].cells[1];

                    selector._onMouseOver({
                        target: cell
                    });

                    expect($row.hasClass('selected')).toBe(false);
                    expect(selector._$ghostCommentFlag.css('display'))
                        .toBe('none');
                });

                describe('Line number cell', function() {
                    beforeEach(function() {
                        cell = $row[0].cells[0];
                    });

                    it('With existing comment on row', function() {
                        $(cell).append('<a class="commentflag" />');
                        selector._onMouseOver({
                            target: cell
                        });

                        expect($row.hasClass('selected')).toBe(true);
                        expect(selector._$ghostCommentFlag.css('display'))
                            .toBe('none');
                    });

                    it('With no column flag', function() {
                        selector._onMouseOver({
                            target: cell
                        });

                        expect($row.hasClass('selected')).toBe(true);
                        expect(selector._$ghostCommentFlag.css('display'))
                            .not.toBe('none');
                    });
                });
            });

            describe('Out of line', function() {
                it('Contents cell', function() {
                    var $row = $($rows[0]);

                    selector._onMouseOver({
                        target: $row[0].cells[0]
                    });

                    expect(selector._$ghostCommentFlag.css('display'))
                        .not.toBe('none');

                    selector._onMouseOut({
                        target: $row[0].cells[0]
                    });

                    expect(selector._$ghostCommentFlag.css('display'))
                        .toBe('none');
                });

                it('Line number cell', function() {
                    var $row = $($rows[0]);

                    selector._onMouseOver({
                        target: $row[0].cells[0]
                    });

                    expect(selector._$ghostCommentFlag.css('display'))
                        .not.toBe('none');
                    expect($row.hasClass('selected')).toBe(true);

                    selector._onMouseOut({
                        target: $row[0].cells[0]
                    });

                    expect(selector._$ghostCommentFlag.css('display'))
                        .toBe('none');
                    expect($row.hasClass('selected')).toBe(false);
                });
            });
        });
    });

    describe('Incremental expansion', function() {
        var model;

        beforeEach(function() {
            model = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileIndex: 1,
                fileDiffID: 10,
                revision: 1
            });
        });

        describe('Expanding', function() {
            beforeEach(function() {
                view = new RB.DiffReviewableView({
                    model: model,
                    el: $(diffTableTemplate({
                        chunks: [
                            {
                                type: 'equal',
                                startRow: 1,
                                numRows: 5
                            },
                            {
                                type: 'collapsed',
                                expandHeaderLines: 7
                            },
                            {
                                type: 'delete',
                                startRow: 10,
                                numRows: 5
                            }
                        ]
                    }))
                });
                view.render().$el.appendTo($container);
            });

            describe('Fetching fragment', function() {
                beforeEach(function() {
                    spyOn(model, 'getRenderedDiffFragment');
                });

                it('Full chunk', function() {
                    var options;

                    view.$('.tests-expand-chunk').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    options = model.getRenderedDiffFragment.calls[0].args[0];
                    expect(options.chunkIndex).toBe(1);
                    expect(options.linesOfContext).toBe(undefined);
                });

                it('+20 above', function() {
                    var options;

                    view.$('.tests-expand-above').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    options = model.getRenderedDiffFragment.calls[0].args[0];
                    expect(options.chunkIndex).toBe(1);
                    expect(options.linesOfContext).toBe('20,0');
                });

                it('+20 below', function() {
                    var options;

                    view.$('.tests-expand-below').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    options = model.getRenderedDiffFragment.calls[0].args[0];
                    expect(options.chunkIndex).toBe(1);
                    expect(options.linesOfContext).toBe('0,20');
                });

                it('Function/class', function() {
                    var options;

                    view.$('.tests-expand-header').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    options = model.getRenderedDiffFragment.calls[0].args[0];
                    expect(options.chunkIndex).toBe(1);
                    expect(options.linesOfContext).toBe('0,7');
                });
            });

            describe('Injecting HTML', function() {
                it('Whole chunk', function() {
                    var $tbodies;

                    spyOn(model, 'getRenderedDiffFragment')
                        .andCallFake(function(options, callbacks, context) {
                            callbacks.success.call(context, [
                                '<tbody class="equal tests-new-chunk">',
                                ' <tr line="6">',
                                '  <th></th>',
                                '  <td>',
                                '   <div class="collapse-floater">',
                                '    <img class="diff-collapse-btn"',
                                '         data-chunk-index="1"',
                                '         data-lines-of-context="0" />',
                                '   </div>',
                                '  </td>',
                                '  <th></th>',
                                '  <td></td>',
                                ' </tr>',
                                '</tbody>'
                            ].join(''));
                        });
                    spyOn(view, 'trigger').andCallThrough();

                    view.$('.tests-expand-chunk').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    $tbodies = view.$('tbody');
                    expect($tbodies.length).toBe(3);
                    expect($($tbodies[0]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('tests-new-chunk'))
                        .toBe(true);
                    expect($($tbodies[2]).hasClass('delete')).toBe(true);
                    expect(view._$collapseButtons.length).toBe(1);

                    expect(view.trigger).toHaveBeenCalledWith(
                        'chunkExpansionChanged');
                });

                it('Merging adjacent expanded chunks', function() {
                    var $tbodies;

                    spyOn(model, 'getRenderedDiffFragment')
                        .andCallFake(function(options, callbacks, context) {
                            callbacks.success.call(context, [
                                '<tbody class="equal tests-new-chunk">',
                                ' <tr line="6">',
                                '  <th></th>',
                                '  <td>',
                                '   <div class="collapse-floater">',
                                '    <img class="diff-collapse-btn"',
                                '         data-chunk-index="1"',
                                '         data-lines-of-context="0" />',
                                '   </div>',
                                '  </td>',
                                '  <th></th>',
                                '  <td></td>',
                                ' </tr>',
                                '</tbody>'
                            ].join(''));
                        });
                    spyOn(view, 'trigger').andCallThrough();

                    /*
                     * Simulate having a couple nearby partially expanded
                     * chunks. These should end up being removed when
                     * expanding the chunk.
                     */
                    $('<tbody class="equal loaded"/>')
                        .append($('<img class="diff-collapse-btn" />'))
                        .insertAfter(view.$('tbody')[1])
                        .clone().insertBefore(view.$('tbody')[1]);

                    expect(view.$('tbody').length).toBe(5);

                    view.$('.tests-expand-chunk').click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    $tbodies = view.$('tbody');
                    expect($tbodies.length).toBe(3);
                    expect($($tbodies[0]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('tests-new-chunk'))
                        .toBe(true);
                    expect($($tbodies[2]).hasClass('delete')).toBe(true);
                    expect(view._$collapseButtons.length).toBe(1);

                    expect(view.trigger).toHaveBeenCalledWith(
                        'chunkExpansionChanged');
                });
            });
        });

        describe('Collapsing', function() {
            var $collapseButton;

            beforeEach(function() {
                view = new RB.DiffReviewableView({
                    model: model,
                    el: $(diffTableTemplate({
                        chunks: [
                            {
                                type: 'equal',
                                startRow: 1,
                                numRows: 5
                            },
                            {
                                type: 'equal',
                                expanded: true,
                                startRow: 6,
                                numRows: 2
                            },
                            {
                                type: 'delete',
                                startRow: 10,
                                numRows: 5
                            }
                        ]
                    }))
                });
                view.render().$el.appendTo($container);

                $collapseButton = view.$('.diff-collapse-btn');
            });

            it('Fetching fragment', function() {
                var options;

                spyOn(model, 'getRenderedDiffFragment');

                $collapseButton.click();

                expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                options = model.getRenderedDiffFragment.calls[0].args[0];
                expect(options.chunkIndex).toBe(1);
                expect(options.linesOfContext).toBe(0);
            });

            describe('Injecting HTML', function() {
                it('Single expanded chunk', function() {
                    var $tbodies;

                    spyOn(model, 'getRenderedDiffFragment')
                        .andCallFake(function(options, callbacks, context) {
                            callbacks.success.call(context, [
                                '<tbody class="equal tests-new-chunk">',
                                ' <tr line="6">',
                                '  <th></th>',
                                '  <td></td>',
                                '  <th></th>',
                                '  <td></td>',
                                ' </tr>',
                                '</tbody>'
                            ].join(''));
                        });
                    spyOn(view, 'trigger').andCallThrough();

                    $collapseButton.click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    $tbodies = view.$('tbody');
                    expect($tbodies.length).toBe(3);
                    expect($($tbodies[0]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('tests-new-chunk'))
                        .toBe(true);
                    expect($($tbodies[2]).hasClass('delete')).toBe(true);
                    expect(view._$collapseButtons.length).toBe(0);

                    expect(view.trigger).toHaveBeenCalledWith(
                        'chunkExpansionChanged');
                });

                it('Merging adjacent expanded chunks', function() {
                    var $tbodies;

                    spyOn(model, 'getRenderedDiffFragment')
                        .andCallFake(function(options, callbacks, context) {
                            callbacks.success.call(context, [
                                '<tbody class="equal tests-new-chunk">',
                                ' <tr line="6">',
                                '  <th></th>',
                                '  <td></td>',
                                '  <th></th>',
                                '  <td></td>',
                                ' </tr>',
                                '</tbody>'
                            ].join(''));
                        });
                    spyOn(view, 'trigger').andCallThrough();

                    /*
                     * Simulate having a couple nearby partially expanded
                     * chunks. These should end up being removed when
                     * expanding the chunk.
                     */
                    $('<tbody class="equal loaded"/>')
                        .append($('<img class="diff-collapse-btn" />'))
                        .insertAfter(view.$('tbody')[1])
                        .clone().insertBefore(view.$('tbody')[1]);

                    $collapseButton.click();

                    expect(model.getRenderedDiffFragment).toHaveBeenCalled();

                    $tbodies = view.$('tbody');
                    expect($tbodies.length).toBe(3);
                    expect($($tbodies[0]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('equal')).toBe(true);
                    expect($($tbodies[1]).hasClass('tests-new-chunk'))
                        .toBe(true);
                    expect($($tbodies[2]).hasClass('delete')).toBe(true);
                    expect(view._$collapseButtons.length).toBe(0);

                    expect(view.trigger).toHaveBeenCalledWith(
                        'chunkExpansionChanged');
                });
            });
        });
    });

    describe('Comment flags', function() {
        describe('Placing visible comments', function() {
            var expandedDiffFragmentHTML = [
                    '<tbody class="equal tests-new-chunk">',
                    ' <tr line="11">',
                    '  <th></th>',
                    '  <td>',
                    '   <div class="collapse-floater">',
                    '    <img class="diff-collapse-btn"',
                    '         data-chunk-index="1"',
                    '         data-lines-of-context="0" />',
                    '   </div>',
                    '  </td>',
                    '  <th></th>',
                    '  <td></td>',
                    ' </tr>',
                    '</tbody>'
                ].join(''),
                $commentFlags,
                $rows,
                diffFragmentHTML;

            beforeEach(function() {
                view = new RB.DiffReviewableView({
                    model: new RB.DiffReviewable({
                        reviewRequest: reviewRequest,
                        serializedCommentBlocks: [
                            {
                                linenum: 2,
                                num_lines: 2,
                                comments: [{
                                    issue_opened: false,
                                    review_id: 1,
                                    localdraft: false,
                                    text: 'Comment 1',
                                    comment_id: 1,
                                    line: 2
                                }]
                            },
                            {
                                linenum: 4,
                                num_lines: 1,
                                comments: [
                                    {
                                        issue_opened: false,
                                        review_id: 1,
                                        localdraft: false,
                                        text: 'Comment 2',
                                        comment_id: 1,
                                        line: 4
                                    },
                                    {
                                        issue_opened: false,
                                        review_id: 1,
                                        localdraft: false,
                                        text: 'Comment 3',
                                        comment_id: 1,
                                        line: 4
                                    }
                                ]
                            },
                            {
                                /* This is in the collapsed area. */
                                linenum: 11,
                                num_lines: 1,
                                comments: [{
                                    issue_opened: false,
                                    review_id: 1,
                                    localdraft: false,
                                    text: 'Comment 4',
                                    comment_id: 1,
                                    line: 12
                                }]
                            }
                        ]
                    }),
                    el: $(diffTableTemplate({
                        chunks: [
                            {
                                type: 'insert',
                                startRow: 1,
                                numRows: 10
                            },
                            {
                                type: 'collapsed',
                                expandHeaderLines: 7
                            }
                        ]
                    }))
                });
                view.render().$el.appendTo($container);

                diffFragmentHTML = expandedDiffFragmentHTML;

                spyOn(view.model, 'getRenderedDiffFragment')
                    .andCallFake(function(options, callbacks, context) {
                        callbacks.success.call(context, diffFragmentHTML);
                    });

                $commentFlags = view.$('.commentflag');
                $rows = view.$el.find('tbody tr');
            });

            it('On initial render', function() {
                var $commentFlag;

                expect($commentFlags.length).toBe(2);
                expect($($commentFlags[0]).find('.commentflag-count').text())
                    .toBe('1');
                expect($($commentFlags[1]).find('.commentflag-count').text())
                    .toBe('2');

                $commentFlag = $($rows[1]).find('.commentflag');
                expect($commentFlag.length).toBe(1);
                expect($commentFlag[0]).toBe($commentFlags[0]);
                expect($commentFlag.parents('tr').attr('line')).toBe('2');

                $commentFlag = $($rows[3]).find('.commentflag');
                expect($commentFlag.length).toBe(1);
                expect($commentFlag[0]).toBe($commentFlags[1]);
                expect($commentFlag.parents('tr').attr('line')).toBe('4');
            });

            it('On chunk expand', function() {
                expect($commentFlags.length).toBe(2);

                view.$('.tests-expand-chunk').click();

                $commentFlags = view.$('.commentflag');
                $rows = view.$el.find('tbody tr');

                expect($commentFlags.length).toBe(3);
                expect($($commentFlags[2]).find('.commentflag-count').text())
                    .toBe('1');

                $commentFlag = $($rows[10]).find('.commentflag');
                expect($commentFlag.length).toBe(1);
                expect($commentFlag[0]).toBe($commentFlags[2]);
                expect($commentFlag.parents('tr').attr('line')).toBe('11');
            });

            it('On chunk re-expand (after collapsing)', function() {
                var collapsedDiffFragmentHTML = [
                    '<tbody class="diff-header">',
                    $(view.$('tbody')[1]).html(),
                    '</tbody>'
                ].join('');

                expect($commentFlags.length).toBe(2);

                view.$('.tests-expand-chunk').click();
                expect(view.$('.commentflag').length).toBe(3);

                diffFragmentHTML = collapsedDiffFragmentHTML;
                view.$('.diff-collapse-btn').click();
                expect(view.$('.commentflag').length).toBe(2);

                diffFragmentHTML = expandedDiffFragmentHTML;
                view.$('.tests-expand-chunk').click();
                expect(view.$('.commentflag').length).toBe(3);

                $commentFlags = view.$('.commentflag');
                $rows = view.$el.find('tbody tr');

                expect($commentFlags.length).toBe(3);
                expect($($commentFlags[2]).find('.commentflag-count').text())
                    .toBe('1');

                $commentFlag = $($rows[10]).find('.commentflag');
                expect($commentFlag.length).toBe(1);
                expect($commentFlag[0]).toBe($commentFlags[2]);
                expect($commentFlag.parents('tr').attr('line')).toBe('11');
            });
        });
    });

    describe('Methods', function() {
        describe('toggleWhitespaceOnlyChunks', function() {
            beforeEach(function() {
                view = new RB.DiffReviewableView({
                    model: new RB.DiffReviewable({
                        reviewRequest: reviewRequest
                    }),
                    el: $(diffTableTemplate({
                        chunks: [
                            {
                                type: 'replace',
                                startRow: 1,
                                numRows: 5,
                                extraClass: 'whitespace-chunk'
                            }
                        ]
                    }))
                });
                view.render().$el.appendTo($container);
            });

            describe('Toggle on', function() {
                it('Chunk classes', function() {
                    var $tbodies,
                        $tbody,
                        $children;

                    view.toggleWhitespaceOnlyChunks();

                    $tbodies = view.$('tbody');
                    $tbody = $($tbodies[0]);
                    $children = $tbody.children();

                    expect($tbody.hasClass('replace')).toBe(false);
                    expect($($children[0]).hasClass('first')).toBe(true);
                    expect($($children[$children.length - 1]).hasClass('last'))
                        .toBe(true);
                });

                it('chunkDimmed event triggered', function() {
                    spyOn(view, 'trigger');

                    view.toggleWhitespaceOnlyChunks();

                    expect(view.trigger)
                        .toHaveBeenCalledWith('chunkDimmed', '0.0');
                });

                it('Whitespace-only file classes', function() {
                    var $tbodies = view.$el.children('tbody'),
                        $whitespaceChunk = $('<tbody/>')
                            .addClass('whitespace-file')
                            .hide()
                            .appendTo(view.$el);

                    expect($whitespaceChunk.is(':visible')).toBe(false);
                    expect($tbodies.is(':visible')).toBe(true);

                    view.toggleWhitespaceOnlyChunks();

                    expect($whitespaceChunk.is(':visible')).toBe(true);
                    expect($tbodies.is(':visible')).toBe(false);
                });
            });

            describe('Toggle off', function() {
                it('Chunk classes', function() {
                    var $tbodies,
                        $tbody,
                        $children;

                    view.toggleWhitespaceOnlyChunks();
                    view.toggleWhitespaceOnlyChunks();

                    $tbodies = view.$('tbody');
                    $tbody = $($tbodies[0]);
                    $children = $tbody.children();

                    expect($tbody.hasClass('replace')).toBe(true);
                    expect($($children[0]).hasClass('first')).toBe(false);
                    expect($($children[$children.length - 1]).hasClass('last'))
                        .toBe(false);
                });

                it('chunkDimmed event triggered', function() {
                    view.toggleWhitespaceOnlyChunks();

                    spyOn(view, 'trigger');

                    view.toggleWhitespaceOnlyChunks();

                    expect(view.trigger)
                        .toHaveBeenCalledWith('chunkUndimmed', '0.0');
                });

                it('Whitespace-only file classes', function() {
                    var $tbodies = view.$el.children('tbody'),
                        $whitespaceChunk = $('<tbody/>')
                            .addClass('whitespace-file')
                            .hide()
                            .appendTo(view.$el);

                    expect($whitespaceChunk.is(':visible')).toBe(false);
                    expect($tbodies.is(':visible')).toBe(true);

                    view.toggleWhitespaceOnlyChunks();
                    view.toggleWhitespaceOnlyChunks();

                    expect($whitespaceChunk.is(':visible')).toBe(false);
                    expect($tbodies.is(':visible')).toBe(true);
                });
            });
        });
    });
});
