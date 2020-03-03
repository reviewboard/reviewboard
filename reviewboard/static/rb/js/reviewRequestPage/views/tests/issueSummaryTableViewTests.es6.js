suite('rb/reviewRequestPage/views/IssueSummaryTable', function() {
    const issueSummaryTableTemplate = _.template(dedent`
        <div>
         <div class="rb-c-review-request-field-tabular
                     rb-c-issue-summary-table">
          <header class="rb-c-review-request-field-tabular__header">
           <div class="rb-c-review-request-field-tabular__filters">
            <select class="rb-c-issue-summary-table__reviewer-filter">
             <option value="all"></option>
            </select>
           </div>
           <ul class="rb-c-tabs">
            <li class="rb-c-tabs__tab -is-active" data-issue-state="open">
             <label class="rb-c-tabs__tab-label">
              <span id="open-counter"
                    class="rb-c-issue-summary-table__counter">2</span>
             </label>
            </li>
            <li class="rb-c-tabs__tab" data-issue-state="verifying">
             <label class="rb-c-tabs__tab-label">
              <span id="verifying-counter"
                    class="rb-c-issue-summary-table__counter">3</span>
             </label>
            </li>
            <li class="rb-c-tabs__tab" data-issue-state="resolved">
             <label class="rb-c-tabs__tab-label">
              <span id="resolved-counter"
                    class="rb-c-issue-summary-table__counter">3</span>
             </label>
            </li>
            <li class="rb-c-tabs__tab" data-issue-state="dropped">
             <label class="rb-c-tabs__tab-label">
              <span id="dropped-counter"
                    class="rb-c-issue-summary-table__counter">1</span>
             </label>
            </li>
            <li class="rb-c-tabs__tab" data-issue-state="all">
             <label class="rb-c-tabs__tab-label">
              <span id="total-counter"
                    class="rb-c-issue-summary-table__counter">6</span>
             </label>
            </li>
           </ul>
          </header>
          <table class="rb-c-review-request-field-tabular__data">
           <thead>
            <tr>
             <th class="-is-sortable"></th>
             <th class="-is-sortable"></th>
             <th class="-is-sortable"></th>
            </tr>
           </thead>
           <tbody>
            <tr class="-is-resolved -is-hidden"
                data-issue-id="1"
                data-reviewer="user1"
                data-comment-type="diff"
                data-comment-href="#comment1">
             <td>
              <span class="rb-icon rb-icon-issue-resolved"></span>
              <p>Resolved comment 1</p>
             </td>
             <td>user1</td>
             <td>
              <time class="timesince" datetime="2017-02-01T20:30:00-07:00">
               February 1, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-resolved -is-hidden"
                data-issue-id="2"
                data-reviewer="user2"
                data-comment-type="diff"
                data-comment-href="#comment2">
             <td>
              <span class="rb-icon rb-icon-issue-resolved"></span>
              <p>Resolved comment 2</p>
             </td>
             <td>user2</td>
             <td>
              <time class="timesince" datetime="2017-02-02T20:30:00-07:00">
               February 2, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-resolved -is-hidden"
                data-issue-id="3"
                data-reviewer="user3"
                data-comment-type="diff"
                data-comment-href="#comment3">
             <td>
              <span class="rb-icon rb-icon-issue-resolved"></span>
              <p>Resolved comment 3</p>
             </td>
             <td>user3</td>
             <td>
              <time class="timesince" datetime="2017-02-03T20:30:00-07:00">
               February 3, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-open"
                data-issue-id="4"
                data-reviewer="user1"
                data-comment-type="diff"
                data-comment-href="#comment4">
             <td>
              <span class="rb-icon rb-icon-issue-open"></span>
              <p>Open comment 4</p>
             </td>
             <td>user1</td>
             <td>
              <time class="timesince" datetime="2017-02-01T20:30:00-07:00">
               February 1, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-open"
                data-issue-id="5"
                data-reviewer="user2"
                data-comment-type="diff"
                data-comment-href="#comment5">
             <td>
              <span class="rb-icon rb-icon-issue-open"></span>
              <p>Open comment 5</p>
             </td>
             <td>user2</td>
             <td>
              <time class="timesince" datetime="2017-02-02T20:30:00-07:00">
               February 2, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-dropped -is-hidden"
                data-issue-id="6"
                data-reviewer="user1"
                data-comment-type="diff"
                data-comment-href="#comment6">
             <td>
              <span class="rb-icon rb-icon-issue-dropped"></span>
              <p>Dropped comment 6</p>
             </td>
             <td>user1</td>
             <td>
              <time class="timesince" datetime="2017-02-01T20:30:00-07:00">
               February 1, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-verifying-dropped -is-hidden"
                data-issue-id="7"
                data-reviewer="user3"
                data-comment-type="diff"
                data-comment-href="#comment7">
             <td>
              <span class="rb-icon rb-icon-issue-dropped"></span>
              <p>Verifying comment 7</p>
             </td>
             <td>user3</td>
             <td>
              <time class="timesince" datetime="2017-02-03T18:30:00-07:00">
               February 3, 2017, 6:30 p.m.
              </time>
             </td>
            </tr>
            <tr class="-is-verifying-resolved -is-hidden"
                data-issue-id="8"
                data-reviewer="user2"
                data-comment-type="diff"
                data-comment-href="#comment8">
             <td>
              <span class="rb-icon rb-icon-issue-dropped"></span>
              <p>Verifying comment 8 - resolved</p>
             </td>
             <td>user2</td>
             <td>
              <time class="timesince" datetime="2017-02-04T20:30:00-07:00">
               February 4, 2017, 8:30 p.m.
              </time>
             </td>
            </tr>
           </tbody>
          </table>
         </div>
        </div>
    `);
    const TAB_SEL = '.rb-c-tabs__tab';
    const NO_ISSUES_SEL = '.rb-c-issue-summary-table__no-issues';
    const ISSUE_ROW_SEL = `tbody tr:not(${NO_ISSUES_SEL})`;
    const DESCRIPTION_HEADER_SEL = 'th:nth-child(1)';
    const REVIEWER_HEADER_SEL = 'th:nth-child(2)';
    const LAST_UPDATED_HEADER_SEL = 'th:nth-child(3)';
    const LAST_UPDATED_CELL_SEL = 'td:nth-child(3)';
    let view;

    function getTab(state) {
        return view.$(`${TAB_SEL}[data-issue-state="${state}"]`);
    }

    beforeEach(function() {
        view = new RB.ReviewRequestPage.IssueSummaryTableView({
            el: $(issueSummaryTableTemplate()),
            model: new RB.CommentIssueManager(),
        });
        view.$el.appendTo($testsScratch);
    });

    describe('render', function() {
        it('Initial state', function() {
            view.render();

            expect(view.statusFilterState).toBe('open');
            expect(view.reviewerFilterState).toBe('all');
            expect(view.reviewerToSelectorMap).toEqual({
                all: '',
                user1: '[data-reviewer="user1"]',
                user2: '[data-reviewer="user2"]',
                user3: '[data-reviewer="user3"]',
            });

            const $reviewers = view._$reviewerFilter.children();
            expect($reviewers.length).toBe(4);
            expect($reviewers.eq(0).val()).toBe('all');
            expect($reviewers.eq(1).val()).toBe('user1');
            expect($reviewers.eq(2).val()).toBe('user2');
            expect($reviewers.eq(3).val()).toBe('user3');
        });

        it('With existing state', function() {
            view.render();

            view.statusFilterState = 'dropped';
            view.reviewerFilterState = 'user1';

            /* Fully replace the element, like when an update is applied. */
            const $oldEl = view.$el;
            view.setElement($(issueSummaryTableTemplate()));
            $oldEl.replaceWith(view.$el);
            view.render();

            expect(view.statusFilterState).toBe('dropped');
            expect(view.reviewerFilterState).toBe('user1');
            expect(view.reviewerToSelectorMap).toEqual({
                all: '',
                user1: '[data-reviewer="user1"]',
                user2: '[data-reviewer="user2"]',
                user3: '[data-reviewer="user3"]',
            });

            const $activeTab = view.$('.rb-c-tabs__tab.-is-active');
            expect($activeTab.length).toBe(1);
            expect($activeTab.data('issue-state')).toBe('dropped');
            expect($activeTab[0]).toBe(view._$currentTab[0]);

            const $reviewer = view.$(
                '.rb-c-issue-summary-table__reviewer-filter');
            expect($reviewer.length).toBe(1);
            expect($reviewer[0]).toBe(view._$reviewerFilter[0]);
            expect($reviewer.val()).toBe('user1');

            const $issues = view.$el.find(ISSUE_ROW_SEL).not('.-is-hidden');
            expect($issues.length).toBe(1);

            const $issue = $issues.eq(0);
            expect($issue.hasClass('-is-dropped')).toBe(true);
            expect($issue.data('reviewer')).toBe('user1');
        });
    });

    describe('Filters', function() {
        describe('Reviewer filter', function() {
            describe('To all', function() {
                it('With issues', function() {
                    view.render();

                    view._$reviewerFilter.val('user1');
                    view._$reviewerFilter.trigger('change');

                    view._$reviewerFilter.val('all');
                    view._$reviewerFilter.trigger('change');

                    const $issues =
                        view.$el
                        .find(ISSUE_ROW_SEL)
                        .not('.-is-hidden');
                    expect($issues.length).toBe(2);
                    expect($issues.eq(0).data('issue-id')).toBe(4);
                    expect($issues.eq(1).data('issue-id')).toBe(5);
                });

                it('Without issues', function() {
                    view.$el.find(ISSUE_ROW_SEL).remove();
                    view.render();

                    view._$reviewerFilter.val('user1');
                    view._$reviewerFilter.trigger('change');

                    view._$reviewerFilter.val('all');
                    view._$reviewerFilter.trigger('change');

                    expect(view.$el
                           .find(ISSUE_ROW_SEL)
                           .not('.-is-hidden').length)
                        .toBe(0);

                    const $noIssues = view.$(NO_ISSUES_SEL);
                    expect($noIssues.length).toBe(1);
                });
            });

            describe('To user', function() {
                it('With issues', function() {
                    view.render();
                    view._$reviewerFilter.val('user1');
                    view._$reviewerFilter.trigger('change');

                    const $issues =
                        view.$el
                        .find(ISSUE_ROW_SEL)
                        .not('.-is-hidden');
                    expect($issues.length).toBe(1);
                    expect($issues.eq(0).data('issue-id')).toBe(4);
                });

                describe('Without issues', function() {
                    function testByUserWithoutIssues(state) {
                        it(`And filtered by ${state} issues`, function() {
                            view.$el
                                .find(`${ISSUE_ROW_SEL}.-is-${state}` +
                                      '[data-reviewer="user1"]')
                                .remove();
                            view.render();

                            view._$reviewerFilter.val('user1');
                            view._$reviewerFilter.trigger('change');

                            const $tab = getTab(state);
                            $tab.click();

                            expect(view.$el
                                   .find(ISSUE_ROW_SEL)
                                   .not('.-is-hidden').length)
                                .toBe(0);

                            const $noIssues = view.$(NO_ISSUES_SEL);
                            expect($noIssues.length).toBe(1);
                            expect($noIssues.text().strip()).toBe(
                                `There are no ${state} issues from user1`);
                        });
                    }

                    testByUserWithoutIssues('open');
                    testByUserWithoutIssues('resolved');
                    testByUserWithoutIssues('dropped');
                });
            });
        });

        describe('Status filters', function() {
            function testStatusFilters(options) {
                const state = options.state;

                describe(options.description, function() {
                    it('With issues', function() {
                        const expectedIDs = options.expectedIDs;

                        view.render();

                        const $tab = getTab(state);
                        $tab.click();
                        expect($tab.hasClass('-is-active')).toBe(true);

                        const $allIssues = view.$el.find(ISSUE_ROW_SEL);
                        const $issues = $allIssues.not('.-is-hidden');

                        expect(view.$el
                               .find(`${ISSUE_ROW_SEL}.-is-hidden`).length)
                            .toBe($allIssues.length - expectedIDs.length);
                        expect($issues.length).toBe(expectedIDs.length);
                        expect(view.$(NO_ISSUES_SEL).length).toBe(0);

                        for (let i = 0; i < expectedIDs.length; i++) {
                            expect($issues.eq(i).data('issue-id'))
                                .toBe(expectedIDs[i]);
                        }
                    });

                    it('Without issues', function() {
                        const stateSel = view.stateToSelectorMap[state];
                        view.$el
                            .find(`${ISSUE_ROW_SEL}${stateSel}`)
                            .remove();
                        view.render();

                        const $tab = getTab(state);
                        $tab.click();
                        expect($tab.hasClass('-is-active')).toBe(true);

                        expect(view.$el
                               .find(ISSUE_ROW_SEL)
                               .not('.-is-hidden').length)
                            .toBe(0);

                        const $noIssues = view.$(NO_ISSUES_SEL);
                        expect($noIssues.length).toBe(1);
                        expect($noIssues.text().strip())
                            .toBe(options.noIssuesText);
                    });
                });
            }

            testStatusFilters({
                description: 'All',
                state: 'all',
                expectedIDs: [1, 2, 3, 4, 5, 6, 7, 8],
                noIssuesText: '',
            });

            testStatusFilters({
                description: 'Verifying',
                state: 'verifying',
                expectedIDs: [7, 8],
                noIssuesText: 'There are no issues waiting for verification',
            });

            testStatusFilters({
                description: 'Open',
                state: 'open',
                expectedIDs: [4, 5],
                noIssuesText: 'There are no open issues',
            });

            testStatusFilters({
                description: 'Resolved',
                state: 'resolved',
                expectedIDs: [1, 2, 3],
                noIssuesText: 'There are no resolved issues',
            });

            testStatusFilters({
                description: 'Dropped',
                state: 'dropped',
                expectedIDs: [6],
                noIssuesText: 'There are no dropped issues',
            });
        });
    });

    describe('Events', function() {
        it('Issue clicked', function() {
            const cb = jasmine.createSpy();

            view.render();
            view.on('issueClicked', cb);

            view.commentIDToRowMap['4'].click();

            expect(cb).toHaveBeenCalledWith({
                commentType: 'diff',
                commentID: 4,
                commentURL: '#comment4',
            });
        });

        describe('Issue status updated', function() {
            const date = new Date(2017, 7, 6, 1, 4, 30);
            let $issue;
            let $icon;
            let comment;

            beforeEach(function() {
                comment = new RB.DiffComment({
                    id: 4,
                });

                view.render();
                expect(view.$('#resolved-counter').text()).toBe('3');
                expect(view.$('#open-counter').text()).toBe('2');
                expect(view.$('#dropped-counter').text()).toBe('1');
                expect(view.$('#total-counter').text()).toBe('6');

                $issue = view.commentIDToRowMap['4'];
                $icon = $issue.find('.rb-icon');
            });

            it('To dropped', function() {
                comment.set('issueStatus', 'dropped');
                view.model.trigger('issueStatusUpdated', comment, 'open', date);

                expect(view.$('#open-counter').text()).toBe('1');
                expect(view.$('#dropped-counter').text()).toBe('2');
                expect(view.$('#total-counter').text()).toBe('6');

                expect($icon.hasClass('rb-icon-issue-open')).toBe(false);
                expect($icon.hasClass('rb-icon-issue-dropped')).toBe(true);
            });

            it('To resolved', function() {
                comment.set('issueStatus', 'resolved');
                view.model.trigger('issueStatusUpdated', comment, 'open', date);

                expect(view.$('#resolved-counter').text()).toBe('4');
                expect(view.$('#open-counter').text()).toBe('1');
                expect(view.$('#total-counter').text()).toBe('6');

                expect($icon.hasClass('rb-icon-issue-open')).toBe(false);
                expect($icon.hasClass('rb-icon-issue-resolved')).toBe(true);
            });

            it('To open', function() {
                comment.set({
                    issueStatus: 'open',
                    id: 1,
                });
                view.model.trigger('issueStatusUpdated', comment, 'resolved',
                                   date);

                $issue = view.commentIDToRowMap['1'];
                $icon = $issue.find('.rb-icon');

                expect(view.$('#resolved-counter').text()).toBe('2');
                expect(view.$('#open-counter').text()).toBe('3');
                expect(view.$('#total-counter').text()).toBe('6');

                expect($icon.hasClass('rb-icon-issue-resolved')).toBe(false);
                expect($icon.hasClass('rb-icon-issue-open')).toBe(true);
            });

            it('After re-renders', function() {
                view.render();
                view.render();

                comment.set('issueStatus', 'resolved');
                view.model.trigger('issueStatusUpdated', comment, 'open',
                                   date);

                expect(view.$('#resolved-counter').text()).toBe('4');
                expect(view.$('#open-counter').text()).toBe('1');
                expect(view.$('#total-counter').text()).toBe('6');

                expect($icon.hasClass('rb-icon-issue-open')).toBe(false);
                expect($icon.hasClass('rb-icon-issue-resolved')).toBe(true);
            });

            afterEach(function() {
                expect($issue.find(`${LAST_UPDATED_CELL_SEL} time`)
                       .attr('datetime'))
                    .toBe(date.toISOString());
            });
        });

        describe('Header clicked', function() {
            function testHeaderSorting(options) {
                it(options.description, function() {
                    view.render();

                    const event = $.Event('click');
                    event.shiftKey = !!options.shiftKey;

                    const $header = view.$(options.headerSel);
                    console.assert($header.length === 1);

                    $header.trigger(event);

                    const $issues = view.$(ISSUE_ROW_SEL);
                    expect($issues.length).toBe(8);

                    const foundIDs = [];

                    for (let i = 0; i < $issues.length; i++) {
                        foundIDs.push($issues.eq(i).data('issue-id'));
                    }

                    expect(foundIDs).toEqual(options.expectedIDs);
                });
            }

            describe('Ascending', function() {
                testHeaderSorting({
                    description: 'Description',
                    headerSel: DESCRIPTION_HEADER_SEL,
                    expectedIDs: [6, 4, 5, 1, 2, 3, 7, 8],
                });

                testHeaderSorting({
                    description: 'From',
                    headerSel: REVIEWER_HEADER_SEL,
                    expectedIDs: [1, 4, 6, 2, 5, 8, 3, 7],
                });

                testHeaderSorting({
                    description: 'Last Updated',
                    headerSel: LAST_UPDATED_HEADER_SEL,
                    expectedIDs: [8, 3, 7, 2, 5, 1, 4, 6],
                });
            });

            describe('Descending', function() {
                testHeaderSorting({
                    description: 'Description',
                    headerSel: DESCRIPTION_HEADER_SEL,
                    expectedIDs: [8, 7, 3, 2, 1, 5, 4, 6],
                    shiftKey: true,
                });

                testHeaderSorting({
                    description: 'From',
                    headerSel: REVIEWER_HEADER_SEL,
                    expectedIDs: [3, 7, 2, 5, 8, 1, 4, 6],
                    shiftKey: true,
                });

                testHeaderSorting({
                    description: 'Last Updated',
                    headerSel: LAST_UPDATED_HEADER_SEL,
                    expectedIDs: [1, 4, 6, 2, 5, 7, 3, 8],
                    shiftKey: true,
                });
            });
        });
    });
});
