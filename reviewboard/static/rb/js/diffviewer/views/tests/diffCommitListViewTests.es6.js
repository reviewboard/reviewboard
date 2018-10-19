suite('rb/diffviewer/views/DiffCommitListView', function() {
    function testRows($rows, options) {
        expect($rows.length).toEqual(options.rowOptions.length);

        const linkIndex = (
            (options.haveHistory ? 1 : 0) +
            (options.haveInterCommitDiffControls ? 2 : 0)
        );

        const valueStartIndex = (
            linkIndex +
            (options.haveExpandCollapse ? 1 : 0)
        );

        for (let i = 0; i < $rows.length; i++) {
            const $row = $rows.eq(i).find('td');

            const rowOptions = options.rowOptions[i];
            const values = rowOptions.values;

            expect($row.length).toEqual(values.length + valueStartIndex);

            if (options.haveHistory) {
                expect($row.eq(0).text().trim()).toEqual(
                    rowOptions.historySymbol.trim());
            }

            if (options.haveInterCommitDiffControls) {
                const $baseSelector = $row.eq(0).find('input');
                expect($baseSelector.length).toEqual(1);
                expect($baseSelector.attr('value')).toEqual((i + 1).toString());
                expect($baseSelector.prop('checked')).toEqual(
                    !!rowOptions.baseSelected);
                expect($baseSelector.prop('disabled')).toEqual(
                    !!rowOptions.baseDisabled);

                const $tipSelector = $row.eq(1).find('input');
                expect($tipSelector.length).toEqual(1);
                expect($tipSelector.attr('value')).toEqual((i + 1).toString());
                expect($tipSelector.prop('checked')).toEqual(
                    rowOptions.tipSelected ? true : false);
                expect($tipSelector.prop('disabled')).toEqual(
                    !!rowOptions.tipDisabled);
            }

            if (options.haveExpandCollapse) {
                const $link = $row.eq(linkIndex).find('a');

                if (rowOptions.haveExpandCollapse) {
                    expect($link.length).toEqual(1);

                    const $span = $link.find('span');

                    if (rowOptions.expanded) {
                        expect($span.attr('class')).toEqual('fa fa-minus');
                        expect($span.attr('title'))
                            .toEqual(gettext('Collapse commit message.'));
                    } else {
                        expect($span.attr('class')).toEqual('fa fa-plus');
                        expect($span.attr('title'))
                            .toEqual(gettext('Expand commit message.'));
                    }
                }
            }

            for (let j = 0; j < values; j++) {
                expect($row.eq(valueStartIndex + j).text().trim()).toEqual(values[j]);
            }
        }
    }

    let view;
    let $container;

    beforeEach(function() {
        $container = $('<div class="diff-commit-list" />')
            .appendTo($testsScratch);
    });

    afterEach(function() {
        view.remove();
        view = null;
        $container = null;
    });

    describe('Render', function() {
        let model;

        beforeEach(function() {
            let commits = new RB.DiffCommitCollection([
                {
                    id: 1,
                    commit_id: 'r1',
                    parent_id: 'r0',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 1',
                },
                {
                    id: 2,
                    commit_id: 'r2',
                    parent_id: 'r1',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 2',
                },
            ], {parse: true});

            model = new RB.DiffCommitList({
                commits,
                historyDiff: new RB.CommitHistoryDiffEntryCollection(),
                isInterdiff: false,
                baseCommitID: null,
                tipCommitID: null,
            });
        });

        it('Without expand/collapse column', function() {
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(2);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: false,
                rowOptions: [
                    {values: ['Commit message 1', 'Example Author']},
                    {values: ['Commit message 2', 'Example Author']},
                ],
            });
        });

        it('With expand/collapse column', function() {
            model.get('commits').models[0].set({
                commitMessage: 'Long commit message\n\n' +
                               'This is a long message.\n',
                summary: 'Long commit message',
            });

            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(2);

            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        haveExpandCollapse: false,
                        values: ['Commit message 2', 'Example Author'],
                    },
                ],
            });
        });

        it('Updates when collection reset', function() {
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            let $table = $container.find('table');

            let $cols = $table.find('thead th');
            expect($cols.length).toEqual(2);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: false,
                rowOptions: [
                    {values: ['Commit message 1', 'Example Author']},
                    {values: ['Commit message 2', 'Example Author']},
                ],
            });

            model.get('commits').reset([
                {
                    commit_id: 'r4',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 4\n\nIt is very long',
                },
            ], {parse: true});

            $table = $container.find('table');

            $cols = $table.find('thead th');
            expect($cols.length).toEqual(2);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Commit message 4', 'Example Author'],
                    },
                ],
            });
        });

        it('Interdiff', function() {
            model.get('historyDiff').reset([
                {
                    entry_type: RB.CommitHistoryDiffEntry.REMOVED,
                    old_commit_id: 1,
                },
                {
                    entry_type: RB.CommitHistoryDiffEntry.ADDED,
                    new_commit_id: 2,
                }
            ], {parse: true});

            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(3);
            expect($cols.eq(0).text().trim()).toEqual('');
            expect($cols.eq(1).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: false,
                haveHistory: true,
                rowOptions: [
                    {
                        historySymbol: '-',
                        values: ['Commit message 1', 'Example Author'],
                    },
                    {
                        historySymbol: '+',
                        values: ['Commit message 2', 'Example Author'],
                    },
                ],
            });
        });

        it('With Inter-Commit Diff Controls', function() {
            view = new RB.DiffCommitListView({
                el: $container,
                model: model,
                showInterCommitDiffControls: true,
            });
            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(4);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        baseSelected: true,
                        values: ['Commit message 1', 'Example Author'],
                    },
                    {
                        tipSelected: true,
                        values: ['Commit message 2', 'Example Author'],
                    },
                ],
            });
        });

        it('With Inter-Commit Diff and Expand/Collapse Controls', function() {
             model.get('commits').get(1).set({
                commitMessage: 'Long commit message\n' +
                               '\nThis is a long message.\n',
                summary: 'Long commit message',
            });

            view = new RB.DiffCommitListView({
                el: $container,
                model: model,
                showInterCommitDiffControls: true,
            });

            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(4);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        baseSelected: true,
                        haveExpandCollapse: true,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        tipSelected: true,
                        values: ['Commit message 2', 'Example Author'],
                    },
                ],
            });
        });

        it('With base and tip commit IDs set', function() {
            const commits = model.get('commits');

            commits.add([
                {
                    id: 3,
                    commit_id: 'r3',
                    parent_id: 'r2',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 3',

                },
                {
                    id: 4,
                    commit_id: 'r4',
                    parent_id: 'r3',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 4',
                },
            ], {parse: true});

            model.set({
                'baseCommitID': commits.findWhere({commitID: 'r2'}).id,
                'tipCommitID': commits.findWhere({commitID: 'r3'}).id,
            });

            view = new RB.DiffCommitListView({
                el: $container,
                model: model,
                showInterCommitDiffControls: true,
            });

            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');
            expect($cols.length).toEqual(4);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        tipDisabled: true,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        tipDisabled: true,
                        values: ['Commit message 2', 'Example Author'],
                    },
                    {
                        baseSelected: true,
                        tipSelected: true,
                        values: ['Commit message 3', 'Example Author'],

                    },
                    {
                        baseDisabled: true,
                        values: ['Commit message 4', 'Example Author'],
                    },
                ],
            });
        });
    });

    describe('Event handlers', function() {
        let model;

        beforeEach(function() {
            let commits = new RB.DiffCommitCollection([
                {
                    id: 1,
                    commit_id: 'r1',
                    parent_id: 'r0',
                    author_name: 'Example Author',
                    commit_message: 'Long commit message\n\n' +
                                    'This is a long message.\n',
                },
                {
                    id: 2,
                    commit_id: 'r2',
                    parent_id: 'r1',
                    author_name: 'Example Author',
                    commit_message: 'Super long\n\nSo very long.',
                },
            ], {parse: true});

            model = new RB.DiffCommitList({
                commits,
                isInterdiff: false,
            });
        });

        it('Expand/collapse', function() {
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });

            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');

            expect($cols.length).toEqual(2);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Super long', 'Example Author'],
                    },
                ],
            });

            const $links = $table.find('a');

            // Expand first row.
            $links.eq(0).click();

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: true,
                        values: [
                            'Long commit message\n\nThis is a long message.',
                            'Example Author',
                        ],
                    },
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Super long', 'Example Author'],
                    },
                ],
            });

            // Collapse first row.
            $links.eq(0).click();

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        iconClass: 'fa-plus',
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        haveExpandCollapse: true,
                        iconClass: 'fa-plus',
                        values: ['Super long', 'Example Author'],
                    },
                ],
            });

            // Expand second row.
            $links.eq(1).click();

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        haveExpandCollapse: true,
                        expanded: true,
                        values: [
                            'Super long\n\nSo very long.',
                            'Example Author',
                        ],
                    },
                ],
            });

            // Collapse second row.
            $links.eq(1).click();

            testRows($table.find('tbody tr'), {
                haveExpandCollapse: true,
                rowOptions: [
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Long commit message', 'Example Author'],
                    },
                    {
                        haveExpandCollapse: true,
                        expanded: false,
                        values: ['Super long', 'Example Author'],
                    },
                ],
            });
        });

        it('Select base/tip', function() {
            model.get('commits').add([
                {
                    id: 3,
                    commit_id: 'r3',
                    parent_id: 'r2',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 3',

                },
                {
                    id: 4,
                    commit_id: 'r4',
                    parent_id: 'r3',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 4',
                },
            ], {parse: true});

            view = new RB.DiffCommitListView({
                el: $container,
                showInterCommitDiffControls: true,
                model: model,
            });
            view.render();

            const $baseSelectors = $container.find('.base-commit-selector');
            const $tipSelectors = $container.find('.tip-commit-selector');

            expect($baseSelectors.length).toEqual(4);
            expect($tipSelectors.length).toEqual(4);

            // Select the interval (r4, r4].
            $baseSelectors.eq(3).click();

            expect($baseSelectors.eq(0).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(1).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(2).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(3).prop('disabled')).toEqual(false);

            expect($tipSelectors.eq(0).prop('disabled')).toEqual(true);
            expect($tipSelectors.eq(1).prop('disabled')).toEqual(true);
            expect($tipSelectors.eq(2).prop('disabled')).toEqual(true);
            expect($tipSelectors.eq(3).prop('disabled')).toEqual(false);

            expect(model.get('baseCommitID')).toEqual(3);
            expect(model.get('tipCommitID')).toEqual(null);

            // Select the interval (r1, r4].
            $baseSelectors.eq(0).click();

            for (let i = 0; i < 4; i++) {
                expect($baseSelectors.eq(i).prop('disabled')).toEqual(false);
                expect($tipSelectors.eq(i).prop('disabled')).toEqual(false);
            }

            expect(model.get('baseCommitID')).toEqual(null);
            expect(model.get('tipCommitID')).toEqual(null);

            // Select the interval (r1, r1].
            $tipSelectors.eq(0).click();

            expect($baseSelectors.eq(0).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(1).prop('disabled')).toEqual(true);
            expect($baseSelectors.eq(2).prop('disabled')).toEqual(true);
            expect($baseSelectors.eq(3).prop('disabled')).toEqual(true);

            expect($tipSelectors.eq(0).prop('disabled')).toEqual(false);
            expect($tipSelectors.eq(1).prop('disabled')).toEqual(false);
            expect($tipSelectors.eq(2).prop('disabled')).toEqual(false);
            expect($tipSelectors.eq(3).prop('disabled')).toEqual(false);

            expect(model.get('baseCommitID')).toEqual(null);
            expect(model.get('tipCommitID')).toEqual(1);

            // Select the interval (r3, r3].
            $tipSelectors.eq(2).click();
            $baseSelectors.eq(2).click();

            expect($baseSelectors.eq(0).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(1).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(2).prop('disabled')).toEqual(false);
            expect($baseSelectors.eq(3).prop('disabled')).toEqual(true);

            expect($tipSelectors.eq(0).prop('disabled')).toEqual(true);
            expect($tipSelectors.eq(1).prop('disabled')).toEqual(true);
            expect($tipSelectors.eq(2).prop('disabled')).toEqual(false);
            expect($tipSelectors.eq(2).prop('disabled')).toEqual(false);

            expect(model.get('baseCommitID')).toEqual(2);
            expect(model.get('tipCommitID')).toEqual(3);
        });
    });
});
