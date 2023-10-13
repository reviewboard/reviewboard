suite('rb/diffviewer/views/DiffCommitListView', function() {
    function testRows($rows, options) {
        expect($rows.length).toEqual(options.rowOptions.length);

        const linkIndex = (
            (options.haveHistory ? 1 : 0) +
            (options.haveInterCommitDiffControls ? 2 : 0)
        );

        const valueStartIndex = linkIndex;

        for (let i = 0; i < $rows.length; i++) {
            const $row = $rows.eq(i);
            const $cols = $row.find('td');

            const rowOptions = options.rowOptions[i];
            const values = rowOptions.values;

            expect($cols.length).toEqual(values.length + valueStartIndex);

            if (options.haveHistory) {
                expect($row[0]).toHaveClass(rowOptions.op);
            }

            if (options.haveInterCommitDiffControls) {
                const $baseSelector = $cols.eq(0).find('input');
                expect($baseSelector.length).toEqual(1);
                expect($baseSelector.attr('value')).toEqual(
                    (i + 1).toString());
                expect($baseSelector.prop('checked')).toEqual(
                    !!rowOptions.baseSelected);
                expect($baseSelector.prop('disabled')).toEqual(
                    !!rowOptions.baseDisabled);

                const $tipSelector = $cols.eq(1).find('input');
                expect($tipSelector.length).toEqual(1);
                expect($tipSelector.attr('value')).toEqual((i + 1).toString());
                expect($tipSelector.prop('checked')).toEqual(
                    rowOptions.tipSelected ? true : false);
                expect($tipSelector.prop('disabled')).toEqual(
                    !!rowOptions.tipDisabled);
            }

            for (let j = 0; j < values; j++) {
                expect($cols.eq(valueStartIndex + j).text().trim())
                    .toEqual(values[j]);
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

        it('Updates when collection reset', function() {
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            let $table = $container.find('table');

            let $cols = $table.find('thead th');
            expect($cols.length).toEqual(3);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                rowOptions: [
                    {
                        values: [
                            'Commit message 1',
                            'r1',
                            'Example Author',
                        ],
                    },
                    {
                        values: [
                            'Commit message 2',
                            'r2',
                            'Example Author',
                        ],
                    },
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
            expect($cols.length).toEqual(3);
            expect($cols.eq(0).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                rowOptions: [
                    {
                        expanded: false,
                        values: [
                            'Commit message 4',
                            'r4',
                            'Example Author',
                        ],
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
            expect($cols.length).toEqual(4);
            expect($cols.eq(0).text().trim()).toEqual('');
            expect($cols.eq(1).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveHistory: true,
                rowOptions: [
                    {
                        op: '-is-removed',
                        values: [
                            'Commit message 1',
                            'r1',
                            'Example Author',
                        ],
                    },
                    {
                        op: '-is-added',
                        values: [
                            'Commit message 2',
                            'r2',
                            'Example Author',
                        ],
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
            expect($cols.length).toEqual(5);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(4).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        baseSelected: true,
                        values: [
                            'Commit message 1',
                            'r1',
                            'Example Author',
                        ],
                    },
                    {
                        tipSelected: true,
                        values: [
                            'Commit message 2',
                            'r2',
                            'Example Author',
                        ],
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
            expect($cols.length).toEqual(5);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(4).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        baseSelected: true,
                        haveExpandCollapse: true,
                        values: [
                            'Long commit message',
                            'r1',
                            'Example Author',
                        ],
                    },
                    {
                        tipSelected: true,
                        values: [
                            'Commit message 2',
                            'r2',
                            'Example Author',
                        ],
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
            expect($cols.length).toEqual(5);
            expect($cols.eq(0).text().trim()).toEqual(gettext('First'));
            expect($cols.eq(1).text().trim()).toEqual(gettext('Last'));
            expect($cols.eq(2).text().trim()).toEqual(gettext('Summary'));
            expect($cols.eq(3).text().trim()).toEqual(gettext('ID'));
            expect($cols.eq(4).text().trim()).toEqual(gettext('Author'));

            testRows($table.find('tbody tr'), {
                haveInterCommitDiffControls: true,
                rowOptions: [
                    {
                        tipDisabled: true,
                        values: [
                            'Long commit message',
                            'r1',
                            'Example Author',
                        ],
                    },
                    {
                        tipDisabled: true,
                        values: [
                            'Commit message 2',
                            'r2',
                            'Example Author',
                        ],
                    },
                    {
                        baseSelected: true,
                        tipSelected: true,
                        values: [
                            'Commit message 3',
                            'r3',
                            'Example Author',
                        ],

                    },
                    {
                        baseDisabled: true,
                        values: [
                            'Commit message 4',
                            'r4',
                            'Example Author',
                        ],
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
