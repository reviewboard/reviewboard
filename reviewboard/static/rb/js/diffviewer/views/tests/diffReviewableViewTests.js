describe('diffviewer/views/DiffReviewableView', function() {
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
            '<% _.each(chunks, function(chunk) { %>',
            ' <tbody class="<%= chunk.type %>">',
            '<%   for (var i = 0; i < chunk.numRows; i++) { %>',
            '  <tr line="<%= i + chunk.startRow %>">',
            '   <th></th>',
            '   <td></td>',
            '   <th></th>',
            '   <td></td>',
            '  </tr>',
            '<%   } %>',
            ' </tbody>',
            '<% }); %>',
            '</table>'
        ].join('')),
        view;

    function sendMouseEvent($el, type, target) {
        var evt = $.Event(type);
        evt.target = target;
        evt.pageX = $(target).offset().left;
        evt.pageY = $(target).offset().top;

        $el.trigger(evt);
    }

    describe('CommentRowSelector', function() {
        var selector,
            $rows;

        beforeEach(function() {
            var $container = $('<div/>').appendTo($testsScratch);

            view = new RB.DiffReviewableView({
                model: new RB.DiffReviewable(),
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

        afterEach(function() {
            view.remove();
        });

        describe('Selecting range', function() {
            var $startRow,
                startCell;

            beforeEach(function() {
                $startRow = $($rows[4]);
                startCell = $startRow[0].cells[0];

                // XXX Needed until DiffCommentBlock is restructured.
                window.gFileAnchorToId = {};
                window.gInterdiffFileAnchorToId = {};
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
                    spyOn(RB, 'DiffCommentBlock').andReturn({
                        showCommentDlg: function() {}
                    });
                });

                describe('With single line', function() {
                    var $row,
                        cell;

                    beforeEach(function() {
                        $row = $($rows[4]);
                        cell = $row[0].cells[0];
                    });

                    it('And existing comment', function() {
                        var onClick = jasmine.createSpy('onClick'),
                            $comment = $('<a class="commentflag" />')
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
                            stopImmediatePropagation: function() {}
                        });

                        expect(RB.DiffCommentBlock).not.toHaveBeenCalled();
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
                            stopImmediatePropagation: function() {}
                        });

                        expect(RB.DiffCommentBlock)
                            .toHaveBeenCalledWith($row, $row, 5, 5);

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
                        var onClick = jasmine.createSpy('onClick'),
                            $comment = $('<a class="commentflag" />')
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
                            stopImmediatePropagation: function() {}
                        });

                        expect(RB.DiffCommentBlock)
                            .toHaveBeenCalledWith($startRow, $endRow, 5, 6);

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
                            stopImmediatePropagation: function() {}
                        });

                        expect(RB.DiffCommentBlock)
                            .toHaveBeenCalledWith($startRow, $endRow, 5, 6);

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
                    var $row = $($rows[0]),
                        cell;

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
                    var $row = $($rows[0]),
                        cell;

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
});
