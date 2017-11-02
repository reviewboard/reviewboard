/**
 * View that manages a display of issues filed on a review request.
 *
 * This displays all the issues filed against a review request, and allows
 * sorting by state and reviewer. As issues are updated on reviews, the
 * table is updated to reflect the new states.
 */
RB.ReviewRequestPage.IssueSummaryTableView = Backbone.View.extend({
    events: {
        'change #issue-reviewer-filter': '_onReviewerChanged',
        'click .issue-summary-tab': '_onTabChanged',
        'click thead th': '_onHeaderClicked',
        'click .issue': '_onIssueClicked',
    },

    /** Maps a status filter state to its corresponding selector. */
    stateToSelectorMap: {
        open: '.open',
        dropped: '.dropped',
        resolved: '.resolved',
        verifying: '.verifying-resolved, .verifying-dropped',
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
        <tr class="no-issues">
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
        this.reviewerToSelectorMap = {
            all: '',
        };

        this._lastWindowWidth = null;
        this._$window = $(window);

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
        this._$table = this.$el.find('table');
        this._$thead = this._$table.find('thead');
        this._$tbody = this._$table.find('tbody');
        this._$filters = this.$('.issue-summary-filters');
        this._$reviewerFilter = this._$filters.find('#issue-reviewer-filter');
        this._$reviewerHeader = this._$thead.find('.from-header');

        this._$currentTab = this.$('.issue-summary-tab.active');
        console.assert(this._$currentTab.length === 1);

        this.statusFilterState = this._$currentTab.data('issue-state');
        this.reviewerFilterState = this._$reviewerFilter.val();

        this._buildReviewerFilterMap();
        this._checkIssues();

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
        this._$tbody.find('.issue.hidden').removeClass('hidden');
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
            this._$tbody.find('.issue').not(sel).addClass('hidden');
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
        this._$tbody.find('tr.no-issues').remove();
        this._$thead.show();

        if (this._$tbody.find('tr.issue').not('.hidden').length === 0) {
            let text;

            if (this.reviewerFilterState !== 'all') {
                if (this.statusFilterState === 'open') {
                    text = interpolate(
                        gettext('There are no open issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'verifying') {
                    text = interpolate(
                        gettext('There are no issues waiting for verification from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'dropped') {
                    text = interpolate(
                        gettext('There are no dropped issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'resolved') {
                    text = interpolate(
                        gettext('There are no resolved issues from %s'),
                        [this.reviewerFilterState]);
                }
            } else {
                if (this.statusFilterState === 'open') {
                    text = gettext('There are no open issues');
                } else if (this.statusFilterState === 'verifying') {
                    text = gettext('There are no issues waiting for verification');
                } else if (this.statusFilterState === 'dropped') {
                    text = gettext('There are no dropped issues');
                } else if (this.statusFilterState === 'resolved') {
                    text = gettext('There are no resolved issues');
                }
            }

            this._$thead.hide();
            this._$tbody.append(this._noIssuesTemplate({
                text: text,
            }));
        }
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
        this._$tbody.html($('.issue').sort((issueA, issueB) => {
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
     * Build the entries for the reviewers filter.
     */
    _buildReviewerFilterMap() {
        _.each(this._$tbody.find('.issue'), issueEl => {
            const reviewer = $(issueEl).data('reviewer');

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
        const $entry = $(`#summary-table-entry-${comment.id}`);
        const newStatus = comment.get('issueStatus');

        RB.scrollManager.markForUpdate(this.$el);

        /* Update the icon for this entry to reflect the new status. */
        $entry
            .removeClass(oldStatus)
            .addClass(newStatus)
            .find('.issue-icon')
                .removeClass(this.statusIconsMap[oldStatus])
                .addClass(this.statusIconsMap[newStatus]);

        /* Show or hide the entry according to the current filter state. */
        if (this.statusFilterState !== newStatus &&
            this.statusFilterState !== 'all') {
            $entry.addClass('hidden');
        } else {
            $entry.removeClass('hidden');
        }

        /* Update the displayed counters for this issue type. */
        const $oldCounter = $(`#${oldStatus}-counter`);
        const $newCounter = $(`#${newStatus}-counter`);

        $oldCounter.text(parseInt($oldCounter.text(), 10) - 1);
        $newCounter.text(parseInt($newCounter.text(), 10) + 1);

        /* Update the timestamp for this issue's entry. */
        $entry.find('.last-updated time')
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

        if (this._$tbody.find('tr.issue').not('.hidden').length !== 0) {
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

        this._$currentTab.removeClass('active');

        this._resetFilters();
        this.statusFilterState = $tab.data('issue-state');
        this._applyFilters();

        $tab.addClass('active');
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
