suite('rb/diffviewer/views/DiffCommitListView', function() {
    function testRows($rows, options) {
        expect($rows.length).toEqual(options.rowOptions.length);

        /*
         * If there is an expand/collapse column, row values start at the
         * second column instead of the first.
         */
        const startIndex = options.haveExpandCollapse ? 1 : 0;

        for (let i = 0; i < $rows.length; i++) {
            const $row = $rows.eq(i).find('td');
            const $link = $row.eq(0).find('a');

            const rowOptions = options.rowOptions[i];
            const values = rowOptions.values;

            if (options.haveExpandCollapse) {
                expect($row.length).toEqual(values.length + 1);

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
                } else {
                    expect($link.find('a').length).toEqual(0);
                }
            } else {
                expect($row.length).toEqual(values.length);
            }

            for (let j = 0; j < values; j++) {
                expect($row.eq(startIndex + j).text()).toEqual(values[j]);
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
                    commit_id: 'r0',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 1',
                },
                {
                    commit_id: 'r1',
                    author_name: 'Example Author',
                    commit_message: 'Commit message 2',
                },
            ], {parse: true});

            model = new RB.DiffCommitList({
                commits,
                isInterdiff: false,
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
            expect($cols.eq(0).text()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text()).toEqual(gettext('Author'));

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
            expect($cols.length).toEqual(3);

            expect($cols.eq(0).text()).toEqual('');
            expect($cols.eq(1).text()).toEqual(gettext('Summary'));
            expect($cols.eq(2).text()).toEqual(gettext('Author'));

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
            expect($cols.eq(0).text()).toEqual(gettext('Summary'));
            expect($cols.eq(1).text()).toEqual(gettext('Author'));

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
            expect($cols.length).toEqual(3);
            expect($cols.eq(0).text()).toEqual('');
            expect($cols.eq(1).text()).toEqual(gettext('Summary'));
            expect($cols.eq(2).text()).toEqual(gettext('Author'));

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
            model.set('isInterdiff', true);
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });
            view.render();

            expect($container.find('table').length).toEqual(0);
            const $p = $container.find('p');

            expect($p.length).toEqual(1);
            expect($p.text()).toEqual(
                'Interdiff commit listings not supported.');
        });
    });

    describe('Event handlers', function() {
        let model;

        beforeEach(() => {
            let commits = new RB.DiffCommitCollection([
                {
                    commit_id: 'r0',
                    author_name: 'Example Author',
                    commit_message: 'Long commit message\n\n' +
                                    'This is a long message.\n',
                },
                {
                    commit_id: 'r1',
                    author_name: 'Example Author',
                    commit_message: 'Super long\n\nSo very long.',
                },
            ], {parse: true});

            model = new RB.DiffCommitList({
                commits,
                isInterdiff: false,
            });
        });

        it('Expand/collapse', () => {
            view = new RB.DiffCommitListView({
                model: model,
                el: $container,
            });

            view.render();

            const $table = $container.find('table');
            const $cols = $table.find('thead th');

            expect($cols.length).toEqual(3);
            expect($cols.eq(0).text()).toEqual('');
            expect($cols.eq(1).text()).toEqual(gettext('Summary'));
            expect($cols.eq(2).text()).toEqual(gettext('Author'));

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
    });
});
