/**
 * View that manages a display of issues filed on a review request.
 *
 * This displays all the issues filed against a review request, and allows
 * sorting by state and reviewer. As issues are updated on reviews, the
 * table is updated to reflect the new states.
 */
RB.ReviewRequestPage.IssueSummaryTableView = Backbone.View.extend({
    events: {
        'change .rb-c-issue-summary-table__reviewer-filter':
            '_onReviewerChanged',
        'click thead th': '_onHeaderClicked',
        'click .rb-c-tabs__tab': '_onTabChanged',
        'click tbody tr': '_onIssueClicked',
    },

    /** Maps a status filter state to its corresponding selector. */
    stateToSelectorMap: {
        open: '.-is-open',
        dropped: '.-is-dropped',
        resolved: '.-is-resolved',
        verifying: '.-is-verifying-resolved, .-is-verifying-dropped',
        all: '',
    },

    /** Maps an issue status type to its corresponding icon. */
    statusIconsMap: {
        open: 'rb-icon-issue-open',
        dropped: 'rb-icon-issue-dropped',
        resolved: 'rb-icon-issue-resolved',
        verifying: 'rb-icon-issue-verifying',
    },

    COLUMN_DESCRIPTION: 1,
    COLUMN_REVIEWER: 2,
    COLUMN_LAST_UPDATED: 3,

    _noIssuesTemplate: _.template(dedent`
        <tr class="rb-c-issue-summary-table__no-issues">
         <td colspan="5"><em><%- text %></em></td>
        </tr>
    `),

    /**
     * Initialize the issue summary table.
     */
    initialize() {
        this.statusFilterState = null;
        this.reviewerFilterState = null;

        // Maps a reviewer name to issues issued by the reviewer.
        this.reviewerToSelectorMap = null;

        // Maps comment IDs to rows in the table.
        this.commentIDToRowMap = {};

        this._lastWindowWidth = null;
        this._$window = $(window);
        this._$currentTab = null;

        _.bindAll(this, '_onWindowResize');
    },

    /**
     * Render the issue summary table.
     *
     * Returns:
     *     RB.ReviewRequestPage.IssueSummaryTableView:
     *     This instance, for chaining.
     */
    render() {
        const $issueSummaryTable =
            this.$el.children('.rb-c-issue-summary-table');

        this._$header = $issueSummaryTable.children(
            '.rb-c-review-request-field-tabular__header');
        this._$tabs = this._$header.children('.rb-c-tabs');
        this._$filters = this._$header.children(
            '.rb-c-review-request-field-tabular__filters');
        this._$reviewerFilter = this._$filters.children(
            '.rb-c-issue-summary-table__reviewer-filter');
        this._$table = $issueSummaryTable.children(
            '.rb-c-review-request-field-tabular__data');
        this._$thead = this._$table.children('thead');
        this._$tbody = this._$table.children('tbody');
        this._$reviewerHeader = this._$thead.find(
            `tr :nth-child(${this.COLUMN_REVIEWER})`);
        this._$noIssues = null;

        let hasExistingState = false;

        if (this.statusFilterState === null) {
            this._$currentTab = this.$('.rb-c-tabs__tab.-is-active');
            console.assert(this._$currentTab.length === 1);

            this.statusFilterState = this._$currentTab.data('issue-state');
        } else {
            this.$('.rb-c-tabs__tab.-is-active').removeClass('-is-active');
            this._$currentTab =
                this.$('.rb-c-tabs__tab' +
                       `[data-issue-state=${this.statusFilterState}]`)
                    .addClass('-is-active');
            hasExistingState = true;
        }

        this._buildMaps();

        if (this.reviewerFilterState === null) {
            this.reviewerFilterState = this._$reviewerFilter.val();
        } else {
            this._$reviewerFilter.val(this.reviewerFilterState);
            hasExistingState = true;
        }

        if (hasExistingState) {
            this._resetFilters();
            this._applyFilters();
        } else {
            this._checkIssues();
        }

        this.stopListening(this.model, 'issueStatusUpdated');
        this.listenTo(this.model, 'issueStatusUpdated',
                      this._onIssueStatusChanged);

        this._$window.off('resize', this._onWindowResize);
        this._$window.on('resize', this._onWindowResize);
        this._onWindowResize();

        this.$('.user').user_infobox();
        this.$('time.timesince').timesince();
        Djblets.enableRetinaImages(this.$el);

        return this;
    },

    /**
     * Reset the filters on the list.
     *
     * This will unhide all rows, preparing the list for a new filter.
     */
    _resetFilters() {
        this._getIssueRows().filter('.-is-hidden').removeClass('-is-hidden');
    },

    /**
     * Apply the filters on the list.
     *
     * This will show or hide rows, based on the current state and reviewer
     * filters.
     */
    _applyFilters() {
        const sel = this.stateToSelectorMap[this.statusFilterState] +
                    this.reviewerToSelectorMap[this.reviewerFilterState];

        if (sel) {
            this._getIssueRows()
                .not(sel)
                .addClass('-is-hidden');
        }

        this._checkIssues();
        this._updateReviewersPos();
    },

    /**
     * Update the position of the reviewers filter.
     *
     * The filter will be aligned with the header column in the table.
     */
    _updateReviewersPos() {
        if (this._$reviewerHeader.is(':visible')) {
            this._$filters.css({
                left: this._$reviewerHeader.offset().left -
                      this._$table.offset().left +
                      this._$reviewerHeader.getExtents('p', 'l'),
            });
        } else {
            this._$filters.css('left', '');
        }
    },

    /**
     * Update the UI to reflect whether the issue list is empty.
     *
     * If the issue list is empty, this will add a row saying there are no
     * issues, using wording that reflects the current filter state.
     */
    _checkIssues() {
        if (this._$noIssues !== null) {
            this._$noIssues.remove();
            this._$noIssues = null;
        }

        this._$thead.show();

        if (this._getIssueRows().not('.-is-hidden').length === 0) {
            const reviewerFilter = this.reviewerFilterState;
            const statusFilter = this.statusFilterState;
            let text;

            if (reviewerFilter !== 'all') {
                if (statusFilter === 'open') {
                    text = interpolate(
                        gettext('There are no open issues from %s'),
                        [reviewerFilter]);
                } else if (statusFilter === 'verifying') {
                    text = interpolate(
                        gettext('There are no issues waiting for verification from %s'),
                        [reviewerFilter]);
                } else if (statusFilter === 'dropped') {
                    text = interpolate(
                        gettext('There are no dropped issues from %s'),
                        [reviewerFilter]);
                } else if (statusFilter === 'resolved') {
                    text = interpolate(
                        gettext('There are no resolved issues from %s'),
                        [reviewerFilter]);
                }
            } else {
                if (statusFilter === 'open') {
                    text = gettext('There are no open issues');
                } else if (statusFilter === 'verifying') {
                    text = gettext('There are no issues waiting for verification');
                } else if (statusFilter === 'dropped') {
                    text = gettext('There are no dropped issues');
                } else if (statusFilter === 'resolved') {
                    text = gettext('There are no resolved issues');
                }
            }

            this._$thead.hide();

            this._$noIssues =
                $(this._noIssuesTemplate({
                    text: text,
                }))
                .appendTo(this._$tbody);
        }
    },

    /**
     * Return the table rows containing issues.
     *
     * Returns:
     *     jQuery:
     *     A selector for the rows containing issues.
     */
    _getIssueRows() {
        return this._$tbody
            .children()
            .not('.rb-c-issue-summary-table__no-issues');
    },

    /**
     * Sort the issues by the selected column in ascending order.
     *
     * The Last Updated column will be sorted based on its timestamp. All
     * other columns will be sorted based on their normalized text contents.
     *
     * Args:
     *     colIndex (number):
     *         The 0-based index of the column clicked.
     *
     *     ascending (boolean):
     *         Whether to sort by ascending order.
     */
    _sortByCol(colIndex, ascending) {
        this._$tbody.html(this._getIssueRows().sort((issueA, issueB) => {
            const $issueA = $(issueA);
            const $issueB = $(issueB);
            const $columnA = $issueA.children(`td:nth-child(${colIndex})`);
            const $columnB = $issueB.children(`td:nth-child(${colIndex})`);
            let value1;
            let value2;

            if (colIndex === this.COLUMN_LAST_UPDATED) {
                /*
                 * Note that we're reversing the values here. We want newer
                 * timestamps (which is "greater", comparison-wise).
                 */
                value1 = $columnB.children('time').attr('datetime');
                value2 = $columnA.children('time').attr('datetime');
            } else {
                value1 = $columnA.text().strip().toLowerCase();
                value2 = $columnB.text().strip().toLowerCase();
            }

            /*
             * If the two values are the same, we'll want to order by
             * issue ID instead, helping to keep ordering consistent within
             * an author or published timestamp.
             *
             * They should always be in ascending order, relative to the
             * column being sorted.
             */
            if (value1 === value2) {
                const issueID1 = $issueA.data('issue-id');
                const issueID2 = $issueB.data('issue-id');

                if (ascending) {
                    value1 = issueID1;
                    value2 = issueID2;
                } else {
                    value1 = issueID2;
                    value2 = issueID1;
                }
            }

            /*
             * Compute an initial value intended for ascending order. Then
             * we'll negate it if sorting in descending order.
             */
            let result;

            if (value1 < value2) {
                result = -1;
            } else if (value1 > value2) {
                result = 1;
            } else {
                result = 0;
            }

            if (!ascending) {
                result = -result;
            }

            return result;
        }));
    },

    /**
     * Build maps for looking up issue rows based on state.
     *
     * This will build a map (and filter entries) for reviewers, and build
     * a map of comment IDs to rows.
     */
    _buildMaps() {
        this._$reviewerFilter.children().not('[value="all"]').remove();

        this.reviewerToSelectorMap = {
            all: '',
        };

        _.each(this._getIssueRows(), issueEl => {
            const $issue = $(issueEl);

            this.commentIDToRowMap[$issue.data('issue-id')] = $issue;

            const reviewer = $issue.data('reviewer');

            if (!_.has(this.reviewerToSelectorMap, reviewer)) {
                this.reviewerToSelectorMap[reviewer] =
                    `[data-reviewer="${reviewer}"]`;
                this._$reviewerFilter.append(
                    $('<option>').text(reviewer).val(reviewer));
            }
        });
    },

    /**
     * Handler for when the issue status of a comment changes.
     *
     * Updates the display of the table to reflect the state of that issue.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment whose issue has changed.
     *
     *     oldStatus (string):
     *         The old status.
     *
     *     timestamp (Date):
     *         The new timestamp for the comment.
     */
    _onIssueStatusChanged(comment, oldStatus, timestamp) {
        const $entry = this.commentIDToRowMap[comment.id];
        const newStatus = comment.get('issueStatus');

        RB.scrollManager.markForUpdate(this.$el);

        /* Update the icon for this entry to reflect the new status. */
        $entry
            .removeClass(`-is-${oldStatus}`)
            .addClass(`-is-${newStatus}`)
            .find('.rb-icon')
                .removeClass(this.statusIconsMap[oldStatus])
                .addClass(this.statusIconsMap[newStatus]);

        /* Show or hide the entry according to the current filter state. */
        if (this.statusFilterState !== newStatus &&
            this.statusFilterState !== 'all') {
            $entry.addClass('-is-hidden');
        } else {
            $entry.removeClass('-is-hidden');
        }

        /* Update the displayed counters for this issue type. */
        const $oldCounter =
            this._$tabs
            .children(`[data-issue-state=${oldStatus}]`)
            .find('.rb-c-issue-summary-table__counter');
        const $newCounter =
            this._$tabs
            .children(`[data-issue-state=${newStatus}]`)
            .find('.rb-c-issue-summary-table__counter');

        $oldCounter.text(parseInt($oldCounter.text(), 10) - 1);
        $newCounter.text(parseInt($newCounter.text(), 10) + 1);

        /* Update the timestamp for this issue's entry. */
        $entry.find('time')
            .attr('datetime', new Date(timestamp).toISOString())
            .text(timestamp)
            .timesince();

        /*
         * If we're no longer showing any issues for this filter, update
         * the table accordingly.
         */
        this._checkIssues();

        /*
         * The updates may have impacted the reviewers filter, so update its
         * position.
         */
        this._updateReviewersPos();

        /*
         * Update the scroll position to counteract the addition/deletion
         * of the entry in the issue summary table, so the page doesn't
         * appear to jump.
         */
        RB.scrollManager.markUpdated(this.$el);
    },

    /**
     * Handler for when a header on the table is clicked.
     *
     * This will sort the table by the header.
     *
     * Args:
     *     evt (Event):
     *         The click event.
     */
    _onHeaderClicked(evt) {
        evt.stopPropagation();

        if (this._getIssueRows().not('.-is-hidden').length !== 0) {
            this._sortByCol(
                $(evt.target).parent().children().index(evt.target) + 1,
                !evt.shiftKey);
        }
    },

    /**
     * Handler for when an issue is clicked.
     *
     * This will notify any listeners to the ``issueClicked`` event that the
     * issue has been clicked, providing the comment type and the issue ID.
     *
     * It will then navigate to the URL for that particular comment.
     *
     * Args:
     *     evt (Event):
     *         The click event.
     */
    _onIssueClicked(evt) {
        if (evt.target.tagName === 'A') {
            /* Allow the link to go through. */
            return;
        }

        evt.stopPropagation();

        /*
         * Extract the comment's attributes from the issue element and trigger
         * the issueClicked event so the page can navigate the user to the
         * relevant issue comment.
         */
        const $el = $(evt.currentTarget);

        this.trigger('issueClicked', {
            commentType: $el.data('comment-type'),
            commentID: $el.data('issue-id'),
            commentURL: $el.data('comment-href'),
        });
    },

    /**
     * Handler for when the tab has changed.
     *
     * This will switch the view to show the issues that match the tab's
     * issue state and the current reviewer filter.
     *
     * Args:
     *     evt (Event):
     *         The click event.
     */
    _onTabChanged(evt) {
        const $tab = $(evt.currentTarget);

        this._$currentTab.removeClass('-is-active');

        this._resetFilters();
        this.statusFilterState = $tab.data('issue-state');
        this._applyFilters();

        $tab.addClass('-is-active');
        this._$currentTab = $tab;
    },

    /**
     * Handler for when the reviewer filter changes.
     *
     * This will switch the view to show issues that match the reviewer
     * and the current issue filter state.
     */
    _onReviewerChanged() {
        this._resetFilters();
        this.reviewerFilterState = this._$reviewerFilter.val();
        this._applyFilters();
    },

    /**
     * Handler for when the window resizes.
     *
     * Updates the calculated position of the reviewers filter.
     */
    _onWindowResize() {
        const winWidth = this._$window.width();

        if (winWidth !== this._lastWindowWidth) {
            this._updateReviewersPos();
        }

        this._lastWindowWidth = winWidth;
    }
});
