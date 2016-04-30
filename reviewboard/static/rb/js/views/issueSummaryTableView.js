/*
 * IssueSummaryTableView handles all interactions with the issue summary
 * table.
 */
RB.IssueSummaryTableView = Backbone.View.extend({
    events: {
        'change #issue-reviewer-filter': '_onReviewerChanged',
        'click .issue-summary-tab': '_onTabChanged',
        'click thead th': '_onHeaderClicked',
        'click .issue': '_onIssueClicked'
    },

    // Maps a status filter state to its corresponding selector
    stateToSelectorMap: {
        open: ".open",
        dropped: ".dropped",
        resolved: ".resolved",
        all: ""
    },

    statusIconsMap: {
        open: 'rb-icon-issue-open',
        dropped: 'rb-icon-issue-dropped',
        resolved: 'rb-icon-issue-resolved'
    },

    initialize: function() {
        this.statusFilterState = null;
        this.reviewerFilterState = null;

        // Maps a reviewer name to issues issued by the reviewer
        this.reviewerToSelectorMap = {
            all: ""
        };

        this._lastWindowWidth = null;
        this._$window = $(window);

        _.bindAll(this, '_onWindowResize');
    },

    render: function() {
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
        this._checkNoIssues();
        this._uncollapseTarget();

        this.listenTo(this.model, 'issueStatusUpdated',
                      this._onIssueStatusChanged);

        this._$window.off('resize', this._onWindowResize);
        this._$window.on('resize', this._onWindowResize);
        this._onWindowResize();

        return this;
    },

    // Show or hide entry according to issue summary filter state.
    setVisibility: function(entry, status) {
        if (this.statusFilterState !== status &&
            this.statusFilterState !== 'all') {
            entry.addClass('hidden');
        } else {
            entry.removeClass('hidden');
        }
    },

    // Decrement old status counter and increment new status counter.
    updateCounters: function(old_status, new_status) {
        var old_counter = $('#' + old_status + '-counter'),
            new_counter = $('#' + new_status + '-counter');

        old_counter.text(parseInt(old_counter.text(), 10) - 1);
        new_counter.text(parseInt(new_counter.text(), 10) + 1);
    },

    // Replace old status class with new status class and update text.
    updateStatus: function(entry, old_status, new_status) {
        entry.removeClass(old_status)
            .addClass(new_status)
            .find('.issue-icon')
                .removeClass(this.statusIconsMap[old_status])
                .addClass(this.statusIconsMap[new_status]);

        this.setVisibility(entry, new_status);
        this._checkNoIssues();
        this._updateReviewersPos();
    },

    // Replace old timestamp attirbute with new timestamp and update text.
    updateTimeStamp: function(entry, timestamp) {
        entry.find('.last-updated time')
            .attr("datetime", new Date(timestamp).toISOString())
            .text(timestamp)
            .timesince();
    },

    /*
     * Handler for when the tab has changed.
     *
     * This will switch the view to show the issues that match the tab's
     * issue state and the current reviewer filter.
     */
    _onTabChanged: function(e) {
        var $tab = $(e.currentTarget);

        this._$currentTab.removeClass('active');

        this._resetFilters();
        this.statusFilterState = $tab.data('issue-state');
        this._applyFilters();

        $tab.addClass('active');
        this._$currentTab = $tab;
    },

    /*
     * Handler for when the reviewer filter changes.
     *
     * This will switch the view to show issues that match the reviewer
     * and the current issue filter state.
     */
    _onReviewerChanged: function() {
        this._resetFilters();
        this.reviewerFilterState = this._$reviewerFilter.val();
        this._applyFilters();
    },

    /*
     * Reset the filters on the list.
     *
     * This will unhide all rows, preparing the list for a new filter.
     */
    _resetFilters: function() {
        this._$tbody.find('.issue.hidden').removeClass('hidden');
    },

    /*
     * Apply the filters on the list.
     *
     * This will show or hide rows, based on the current state and reviewer
     * filters.
     */
    _applyFilters: function() {
        var sel = this.stateToSelectorMap[this.statusFilterState] +
                  this.reviewerToSelectorMap[this.reviewerFilterState];

        if (sel) {
            this._$tbody.find('.issue').not(sel).addClass('hidden');
        }

        this._checkNoIssues();
        this._updateReviewersPos();
    },

    /*
     * Updates the position of the reviewers filter.
     *
     * The filter will be aligned with the header column in the table.
     */
    _updateReviewersPos: function() {
        if (this._$reviewerHeader.is(':visible')) {
            this._$filters.css({
                left: this._$reviewerHeader.offset().left -
                      this._$table.offset().left +
                      this._$reviewerHeader.getExtents('p', 'l')
            });
        } else {
            this._$filters.css('left', '');
        }
    },

    _onHeaderClicked: function(event) {
        if (this._$tbody.find('tr.issue:visible').length !== 0) {
            var $header = $(event.target);

            this._sortByCol(
                $header.parent().children().index(event.target) + 1);
        }

        return false;
    },

    _onIssueClicked: function(event) {
        var $el;

        if (event.target.tagName === 'A') {
            /* Allow the link to go through. */
            return;
        }

        $el = $(event.currentTarget);

        event.stopPropagation();

        /*
         * Extract the comment's attributes from the issue element and trigger
         * the issueClicked event so the page can navigate the user to the
         * relevant issue comment.
         */
        this.trigger('issueClicked', {
            type: $el.data('comment-type'),
            id: $el.data('issue-id')
        });

        window.location = $el.data('comment-href');
    },

    // Check that there are no issues that match the selected filter(s).
    _checkNoIssues: function() {
        this._$tbody.find('tr.no-issues').remove();
        this._$thead.show();

        if (this._$tbody.find('tr.issue:visible').length === 0) {
            var text;

            if (this.reviewerFilterState !== 'all') {
                if (this.statusFilterState === "open") {
                    text = interpolate(
                        gettext('There are no open issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'dropped') {
                    text = interpolate(
                        gettext('There are no dropped issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'resolved') {
                    text = interpolate(
                        gettext('There are no resolved issues'),
                        [this.reviewerFilterState]);
                }
            } else {
                if (this.statusFilterState === "open") {
                    text = gettext('There are no open issues');
                } else if (this.statusFilterState === 'dropped') {
                    text = gettext('There are no dropped issues');
                } else if (this.statusFilterState === 'resolved') {
                    text = gettext('There are no resolved issues');
                }
            }

            this._$thead.hide();
            this._$tbody.append($('<tr>')
                .addClass('no-issues')
                .append($('<td>')
                    .attr("colspan", 5)
                    .append($('<i>')
                        .text(text))));
        }
    },

    /*
     * Sort the issue summary table entries by the selected column in ascending
     * order.
     *
     * Entries with timestamps will be sorted using the timestamp attribute.
     * Entries with comment ids will be sorted using the comment-id attribute.
     * All other entries will be sorted alphabetically.
     */
    _sortByCol: function(colIndex) {
        this._$tbody.html($('.issue').sort(function(a, b) {
            var firstElement = $(a).find('td:nth-child(' + colIndex + ')'),
                secondElement = $(b).find('td:nth-child(' + colIndex + ')'),
                firstElementText = firstElement.text().toLowerCase(),
                secondElementText = secondElement.text().toLowerCase(),
                firstText,
                secondText;

            if (firstElement.attr('timestamp')) {
                return parseInt(firstElement.attr('timestamp'), 10) -
                       parseInt(secondElement.attr('timestamp'), 10);
            } else if (firstElement.hasClass('comment-id')) {
                 firstText = firstElementText.split(" ");
                 secondText = secondElementText.split(" ");

                 if (firstText[0] > secondText[0]) {
                     return 1;
                 } else if (firstText[0] < secondText[0]) {
                    return -1;
                 } else {
                     return parseInt(firstText[1], 10) -
                            parseInt(secondText[1], 10);
                 }
            } else if (firstElementText > secondElementText) {
                return 1;
            } else if (firstElementText === secondElementText) {
                return 0;
            } else {
                return -1;
            }
        }));
    },

    // Add entries to the reviewerToSelectorMap
    _buildReviewerFilterMap: function() {
        var self = this;

        this._$tbody.find('.issue').each(function() {
            var reviewer = $(this).data('reviewer');

            if (!_.has(self.reviewerToSelectorMap, reviewer)) {
                self.reviewerToSelectorMap[reviewer] =
                    '[data-reviewer="' + reviewer + '"]';
                self._$reviewerFilter.append(
                    $('<option>').text(reviewer).val(reviewer));
            }
        });
    },

    _uncollapseTarget: function() {
        var hash = window.location.hash,
            commentName,
            targetBox;

        if (hash.indexOf("comment") > 0) {
            commentName = hash.toString().substring(1);
            targetBox = $('a[name=' + commentName + ']').closest(".box");

            if (targetBox.hasClass('collapsed')) {
                targetBox.removeClass('collapsed');
                // Scroll down to the targeted comment box
                window.location = window.location;
            }
        }
    },

    /*
     * Handler for when the issue status of a comment changes.
     *
     * Updates the display of the table to reflect the state of that issue.
     */
    _onIssueStatusChanged: function(comment, oldStatus, lastUpdated) {
        var entry = $('#summary-table-entry-' + comment.id),
            newStatus = comment.get('issueStatus'),
            oldHeight = this.$el.height();

        this.updateStatus(entry, oldStatus, newStatus);
        this.updateCounters(oldStatus, newStatus);
        this.updateTimeStamp(entry, lastUpdated);

        /*
         * Update the scroll position to counteract the addition/deletion
         * of the entry in the issue summary table, so the page doesn't
         * appear to jump.
         */
        $(window).scrollTop($(window).scrollTop() + this.$el.height() -
                            oldHeight);
    },

    /*
     * Handler for when the window resizes.
     *
     * Updates the calculated position of the reviewers filter.
     */
    _onWindowResize: function() {
        var winWidth = this._$window.width();

        if (winWidth !== this._lastWindowWidth) {
            this._updateReviewersPos();
        }

        this._lastWindowWidth = winWidth;
    }
});
